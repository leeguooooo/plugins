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
# The repo defaults to the name; ocs lives in leeguooooo/open-cross-session.
# Keep in step with .claude-plugin/marketplace.json.
USES="chrome-use:skills/chrome-use cookie-use:skills/cookie-use iphone-use:skills/iphone-use
mail-use:skills/mail-use wechat-use:. discord-use:. profile-use:. bitwarden-use:.
chatgpt-use:. image-use:. memory-use:. ocs=open-cross-session:skills/ocs message-use:. motion-use:.
paste-use:."
# Uses that ship a CLI on PATH (iphone-use runs as a daemon, profile-use as a script in its skill).
CLIS="chrome-use cookie-use mail-use discord-use bitwarden-use chatgpt-use memory-use ocs motion-use"

repo_of() {  # repo_of <name>: the GitHub repo a use lives in
  case "$1" in ocs) echo open-cross-session ;; *) echo "$1" ;; esac
}
[ "$(uname -s)" = Darwin ] && CLIS="$CLIS wechat-use message-use paste-use"

fetch() {  # fetch <repo> <dir>
  if [ -d "$2/.git" ]; then
    git -C "$2" pull -q --ff-only || echo "warn   $1: not updated (local changes?)"
  else
    git clone -q --depth 1 "https://github.com/leeguooooo/$1.git" "$2"
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
link "$BASE/plugins/plugins/use-family/skills/use-family" use-family

for entry in $USES; do
  head=${entry%%:*}; sub=${entry#*:}; name=${head%%=*}
  fetch "$(repo_of "$name")" "$BASE/$name"
  target="$BASE/$name"; [ "$sub" = . ] || target="$target/$sub"
  if [ -f "$target/SKILL.md" ]; then link "$target" "$name"; else echo "warn   $name: no SKILL.md at $sub"; fi
done

missing=""
for name in $CLIS; do command -v "$name" >/dev/null 2>&1 || missing="$missing $name"; done
echo
echo "Skills are in $SKILLS. Start a new Codex session to pick them up."
if [ -n "$missing" ]; then
  echo "CLIs not installed yet:$missing"
  for name in $missing; do
    echo "  curl -fsSL https://raw.githubusercontent.com/leeguooooo/$(repo_of "$name")/main/install.sh | sh"
  done
fi
