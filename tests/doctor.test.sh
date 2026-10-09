#!/bin/sh
# Runs use-family's doctor.sh with no *-use CLI installed, as an Intel and an Apple Silicon Mac
# (fake uname), and checks which CLIs it names and with what install hint.
#   sh tests/doctor.test.sh
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin" "$TMP/home"
cat > "$TMP/bin/uname" <<'UNAME'
#!/bin/sh
case "$1" in -m) echo "$FAKE_ARCH" ;; *) echo Darwin ;; esac
UNAME
chmod +x "$TMP/bin/uname"
# Only the shell itself: no *-use CLI and no system tool that doctor.sh might find.
ln -s "$(command -v sh)" "$TMP/bin/sh"

run() {  # run <arch>: doctor.sh's stdout on a Mac with that arch
  FAKE_ARCH=$1 HOME="$TMP/home" PATH="$TMP/bin" sh "$ROOT/plugins/use-family/scripts/doctor.sh"
}
fail() { echo "FAIL: $1"; echo "$out"; exit 1; }

out=$(run x86_64)
echo "$out" | grep -q 'not installed:.* wechat-use' && fail "Intel: suggests wechat-use, whose installer is Apple Silicon only"
echo "$out" | grep -qF 'cargo install --git https://github.com/leeguooooo/discord-use' || fail "Intel: no build-from-source hint for discord-use"
echo "$out" | grep -q 'discord-use/main/install.sh' && fail "Intel: points at discord-use's install.sh, which has no Intel binary"
echo "$out" | grep -q 'not installed:.* image-use' || fail "image-use not checked"
echo "$out" | grep -q 'image-use/main/install.sh' && fail "points at an install.sh image-use does not have"
echo "$out" | grep -qF 'ln -sf ~/.agents/use-family/image-use/image-use ~/.local/bin/image-use' || fail "no single-file install hint for image-use"

out=$(run arm64)
echo "$out" | grep -q 'not installed:.* wechat-use' || fail "Apple Silicon: wechat-use not checked"
echo "$out" | grep -qF 'leeguooooo/discord-use/main/install.sh | sh' || fail "Apple Silicon: lost discord-use's install.sh hint"

echo "ok doctor.sh"
