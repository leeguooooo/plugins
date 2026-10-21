#!/bin/sh
# Compatibility entry point. use upgrade is the installed, independently scheduled manager.
set -eu
PATH="$HOME/.local/bin:$PATH"
if command -v use >/dev/null 2>&1; then exec use upgrade "$@"; fi
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -f "$0" ] && [ -f "$root/install-use.sh" ]; then
  sh "$root/install-use.sh"
else
  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' EXIT
  curl -fsSL https://raw.githubusercontent.com/leeguooooo/plugins/main/install-use.sh -o "$tmp/install-use.sh"
  sh "$tmp/install-use.sh"
fi
exec "$HOME/.local/bin/use" upgrade "$@"
