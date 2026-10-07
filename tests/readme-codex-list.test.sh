#!/bin/sh
# The README's Codex loop must name every use-family dependency, or Codex users silently miss one.
#   sh tests/readme-codex-list.test.sh
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
want=$(jq -r '.dependencies[]' "$ROOT/plugins/use-family/.claude-plugin/plugin.json" | sort)
line=$(grep '^for plugin in use-family ' "$ROOT/README.md") || { echo "FAIL: no Codex install loop in README.md"; exit 1; }
got=$(echo "$line" | sed 's/^for plugin in use-family //; s/; do$//' | tr ' ' '\n' | sort)
if [ "$want" != "$got" ]; then
  echo "FAIL: README Codex loop differs from use-family dependencies"
  echo "want:" $want; echo "got: " $got
  exit 1
fi
jq -e '[.plugins[].name] | index("curl-crypto-plugin") | not' "$ROOT/.claude-plugin/marketplace.json" >/dev/null \
  || { echo "FAIL: curl-crypto-plugin is back in marketplace.json"; exit 1; }
echo "ok README Codex list"
