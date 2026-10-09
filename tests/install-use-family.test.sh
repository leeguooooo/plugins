#!/bin/sh
# Runs install-use-family.sh end to end against a fake git and an isolated HOME/PATH,
# then checks the missing-CLI hints. Nothing outside a temp dir is touched.
#   sh tests/install-use-family.test.sh
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin" "$TMP/home"

# Fake git: `clone` makes a checkout holding SKILL.md at every place the installer looks.
cat > "$TMP/bin/git" <<'GIT'
#!/bin/sh
for dest; do :; done
case "$*" in
  *clone*) mkdir -p "$dest/.git"; touch "$dest/SKILL.md"
           for sub in chrome-use cookie-use iphone-use mail-use ocs; do mkdir -p "$dest/skills/$sub"; touch "$dest/skills/$sub/SKILL.md"; done
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

run() {  # run: the installer's stdout, with only $TMP/bin on PATH
  HOME="$TMP/home" PATH="$TMP/bin" sh "$ROOT/install-use-family.sh"
}
fail() { echo "FAIL: $1"; echo "$out"; exit 1; }

out=$(run)
echo "$out" | grep -q '^CLIs not installed yet:.* image-use' || fail "image-use missing from the not-installed list"
echo "$out" | grep -qF "sudo install \"$TMP/home/.agents/use-family/image-use/image-use\" /usr/local/bin/image-use" \
  || fail "no single-file install hint for image-use"
echo "$out" | grep -q 'leeguooooo/image-use/main/install.sh' && fail "points at an install.sh image-use does not have"
echo "$out" | grep -qF 'leeguooooo/mail-use/main/install.sh | sh' || fail "generic install.sh hint lost"

echo "$out" | grep -q '^CLIs not installed yet:.* wechat-use' || fail "Apple Silicon: wechat-use missing from the not-installed list"
echo "$out" | grep -qF 'leeguooooo/discord-use/main/install.sh | sh' || fail "Apple Silicon: lost discord-use's install.sh hint"

out=$(FAKE_ARCH=x86_64 run)
echo "$out" | grep -q '^CLIs not installed yet:.* wechat-use' && fail "Intel: suggests wechat-use, whose installer is Apple Silicon only"
echo "$out" | grep -qF 'cargo install --git https://github.com/leeguooooo/discord-use' || fail "Intel: no build-from-source hint for discord-use"

printf '#!/bin/sh\n' > "$TMP/bin/image-use"; chmod +x "$TMP/bin/image-use"
out=$(run)
echo "$out" | grep -q 'image-use/image-use\|not installed yet:.* image-use' && fail "image-use reported although it is on PATH"

echo "ok install-use-family.sh"
