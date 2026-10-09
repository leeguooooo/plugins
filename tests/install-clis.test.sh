#!/bin/sh
# Runs install-clis.sh with a fake curl (each "installer" just drops a CLI into ~/.local/bin),
# a fake uname and an isolated HOME. Checks which CLIs it installs per platform, that it skips
# installed ones, keeps going past a failure and reports it. Nothing outside a temp dir is touched.
#   sh tests/install-clis.test.sh
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin"
cat > "$TMP/bin/uname" <<'UNAME'
#!/bin/sh
case "$1" in -m) echo "$FAKE_ARCH" ;; *) echo Darwin ;; esac
UNAME
# Fake curl: -o <file> <url>; the "installer" for <repo> creates the CLI. $FAIL_REPO 404s.
cat > "$TMP/bin/curl" <<'CURL'
#!/bin/sh
out=""; url=""
while [ $# -gt 0 ]; do case "$1" in -o) out=$2; shift 2 ;; -*) shift ;; *) url=$1; shift ;; esac; done
repo=${url#*/leeguooooo/}; repo=${repo%%/*}
[ "$repo" = "${FAIL_REPO:-}" ] && exit 22
name=$repo; [ "$repo" = open-cross-session ] && name=ocs
if [ "$name" = profile-use ]; then
  printf 'mkdir -p "$HOME/.agents/use-family/profile-use"; touch "$HOME/.agents/use-family/profile-use/SKILL.md"\n' > "$out"
else
  printf 'mkdir -p "$HOME/.local/bin"; printf "#!/bin/sh\\n" > "$HOME/.local/bin/%s"; chmod +x "$HOME/.local/bin/%s"\n' "$name" "$name" > "$out"
fi
CURL
chmod +x "$TMP/bin/uname" "$TMP/bin/curl"
for tool in sh mkdir mktemp rm chmod touch printf cat; do
  p=$(command -v "$tool") && case "$p" in /*) ln -sf "$p" "$TMP/bin/$tool" ;; esac
done

fresh() { rm -rf "$TMP/home"; mkdir -p "$TMP/home"; }
run() {  # run <arch> [args]: install-clis.sh's output; status in $rc
  arch=$1; shift
  set +e; out=$(FAKE_ARCH=$arch HOME="$TMP/home" PATH="$TMP/bin" sh "$ROOT/install-clis.sh" "$@" 2>&1); rc=$?; set -e
}
fail() { echo "FAIL: $1"; echo "$out"; exit 1; }
has() { [ -x "$TMP/home/.local/bin/$1" ]; }

fresh; run x86_64
[ "$rc" = 0 ] || fail "Intel: exit $rc"
for n in chrome-use cookie-use mail-use discord-use bitwarden-use chatgpt-use memory-use ocs image-use motion-use message-use paste-use; do
  has "$n" || fail "Intel: $n not installed"
done
[ -f "$TMP/home/.agents/use-family/profile-use/SKILL.md" ] || fail "Intel: profile-use not installed"
has wechat-use && fail "Intel: ran wechat-use's Apple Silicon-only installer"
echo "$out" | grep -q '^next: memory-use init' || fail "no memory-use init hint"

run x86_64
echo "$out" | grep -q '^installed:' && fail "re-run installed something again"
echo "$out" | grep -q '^already installed:.* ocs' || fail "re-run: ocs not reported as already installed"

fresh; run arm64
has wechat-use || fail "Apple Silicon: wechat-use not installed"

fresh; FAIL_REPO=mail-use run arm64
[ "$rc" != 0 ] || fail "a failed install still exited 0"
echo "$out" | grep -q '^failed: mail-use' || fail "failure not reported"
has ocs || fail "stopped after a failure instead of carrying on"

fresh; run arm64 ocs iphone-use
has ocs || fail "named: ocs not installed"
has chrome-use && fail "named: installed more than it was asked"

echo "ok install-clis.sh"
