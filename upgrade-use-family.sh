#!/bin/sh
# Compatibility entry point. use update is the installed, independently scheduled manager.
set -eu
PATH="$HOME/.local/bin:$PATH"
family_update() {
  # Older managers used upgrade for the family and have no update subcommand.
  if "$1" update --help >/dev/null 2>&1; then
    manager=$1; shift; exec "$manager" update "$@"
  else
    manager=$1; shift; exec "$manager" upgrade "$@"
  fi
}
if command -v use >/dev/null 2>&1; then family_update use "$@"; fi
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -f "$0" ] && [ -f "$root/install-use.sh" ]; then
  sh "$root/install-use.sh"
else
  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' EXIT
  curl -fsSL https://raw.githubusercontent.com/leeguooooo/plugins/main/install-use.sh -o "$tmp/install-use.sh"
  sh "$tmp/install-use.sh"
fi
family_update "$HOME/.local/bin/use" "$@"
