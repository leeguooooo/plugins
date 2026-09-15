#!/bin/sh
# use-family session-start check: name any missing *-use CLI and its one-line installer.
# Silent when everything is installed, so the common case adds nothing to the context.
# Only names the installer; the agent asks the user before running it.
PATH="$PATH:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin"

# iphone-use runs as a daemon and profile-use ships its script inside the skill,
# so neither has a CLI on PATH to look for.
names="chrome-use cookie-use mail-use discord-use bitwarden-use chatgpt-use"
[ "$(uname -s)" = Darwin ] && names="$names wechat-use"

missing=""
for name in $names; do
  command -v "$name" >/dev/null 2>&1 || missing="$missing $name"
done
[ -z "$missing" ] && exit 0

echo "use-family: these CLIs are not installed:$missing"
echo "Install one when a task needs it, after asking the user:"
for name in $missing; do
  echo "  curl -fsSL https://raw.githubusercontent.com/leeguooooo/$name/main/install.sh | sh"
done
