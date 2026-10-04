#!/bin/sh
# use-family session-start: keep each *-use CLI at the version of its Claude Code plugin.
# Claude Code auto-updates the plugins (SKILL.md); this makes the CLIs follow. For every
# <name>@leeguooooo-plugins installed here whose CLI reports an older version than the plugin,
# it runs `<name> upgrade` (docs/upgrade.md). A CLI without `upgrade` is only named, with its
# installer, because some installers do more than swap a binary (wechat-use). bitwarden-use is
# skipped: its plugin carries its own hook. Silent when every CLI is current.
# Off with USE_NO_AUTO_UPGRADE or CI; per use with <NAME>_NO_AUTO_UPGRADE (e.g. MAIL_USE_NO_AUTO_UPGRADE).
PATH="$PATH:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin"
[ -n "${USE_NO_AUTO_UPGRADE:-}${CI:-}" ] && exit 0
plugins="$HOME/.claude/plugins/installed_plugins.json"
[ -f "$plugins" ] && command -v python3 >/dev/null 2>&1 || exit 0

names="chrome-use cookie-use iphone-use mail-use wechat-use discord-use chatgpt-use memory-use ocs message-use image-use paste-use motion-use"

# "<name> <plugin version>" for each installed plugin of the family (newest install per name)
installed=$(python3 - "$plugins" $names <<'EOF'
import json, re, sys
try:
    data = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
data = data.get("plugins", data)
key = lambda v: tuple(int(x) for x in v.split("."))
for name in sys.argv[2:]:
    entries = data.get(f"{name}@leeguooooo-plugins") or []
    if isinstance(entries, dict):
        entries = [entries]
    versions = [e.get("version", "") for e in entries]
    versions = [v for v in versions if re.fullmatch(r"\d+\.\d+\.\d+", v)]
    if versions:
        print(name, max(versions, key=key))
EOF
)
[ -n "$installed" ] || exit 0

# older A B: version A sorts strictly before version B
older() {
  [ "$1" != "$2" ] && [ "$(printf '%s\n%s\n' "$1" "$2" | sort -t. -k1,1n -k2,2n -k3,3n | head -n 1)" = "$1" ]
}
cli_version() {
  USE_NO_UPDATE_CHECK=1 "$1" --version 2>/dev/null | head -n 1 |
    grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1
}
has_upgrade() {  # same test as upgrade-use-family.sh
  "$1" --help 2>&1 | grep -qE "^[[:space:]]+($1[[:space:]]+)?upgrade([[:space:]]|\$)|\"name\":[[:space:]]*\"upgrade\""
}
repo_of() { case "$1" in ocs) echo open-cross-session ;; *) echo "$1" ;; esac; }
# Bound each upgrade when a timeout command exists (coreutils); the hook has its own limit too.
bounded() { if command -v timeout >/dev/null 2>&1; then timeout 240 "$@"; else "$@"; fi; }

state="${XDG_CACHE_HOME:-$HOME/.cache}/use-family"
mkdir -p "$state" || exit 0
log="$state/auto-upgrade.log"
# One run at a time across sessions; a lock older than 15 minutes is stale.
lock="$state/auto-upgrade.lock"
find "$lock" -maxdepth 0 -mmin +15 -exec rmdir {} \; 2>/dev/null
mkdir "$lock" 2>/dev/null || exit 0
trap 'rmdir "$lock" 2>/dev/null' EXIT

echo "$installed" | while read -r name want; do
  env_off=$(echo "$name" | tr 'a-z-' 'A-Z_')_NO_AUTO_UPGRADE
  eval "[ -n \"\${$env_off:-}\" ]" && continue
  command -v "$name" >/dev/null 2>&1 || continue  # not installed: doctor.sh names it
  have=$(cli_version "$name")
  [ -n "$have" ] && older "$have" "$want" || continue
  # A version that did not install is retried at most once an hour, not every session.
  skip="$state/$name.skip"
  if [ "$(cat "$skip" 2>/dev/null)" = "$want" ] && [ -z "$(find "$skip" -mmin +60 2>/dev/null)" ]; then
    continue
  fi
  if ! has_upgrade "$name"; then
    echo "$want" > "$skip"
    echo "use-family: $name CLI is $have but its plugin is $want, and this $name has no \`upgrade\` command. Tell the user; update with: curl -fsSL https://raw.githubusercontent.com/leeguooooo/$(repo_of "$name")/main/install.sh | sh"
    continue
  fi
  echo "$(date '+%F %T') $name $have -> $want" >> "$log"
  USE_NO_UPDATE_CHECK=1 bounded "$name" upgrade >> "$log" 2>&1 < /dev/null
  now=$(cli_version "$name")
  echo "$(date '+%F %T') $name now ${now:-?}" >> "$log"
  if [ -n "$now" ] && ! older "$now" "$want"; then
    rm -f "$skip"
    echo "use-family: upgraded the $name CLI $have -> $now to match its plugin."
  else
    echo "$want" > "$skip"
    echo "use-family: $name CLI is ${now:-$have} but its plugin is $want, and \`$name upgrade\` did not get there (see $log). Tell the user."
  fi
done
