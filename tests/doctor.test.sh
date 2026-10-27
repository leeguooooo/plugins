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
echo "$out" | grep -qF 'leeguooooo/plugins/main/install-clis.sh | sh' || fail "no all-at-once install-clis.sh line"
echo "$out" | grep -qF 'leeguooooo/discord-use/main/install.sh | sh' || fail "Intel: no discord-use installer (it has an Intel binary since v0.2.1)"
echo "$out" | grep -q 'not installed:.* image-use' || fail "image-use not checked"
echo "$out" | grep -qF 'leeguooooo/image-use/main/install.sh | sh' || fail "no image-use installer line"
echo "$out" | grep -qF 'leeguooooo/open-cross-session/main/install.sh | sh' || fail "ocs not mapped to its repo"
echo "$out" | grep -qF 'leeguooooo/session-flow/main/install.sh | sh' || fail "sflow not mapped to its repo"

out=$(run arm64)
echo "$out" | grep -q 'not installed:.* wechat-use' || fail "Apple Silicon: wechat-use not checked"

# image-use's plugin installed, its CLI missing: name the one command that installs it.
mkdir -p "$TMP/home/.claude/plugins"
echo '{"plugins":{"image-use@leeguooooo-plugins":[{"version":"1.0.0"}]}}' > "$TMP/home/.claude/plugins/installed_plugins.json"
out=$(run arm64)
echo "$out" | grep -q 'plugins are installed but their CLIs are missing: image-use$' || fail "plugin-installed image-use not singled out"
echo "$out" | grep -qF 'installer lines below' || fail "no fallback hint without use on PATH"
printf '#!/bin/sh\n' > "$TMP/bin/use"; chmod +x "$TMP/bin/use"
out=$(run arm64)
echo "$out" | grep -qF 'run: use install image-use' || fail "no use install command"

echo "ok doctor.sh"
