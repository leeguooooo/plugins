#!/bin/sh
# Install the unified use manager, not every family CLI. Add --auto to enable daily upgrades.
set -eu
command -v python3 >/dev/null 2>&1 || { echo 'Python 3.9+ is required' >&2; exit 1; }
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -f "$0" ] && [ -f "$root/plugins/use-family/scripts/use.py" ]; then
  exec python3 "$root/plugins/use-family/scripts/use.py" install --local "$@"
fi
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
curl -fsSL https://raw.githubusercontent.com/leeguooooo/plugins/main/plugins/use-family/scripts/use.py -o "$tmp/use.py"
python3 "$tmp/use.py" install "$@"
