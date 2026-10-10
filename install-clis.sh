#!/bin/sh
# Install every *-use CLI this machine is missing, each through its own install.sh, in one go.
#   curl -fsSL https://raw.githubusercontent.com/leeguooooo/plugins/main/install-clis.sh | sh
#   curl -fsSL https://raw.githubusercontent.com/leeguooooo/plugins/main/install-clis.sh | sh -s -- mail-use ocs
# With names, installs just those (iphone-use too, which needs an iPhone and isn't in the default set).
# Installed CLIs are left alone: `<name> upgrade`, or upgrade-use-family.sh, updates them.
# The plugins / skills come from `/plugin install use-family@leeguooooo-plugins` or
# install-use-family.sh; this only puts the CLIs on PATH. One failure doesn't stop the rest.
set -u
PATH="$PATH:$HOME/.local/bin"
RAW="${USE_FAMILY_RAW:-https://raw.githubusercontent.com/leeguooooo}"

# Keep in step with plugins/use-family/scripts/doctor.sh.
os=$(uname -s); arch=$(uname -m)
names="chrome-use cookie-use mail-use discord-use bitwarden-use chatgpt-use memory-use ocs image-use profile-use"
case "$os" in MINGW*|MSYS*|CYGWIN*) ;; *) names="$names motion-use" ;; esac  # motion-use: macOS and Linux only
[ "$os" = Darwin ] && names="$names message-use paste-use thermo-use"
# wechat-use's macOS installer stops with "Apple Silicon only" on Intel.
[ "$os-$arch" = Darwin-arm64 ] && names="$names wechat-use"
[ $# -gt 0 ] && names="$*"

repo_of() { case "$1" in ocs) echo open-cross-session ;; *) echo "$1" ;; esac; }
installed() {  # installed <name>: already set up here
  case "$1" in
    # profile-use is a skill with a script, not a CLI; iphone-use is a daemon with an app.
    profile-use) [ -f "${USE_FAMILY_DIR:-$HOME/.agents/use-family}/profile-use/SKILL.md" ] ;;
    iphone-use) [ -d "$HOME/Applications/iPhoneUse.app" ] || [ -d /Applications/iPhoneUse.app ] ;;
    *) command -v "$1" >/dev/null 2>&1 ;;
  esac
}

tmp=$(mktemp -d) || exit 1
trap 'rm -rf "$tmp"' EXIT
done_list=""; skipped=""; failed=""
for name in $names; do
  if installed "$name"; then skipped="$skipped $name"; continue; fi
  echo "==> $name"
  url="$RAW/$(repo_of "$name")/main/install.sh"
  # Download first: in `curl | sh` a failed download is an empty script that "succeeds".
  if ! curl -fsSL --retry 2 -o "$tmp/$name.sh" "$url"; then
    echo "    could not download $url"; failed="$failed $name"; continue
  fi
  if sh "$tmp/$name.sh" < /dev/null; then done_list="$done_list $name"; else failed="$failed $name"; fi
done

echo
[ -n "$done_list" ] && echo "installed:$done_list"
[ -n "$skipped" ] && echo "already installed:$skipped"
[ -n "$failed" ] && echo "failed:$failed  (re-run to retry; each one's output is above)"
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *)
  echo "note: most CLIs live in ~/.local/bin; add it to PATH" ;;
esac
# One-time setup some of them need before they're useful.
case " $done_list $skipped " in *" memory-use "*)
  [ -f "$HOME/.config/memory-use/config.json" ] ||
    echo "next: memory-use init --repo <owner>/<notes>   (--create for a new private notes repo)" ;;
esac
case " $done_list " in *" mail-use "*) echo "next: add a mailbox: \`mail-use apple-mail import\` (takes Apple Mail's accounts) or \`mail-use account --help\`" ;; esac
case " $done_list " in *" message-use "*) echo "next: give your terminal Full Disk Access so message-use can read Messages" ;; esac
case " $done_list " in *" discord-use "*) echo "next: set DISCORD_TOKEN (a bot token) for discord-use" ;; esac
[ -z "$failed" ]
