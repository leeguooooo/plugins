#!/bin/sh
# Runs install-use-family.sh end to end against a fake git and an isolated HOME/PATH,
# then checks the missing-CLI hints. Nothing outside a temp dir is touched.
#   sh tests/install-use-family.test.sh
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin" "$TMP/home"

# Fake git: `clone` makes a checkout holding SKILL.md at every place the installer looks.
# For an existing checkout named $FAKE_REPO: FAKE_FETCH=fail fails fetch, FAKE_MERGE=fail
# refuses the fast-forward, FAKE_DIRTY=1 reports uncommitted changes.
cat > "$TMP/bin/git" <<'GIT'
#!/bin/sh
for dest; do :; done
[ "$1" = -C ] && repo=${2##*/}
mine() { [ "$repo" = "${FAKE_REPO:-}" ]; }
case "$*" in
  *" fetch"*) mine && [ "${FAKE_FETCH:-}" = fail ] && exit 1; exit 0 ;;
  *" merge"*) mine && [ "${FAKE_MERGE:-}" = fail ] && { echo "fatal: Not possible to fast-forward, aborting." >&2; exit 128; }; exit 0 ;;
  *" status"*) mine && [ "${FAKE_DIRTY:-}" = 1 ] && echo " M SKILL.md"; exit 0 ;;
  *clone*) mkdir -p "$dest/.git"; touch "$dest/SKILL.md"
           for sub in chrome-use cookie-use iphone-use android-use mail-use ocs; do mkdir -p "$dest/skills/$sub"; touch "$dest/skills/$sub/SKILL.md"; done
           mkdir -p "$dest/plugins/use-family/skills/use-family"
           if [ "${dest##*/}" = thermo-use ] && [ "${FAKE_THERMO_LAYOUT:-nested}" != legacy ]; then
             rm "$dest/SKILL.md"
             mkdir -p "$dest/skills/thermo-use/references"
             touch "$dest/skills/thermo-use/SKILL.md"
             echo owned-reference > "$dest/skills/thermo-use/references/ai-diagnostics.md"
           fi
           if [ "${dest##*/}" = paste-use ] && [ "${FAKE_PASTE_LAYOUT:-nested}" != legacy ]; then
             rm "$dest/SKILL.md"
             mkdir -p "$dest/skills/paste-use"
             touch "$dest/skills/paste-use/SKILL.md"
           fi
           if [ "${dest##*/}" = message-use ] && [ "${FAKE_MESSAGE_LAYOUT:-nested}" != legacy ]; then
             rm "$dest/SKILL.md"
             mkdir -p "$dest/skills/message-use"
             touch "$dest/skills/message-use/SKILL.md"
           fi
           if [ "${dest##*/}" = discord-use ] && [ "${FAKE_DISCORD_LAYOUT:-nested}" != legacy ]; then
             rm "$dest/SKILL.md"
             mkdir -p "$dest/skills/discord-use"
             touch "$dest/skills/discord-use/SKILL.md"
           fi
           if [ "${dest##*/}" = image-use ] && [ "${FAKE_IMAGE_LAYOUT:-nested}" != legacy ]; then
             rm "$dest/SKILL.md"
             mkdir -p "$dest/skills/image-use"
             touch "$dest/skills/image-use/SKILL.md"
           fi
           if [ "${dest##*/}" = switch-use ] && [ "${FAKE_SWITCH_LAYOUT:-nested}" != legacy ]; then
             rm "$dest/SKILL.md"
             mkdir -p "$dest/skills/switch-use"
             touch "$dest/skills/switch-use/SKILL.md"
           fi ;;
esac
GIT
chmod +x "$TMP/bin/git"
# Fake uname: a Mac whose arch is $FAKE_ARCH (arm64 unless a check sets it).
cat > "$TMP/bin/uname" <<'UNAME'
#!/bin/sh
case "$1" in -m) echo "${FAKE_ARCH:-arm64}" ;; *) echo Darwin ;; esac
UNAME
chmod +x "$TMP/bin/uname"
for tool in sh mkdir ln readlink touch chmod rm cat dirname basename; do
  ln -s "$(command -v "$tool")" "$TMP/bin/$tool"
done

run() {  # run: the installer's stdout and exit status ($code), with only $TMP/bin on PATH
  code=0; HOME="${TEST_HOME:-$TMP/home}" PATH="$TMP/bin" sh "$ROOT/install-use-family.sh" 2>&1 || code=$?
}
fail() { echo "FAIL: $1"; echo "$out"; exit 1; }

out=$(run; echo "exit=$code")
echo "$out" | grep -qF "exit=0" || fail "fresh install did not exit 0"
echo "$out" | grep -qF "linked android-use" || fail "Android skill missing"
echo "$out" | grep -qF "leeguooooo/android-use/main/install.sh | sh" || fail "Android installer hint missing"
echo "$out" | grep -q '^CLIs not installed yet:.* image-use' || fail "image-use missing from the not-installed list"
echo "$out" | grep -qF 'leeguooooo/image-use/main/install.sh | sh' || fail "no image-use installer line"
echo "$out" | grep -qF 'leeguooooo/mail-use/main/install.sh | sh' || fail "generic install.sh hint lost"
echo "$out" | grep -qF 'leeguooooo/plugins/main/install-clis.sh | sh' || fail "no all-at-once install-clis.sh line"
echo "$out" | grep -q '^CLIs not installed yet:.* wechat-use' || fail "Apple Silicon: wechat-use missing from the not-installed list"

# Thermo's plugin and standalone install now share one canonical nested Skill folder.
[ "$(readlink "$TMP/home/.agents/skills/thermo-use")" = "$TMP/home/.agents/use-family/thermo-use/skills/thermo-use" ] || fail "Thermo skill linked to the wrong root"
[ ! -f "$TMP/home/.agents/use-family/thermo-use/SKILL.md" ] || fail "fixture still masks the old root-only layout"
grep -q owned-reference "$TMP/home/.agents/skills/thermo-use/references/ai-diagnostics.md" || fail "Thermo references are not accessible through the Skill link"
# An old installer-managed root link migrates; arbitrary user directories remain protected by link().
ln -sfn "$TMP/home/.agents/use-family/thermo-use" "$TMP/home/.agents/skills/thermo-use"
out=$(run)
[ "$(readlink "$TMP/home/.agents/skills/thermo-use")" = "$TMP/home/.agents/use-family/thermo-use/skills/thermo-use" ] || fail "old managed Thermo link was not migrated"

# The new installer can run before the Skill repository update and preserve a failed old checkout.
out=$(FAKE_THERMO_LAYOUT=legacy TEST_HOME="$TMP/legacy-home" run; echo "exit=$code")
echo "$out" | grep -qF "exit=0" || fail "legacy Thermo layout failed"
[ "$(readlink "$TMP/legacy-home/.agents/skills/thermo-use")" = "$TMP/legacy-home/.agents/use-family/thermo-use" ] || fail "legacy Thermo root was not retained"
out=$(FAKE_REPO=thermo-use FAKE_FETCH=fail TEST_HOME="$TMP/legacy-home" run; echo "exit=$code")
echo "$out" | grep -qF "exit=1" || fail "legacy Thermo failed update did not retain failure status"
[ -f "$TMP/legacy-home/.agents/skills/thermo-use/SKILL.md" ] || fail "failed update broke legacy Thermo Skill link"

# Paste uses the same migration behavior, including old checkouts after failed fetch.
[ "$(readlink "$TMP/home/.agents/skills/paste-use")" = "$TMP/home/.agents/use-family/paste-use/skills/paste-use" ] || fail "Paste nested Skill missing"
ln -sfn "$TMP/home/.agents/use-family/paste-use" "$TMP/home/.agents/skills/paste-use"
out=$(run)
[ "$(readlink "$TMP/home/.agents/skills/paste-use")" = "$TMP/home/.agents/use-family/paste-use/skills/paste-use" ] || fail "Paste old managed link was not migrated"
out=$(FAKE_PASTE_LAYOUT=legacy TEST_HOME="$TMP/paste-legacy-home" run; echo "exit=$code")
echo "$out" | grep -qF "exit=0" || fail "legacy Paste layout failed"
[ "$(readlink "$TMP/paste-legacy-home/.agents/skills/paste-use")" = "$TMP/paste-legacy-home/.agents/use-family/paste-use" ] || fail "legacy Paste link not retained"
out=$(FAKE_REPO=paste-use FAKE_FETCH=fail TEST_HOME="$TMP/paste-legacy-home" run; echo "exit=$code")
echo "$out" | grep -qF "exit=1" || fail "Paste failed fetch lost failure status"
[ -f "$TMP/paste-legacy-home/.agents/skills/paste-use/SKILL.md" ] || fail "failed fetch broke Paste Skill"

# Message Skill layout migrates only managed links, with old checkouts retained after failed fetch.
[ "$(readlink "$TMP/home/.agents/skills/message-use")" = "$TMP/home/.agents/use-family/message-use/skills/message-use" ] || fail "Message nested Skill missing"
ln -sfn "$TMP/home/.agents/use-family/message-use" "$TMP/home/.agents/skills/message-use"
out=$(run)
[ "$(readlink "$TMP/home/.agents/skills/message-use")" = "$TMP/home/.agents/use-family/message-use/skills/message-use" ] || fail "Message managed link not migrated"
out=$(FAKE_MESSAGE_LAYOUT=legacy TEST_HOME="$TMP/message-legacy-home" run; echo "exit=$code")
echo "$out" | grep -qF "exit=0" || fail "legacy Message layout failed"
[ "$(readlink "$TMP/message-legacy-home/.agents/skills/message-use")" = "$TMP/message-legacy-home/.agents/use-family/message-use" ] || fail "legacy Message root not retained"
out=$(FAKE_REPO=message-use FAKE_FETCH=fail TEST_HOME="$TMP/message-legacy-home" run; echo "exit=$code")
echo "$out" | grep -qF "exit=1" || fail "Message failed fetch lost failure status"
[ -f "$TMP/message-legacy-home/.agents/skills/message-use/SKILL.md" ] || fail "failed fetch broke Message Skill"

# Discord Skill layout migrates only managed links, with old checkouts retained after failed fetch.
[ "$(readlink "$TMP/home/.agents/skills/discord-use")" = "$TMP/home/.agents/use-family/discord-use/skills/discord-use" ] || fail "Discord nested Skill missing"
ln -sfn "$TMP/home/.agents/use-family/discord-use" "$TMP/home/.agents/skills/discord-use"
out=$(run)
[ "$(readlink "$TMP/home/.agents/skills/discord-use")" = "$TMP/home/.agents/use-family/discord-use/skills/discord-use" ] || fail "Discord managed link not migrated"
out=$(FAKE_DISCORD_LAYOUT=legacy TEST_HOME="$TMP/discord-legacy-home" run; echo "exit=$code")
echo "$out" | grep -qF "exit=0" || fail "legacy Discord layout failed"
[ "$(readlink "$TMP/discord-legacy-home/.agents/skills/discord-use")" = "$TMP/discord-legacy-home/.agents/use-family/discord-use" ] || fail "legacy Discord root not retained"
out=$(FAKE_REPO=discord-use FAKE_FETCH=fail TEST_HOME="$TMP/discord-legacy-home" run; echo "exit=$code")
echo "$out" | grep -qF "exit=1" || fail "Discord failed fetch lost failure status"
[ -f "$TMP/discord-legacy-home/.agents/skills/discord-use/SKILL.md" ] || fail "failed fetch broke Discord Skill"

# Image Skill layout migrates only managed links, with old checkouts retained after failed fetch.
[ "$(readlink "$TMP/home/.agents/skills/image-use")" = "$TMP/home/.agents/use-family/image-use/skills/image-use" ] || fail "Image nested Skill missing"
ln -sfn "$TMP/home/.agents/use-family/image-use" "$TMP/home/.agents/skills/image-use"
out=$(run)
[ "$(readlink "$TMP/home/.agents/skills/image-use")" = "$TMP/home/.agents/use-family/image-use/skills/image-use" ] || fail "Image managed link not migrated"
out=$(FAKE_IMAGE_LAYOUT=legacy TEST_HOME="$TMP/image-legacy-home" run; echo "exit=$code")
echo "$out" | grep -qF "exit=0" || fail "legacy Image layout failed"
[ "$(readlink "$TMP/image-legacy-home/.agents/skills/image-use")" = "$TMP/image-legacy-home/.agents/use-family/image-use" ] || fail "legacy Image root not retained"
out=$(FAKE_REPO=image-use FAKE_FETCH=fail TEST_HOME="$TMP/image-legacy-home" run; echo "exit=$code")
echo "$out" | grep -qF "exit=1" || fail "Image failed fetch lost failure status"
[ -f "$TMP/image-legacy-home/.agents/skills/image-use/SKILL.md" ] || fail "failed fetch broke Image Skill"

# Switch follows the same managed-link migration while preserving usable old checkouts.
[ "$(readlink "$TMP/home/.agents/skills/switch-use")" = "$TMP/home/.agents/use-family/switch-use/skills/switch-use" ] || fail "Switch nested Skill missing"
ln -sfn "$TMP/home/.agents/use-family/switch-use" "$TMP/home/.agents/skills/switch-use"
out=$(run)
[ "$(readlink "$TMP/home/.agents/skills/switch-use")" = "$TMP/home/.agents/use-family/switch-use/skills/switch-use" ] || fail "Switch managed link not migrated"
out=$(FAKE_SWITCH_LAYOUT=legacy TEST_HOME="$TMP/switch-legacy-home" run; echo "exit=$code")
echo "$out" | grep -qF "exit=0" || fail "legacy Switch layout failed"
[ "$(readlink "$TMP/switch-legacy-home/.agents/skills/switch-use")" = "$TMP/switch-legacy-home/.agents/use-family/switch-use" ] || fail "legacy Switch root not retained"
out=$(FAKE_REPO=switch-use FAKE_FETCH=fail TEST_HOME="$TMP/switch-legacy-home" run; echo "exit=$code")
echo "$out" | grep -qF "exit=1" || fail "Switch failed fetch lost failure status"
[ -f "$TMP/switch-legacy-home/.agents/skills/switch-use/SKILL.md" ] || fail "failed fetch broke Switch Skill"

out=$(FAKE_ARCH=x86_64 run)
echo "$out" | grep -q '^CLIs not installed yet:.* wechat-use' && fail "Intel: suggests wechat-use, whose installer is Apple Silicon only"

printf '#!/bin/sh\n' > "$TMP/bin/image-use"; chmod +x "$TMP/bin/image-use"
out=$(run)
echo "$out" | grep -q 'not installed yet:.* image-use' && fail "image-use reported although it is on PATH"

# Existing checkouts (the first run cloned them all). A clean checkout whose history was
# rewritten upstream: reported as such, the rest still update, and the run exits non-zero.
out=$(FAKE_REPO=discord-use FAKE_MERGE=fail run; echo "exit=$code")
echo "$out" | grep -qF "exit=1" || fail "diverged checkout: exit status is not 1"
echo "$out" | grep -qF "discord-use: not updated, its history no longer fast-forwards" || fail "diverged checkout: no history message"
echo "$out" | grep -qF "mv \"$TMP/home/.agents/use-family/discord-use\"" || fail "diverged checkout: no back-up-and-reclone hint"
echo "$out" | grep -q "discord-use: .*local changes" && fail "clean diverged checkout blamed on local changes"
echo "$out" | grep -qF "Not updated: discord-use" || fail "diverged checkout: missing from the failed summary"
echo "$out" | grep -qF "linked wechat-use" || fail "a failed update stopped the remaining uses"

out=$(FAKE_REPO=discord-use FAKE_MERGE=fail FAKE_DIRTY=1 run; echo "exit=$code")
echo "$out" | grep -qF "exit=1" || fail "dirty checkout: exit status is not 1"
echo "$out" | grep -qF "discord-use: not updated, $TMP/home/.agents/use-family/discord-use has local changes" || fail "dirty checkout: no local-changes message"

out=$(FAKE_REPO=mail-use FAKE_FETCH=fail run; echo "exit=$code")
echo "$out" | grep -qF "exit=1" || fail "fetch failure: exit status is not 1"
echo "$out" | grep -qF "mail-use: not updated, fetch failed" || fail "fetch failure: no message"

out=$(run; echo "exit=$code")
echo "$out" | grep -qF "exit=0" || fail "clean re-run did not exit 0"

# Grok and Cursor: mirrored only where the host exists, and nothing already there is replaced.
mkdir -p "$TMP/home/.grok/skills/chrome-use" "$TMP/home/.cursor/skills"
ln -s /elsewhere "$TMP/home/.cursor/skills/mail-use"
out=$(run; echo "exit=$code")
echo "$out" | grep -qF "exit=0" || fail "host mirror: run failed"
[ "$(readlink "$TMP/home/.grok/skills/memory-use")" = "$TMP/home/.agents/skills/memory-use" ] || fail "memory-use not mirrored into ~/.grok/skills"
[ -L "$TMP/home/.cursor/skills/bitwarden-use" ] || fail "bitwarden-use not mirrored into ~/.cursor/skills"
[ -L "$TMP/home/.grok/skills/chrome-use" ] && fail "a real skill directory in ~/.grok/skills was replaced"
[ "$(readlink "$TMP/home/.cursor/skills/mail-use")" = /elsewhere ] || fail "a user's own link in ~/.cursor/skills was replaced"
out=$(run)
echo "$out" | grep -qF ".grok/skills" && fail "host mirror is not idempotent"

echo "ok install-use-family.sh"
