#!/bin/sh
# Install the *-use family as agent skills for Codex and any other agent that reads
# ~/.agents/skills. Claude Code users: /plugin install use-family@leeguooooo-plugins instead.
#   curl -fsSL https://raw.githubusercontent.com/leeguooooo/plugins/main/install-use-family.sh | sh
# Re-run to update: every use is a git checkout under ~/.agents/use-family, linked into
# ~/.agents/skills. CLIs are not installed here; missing ones are listed with their installer.
set -eu
BASE="${USE_FAMILY_DIR:-$HOME/.agents/use-family}"
SKILLS="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}"
command -v git >/dev/null 2>&1 || { echo "error: git is required" >&2; exit 1; }
mkdir -p "$BASE" "$SKILLS"

# <name>[=<repo>]:<skill directory inside the repo>; "." means SKILL.md sits at the repo root.
# The repo defaults to the name; ocs lives in leeguooooo/open-cross-session, sflow in leeguooooo/session-flow.
# Keep in step with .claude-plugin/marketplace.json.
USES="chrome-use:skills/chrome-use cookie-use:skills/cookie-use iphone-use:skills/iphone-use android-use:skills/android-use
mail-use:skills/mail-use wechat-use:. discord-use:skills/discord-use profile-use:. bitwarden-use:.
chatgpt-use:. image-use:skills/image-use memory-use:. ocs=open-cross-session:skills/ocs sflow=session-flow:skills/sflow message-use:skills/message-use motion-use:.
paste-use:skills/paste-use thermo-use:skills/thermo-use switch-use:skills/switch-use"
# Uses that ship a CLI on PATH (iphone-use runs as a daemon, profile-use as a script in its skill;
# switch-use needs a homebrew Switch, so it is installed only by name).
CLIS="android-use chrome-use cookie-use mail-use discord-use bitwarden-use chatgpt-use memory-use ocs motion-use image-use"

repo_of() {  # repo_of <name>: the GitHub repo a use lives in
  case "$1" in ocs) echo open-cross-session ;; sflow) echo session-flow ;; *) echo "$1" ;; esac
}
[ "$(uname -s)" = Darwin ] && CLIS="$CLIS message-use paste-use thermo-use"
# sflow drives tmux sessions: macOS and Linux.
case "$(uname -s)" in Darwin|Linux) CLIS="$CLIS sflow" ;; esac
# wechat-use's macOS installer stops with "Apple Silicon only" on Intel, so don't suggest it there.
[ "$(uname -s)-$(uname -m)" = Darwin-arm64 ] && CLIS="$CLIS wechat-use"

failed=""
fetch() {  # fetch <repo> <dir>; a failure is reported and recorded, never fixed by force
  if [ ! -d "$2/.git" ]; then
    git clone -q --depth 1 "https://github.com/leeguooooo/$1.git" "$2" && return
    echo "warn   $1: clone failed"; failed="$failed $1"; return
  fi
  if ! git -C "$2" fetch -q; then
    echo "warn   $1: not updated, fetch failed (network?)"; failed="$failed $1"; return
  fi
  git -C "$2" merge -q --ff-only '@{u}' && return
  failed="$failed $1"
  if [ -n "$(git -C "$2" status --porcelain 2>/dev/null)" ]; then
    echo "warn   $1: not updated, $2 has local changes; commit or stash them and re-run"
  else
    echo "warn   $1: not updated, its history no longer fast-forwards to origin (upstream was rewritten)"
    echo "       your checkout is untouched; to recover, back it up and re-run:  mv \"$2\" \"$2.bak\""
  fi
}

link() {  # link <target dir> <skill name>; never replaces a real directory or your own link
  dest="$SKILLS/$2"
  if [ -e "$dest" ] && [ ! -L "$dest" ]; then
    echo "skip   $2: left alone (a real directory, possibly kept current by $2's own installer)"
    return
  fi
  if [ -L "$dest" ]; then
    case "$(readlink "$dest")" in
      "$BASE"/*) ;;
      *) echo "keep   $2: already linked to $(readlink "$dest")"; return ;;
    esac
  fi
  ln -sfn "$1" "$dest" && echo "linked $2"
}

fetch plugins "$BASE/plugins"
[ -d "$BASE/plugins/.git" ] && link "$BASE/plugins/plugins/use-family/skills/use-family" use-family

for entry in $USES; do
  head=${entry%%:*}; sub=${entry#*:}; name=${head%%=*}
  fetch "$(repo_of "$name")" "$BASE/$name"
  [ -d "$BASE/$name/.git" ] || continue
  target="$BASE/$name"; [ "$sub" = . ] || target="$target/$sub"
  # A checkout kept at the old root layout is still usable if its update failed,
  # or while the installer and Skill repository releases are rolling out.
  if { [ "$name" = thermo-use ] || [ "$name" = paste-use ] || [ "$name" = message-use ] || [ "$name" = discord-use ] || [ "$name" = image-use ] || [ "$name" = switch-use ]; } && [ ! -f "$target/SKILL.md" ] && [ -f "$BASE/$name/SKILL.md" ]; then
    target="$BASE/$name"
  fi
  if [ -f "$target/SKILL.md" ]; then link "$target" "$name"; else echo "warn   $name: no SKILL.md at $sub"; fi
done

# The manager itself is small and local to this already trusted checkout. It does not
# install missing family CLIs or enable background scheduling without explicit consent.
manager="$BASE/plugins/plugins/use-manager/scripts/use.py"
if [ -f "$manager" ] && command -v python3 >/dev/null 2>&1; then
  python3 "$manager" install --local || failed="$failed use-manager"
fi

missing=""
for name in $CLIS; do command -v "$name" >/dev/null 2>&1 || missing="$missing $name"; done
echo
echo "Skills are in $SKILLS. Start a new Codex session to pick them up."
if [ -n "$missing" ]; then
  echo "CLIs not installed yet:$missing"
  echo "Install them all at once:"
  echo "  curl -fsSL https://raw.githubusercontent.com/leeguooooo/plugins/main/install-clis.sh | sh"
  echo "Or one at a time:"
  for name in $missing; do
    echo "  curl -fsSL https://raw.githubusercontent.com/leeguooooo/$(repo_of "$name")/main/install.sh | sh"
  done
fi
if [ -n "$failed" ]; then
  echo
  echo "Not updated:$failed  (each one's reason is above; their old skills stay linked)"
  exit 1
fi
