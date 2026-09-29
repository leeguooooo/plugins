#!/bin/sh
# Upgrade every installed *-use: each CLI through its own `upgrade` command, the skill
# checkouts made by install-use-family.sh, and the Claude Code plugins.
#   curl -fsSL https://raw.githubusercontent.com/leeguooooo/plugins/main/upgrade-use-family.sh | sh
# Convention: docs/upgrade.md.
set -u
BASE="${USE_FAMILY_DIR:-$HOME/.agents/use-family}"
PLUGINS="$HOME/.claude/plugins/installed_plugins.json"
NAMES="chrome-use cookie-use iphone-use mail-use wechat-use discord-use profile-use bitwarden-use chatgpt-use image-use memory-use ocs message-use"
failed=""

repo_of() {  # repo_of <name>: the GitHub repo a use lives in
  case "$1" in ocs) echo open-cross-session ;; *) echo "$1" ;; esac
}

has_upgrade() {  # the CLI lists an `upgrade` subcommand in its help (text, or JSON when piped, e.g. mail-use);
  # usage lines may repeat the program name ("  ocs upgrade [--check]")
  "$1" --help 2>&1 | grep -qE "^[[:space:]]+($1[[:space:]]+)?upgrade([[:space:]]|\$)|\"name\":[[:space:]]*\"upgrade\""
}

echo "== CLIs"
for name in $NAMES; do
  command -v "$name" >/dev/null 2>&1 || continue
  if has_upgrade "$name"; then
    echo "-- $name"
    "$name" upgrade || failed="$failed $name"
  else
    echo "-- $name: no upgrade command in this version; reinstall to get it:"
    echo "   curl -fsSL https://raw.githubusercontent.com/leeguooooo/$(repo_of "$name")/main/install.sh | sh"
  fi
done

if [ -d "$BASE" ]; then
  echo "== skills from install-use-family.sh ($BASE)"
  for dir in "$BASE"/*/; do
    [ -d "$dir.git" ] || continue
    name=$(basename "$dir")
    if git -C "$dir" pull -q --ff-only; then echo "-- $name updated"; else echo "-- $name: not updated (local changes?)"; failed="$failed $name-skill"; fi
  done
fi

if command -v claude >/dev/null 2>&1 && [ -f "$PLUGINS" ]; then
  echo "== Claude Code plugins"
  claude plugin marketplace update leeguooooo-plugins >/dev/null 2>&1 || true
  for name in use-family $NAMES; do
    grep -q "\"$name@leeguooooo-plugins\"" "$PLUGINS" || continue
    printf -- "-- %s: " "$name"
    claude plugin update "$name@leeguooooo-plugins" 2>&1 | tail -1
  done
  echo "Restart Claude Code (or /reload-plugins) to load updated plugins."
fi

if [ -n "$failed" ]; then
  echo
  echo "Some upgrades did not finish:$failed"
  exit 2
fi
