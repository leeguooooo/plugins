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
           mkdir -p "$dest/plugins/use-family/skills/use-family" ;;
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
  code=0; HOME="$TMP/home" PATH="$TMP/bin" sh "$ROOT/install-use-family.sh" 2>&1 || code=$?
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

echo "ok install-use-family.sh"
