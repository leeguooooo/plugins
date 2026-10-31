#!/bin/sh
# use-family session-start check: name any missing *-use CLI and its one-line installer.
# Silent when everything is installed, so the common case adds nothing to the context.
# Only names the installers; the agent asks the user before running them.
PATH="$PATH:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin"

# iphone-use runs as a daemon and profile-use ships its script inside the skill,
# so neither has a CLI on PATH to look for.
# Keep the list in step with install-clis.sh at the repo root.
os=$(uname -s); arch=$(uname -m)
names="android-use chrome-use cookie-use mail-use discord-use bitwarden-use chatgpt-use memory-use ocs image-use"
case "$os" in MINGW*|MSYS*|CYGWIN*) ;; *) names="$names motion-use sflow" ;; esac  # motion-use, sflow: macOS and Linux only
[ "$os" = Darwin ] && names="$names message-use paste-use thermo-use"
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

# A member whose plugin is installed but whose CLI is missing: its skill is offered to the agent
# yet cannot run, so name the one command that fixes it. Still the user's call (installers write
# to their machine), so the agent asks first; \`use install\` runs the same owner installer.
# use.py owns the host registry; without python3 (or on a host with no plugins) this hint is skipped.
ROOT=${USE_PLUGIN_ROOT:+$USE_PLUGIN_ROOT/scripts}
ROOT=${ROOT:-${0%/*}}
wanted=""
if command -v python3 >/dev/null 2>&1; then
  installed=$(python3 "$ROOT/use.py" plugins 2>/dev/null) || installed=""
  for name in $missing; do
    case "
$installed" in *"
$name "*) wanted="$wanted $name" ;; esac
  done
fi
if [ -n "$wanted" ]; then
  echo "use-family: these plugins are installed but their CLIs are missing:$wanted"
  if command -v use >/dev/null 2>&1; then
    echo "Their skills cannot run until installed. Ask the user once, then run: use install$wanted"
  else
    echo "Their skills cannot run until installed. Ask the user once, then run the installer lines below."
  fi
fi

echo "use-family: these CLIs are not installed:$missing"
echo "Install them when a task needs one, after asking the user. All at once:"
echo "  curl -fsSL https://raw.githubusercontent.com/leeguooooo/plugins/main/install-clis.sh | sh"
echo "Or one at a time:"
for name in $missing; do
  repo=$name; [ "$name" = ocs ] && repo=open-cross-session; [ "$name" = sflow ] && repo=session-flow
  echo "  curl -fsSL https://raw.githubusercontent.com/leeguooooo/$repo/main/install.sh | sh"
done
