#!/bin/sh
# use-family session-start check: name any missing *-use CLI and its one-line installer.
# Silent when everything is installed, so the common case adds nothing to the context.
# Only names the installers; the agent asks the user before running them.
PATH="$PATH:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin"

# iphone-use runs as a daemon and profile-use ships its script inside the skill,
# so neither has a CLI on PATH to look for.
# Keep the list in step with install-clis.sh at the repo root.
os=$(uname -s); arch=$(uname -m)
names="chrome-use cookie-use mail-use discord-use bitwarden-use chatgpt-use memory-use ocs image-use"
case "$os" in MINGW*|MSYS*|CYGWIN*) ;; *) names="$names motion-use" ;; esac  # motion-use: macOS and Linux only
[ "$os" = Darwin ] && names="$names message-use paste-use"
# wechat-use's macOS installer stops with "Apple Silicon only" on Intel, so don't suggest it there.
[ "$os-$arch" = Darwin-arm64 ] && names="$names wechat-use"

missing=""
for name in $names; do
  command -v "$name" >/dev/null 2>&1 || missing="$missing $name"
done

# memory-use is only useful once it knows which private repo holds the notes.
if command -v memory-use >/dev/null 2>&1 && [ ! -f "$HOME/.config/memory-use/config.json" ]; then
  echo "memory-use: no notes repo configured yet — run \`memory-use init --repo <owner>/<name>\` (add --create for a new private one), after asking the user."
fi
[ -z "$missing" ] && exit 0

echo "use-family: these CLIs are not installed:$missing"
echo "Install them when a task needs one, after asking the user. All at once:"
echo "  curl -fsSL https://raw.githubusercontent.com/leeguooooo/plugins/main/install-clis.sh | sh"
echo "Or one at a time:"
for name in $missing; do
  repo=$name; [ "$name" = ocs ] && repo=open-cross-session
  echo "  curl -fsSL https://raw.githubusercontent.com/leeguooooo/$repo/main/install.sh | sh"
done
