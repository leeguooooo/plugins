# leeguooooo/plugins

Developer plugins for Claude Code.

## Add this marketplace

```
/plugin marketplace add leeguooooo/plugins
```

---

## Plugins

### [curl-crypto-plugin](https://github.com/leeguooooo/curl-crypto-plugin)

Decrypt encrypted curl request parameters and encrypt payloads for test-service calls.

**Claude Code:** `/plugin install curl-crypto-plugin@leeguooooo-plugins`

### [wrangler-accounts](https://github.com/leeguooooo/wrangler-accounts)

Cloudflare Wrangler multi-account helper. AWS-style profiles with a guard hook that blocks raw `wrangler` calls when local profiles are configured.

**Claude Code:** `/plugin install wrangler-accounts@leeguooooo-plugins`

---

### [claude-statusbar](https://github.com/leeguooooo/claude-code-usage-bar)

Lightweight Claude Code statusLine monitor. 3 styles (classic / capsule / hairline) × 7 themes (graphite / twilight / linen / nord / dracula / sakura / mono) and a multi-track time-driven pet animation. `/statusbar` slash commands included.

**Claude Code:**
```
/plugin install claude-statusbar@leeguooooo-plugins
pip install claude-statusbar    # or: uv tool install claude-statusbar
cs --setup
```

The plugin only carries the slash commands; the actual statusLine renderer is the `cs` CLI from PyPI.

---

## The `*-use` family

Agent-native CLIs that let coding agents drive real, logged-in surfaces — a browser, a phone, WeChat, Discord, a password vault, a private notes repo, the clipboard history — and talk to each other (`ocs`, from [open-cross-session](https://github.com/leeguooooo/open-cross-session)). Each plugin ships the agent skill; the CLI binary self-installs on first use (GitHub Release, no npm, no token).

## The *-use family in one install

```
/plugin marketplace add leeguooooo/plugins
/plugin install use-family@leeguooooo-plugins
```

`use-family` installs every `*-use` plugin below as a dependency, adds a `use-family` skill that tells the agent which one to reach for and how they combine, and checks at session start for any missing CLI (it only names the one-line installer; nothing runs without asking).

**Codex and the ChatGPT desktop app.** Add the same marketplace, then add the uses you want. Codex doesn't install plugin dependencies, so `use-family` there brings in the routing skill alone; add each `*-use` by name:

```sh
codex plugin marketplace add leeguooooo/plugins
codex plugin add use-family@leeguooooo-plugins
codex plugin add chrome-use@leeguooooo-plugins   # and mail-use, memory-use, …
```

The marketplace also shows up in the ChatGPT desktop app's Plugins Directory. `codex plugin marketplace upgrade leeguooooo-plugins` refreshes it.

**Any other agent that reads `~/.agents/skills`.** Use the installer. It clones every `*-use` into `~/.agents/use-family` and links each skill into `~/.agents/skills`; run it again to update.

```sh
curl -fsSL https://raw.githubusercontent.com/leeguooooo/plugins/main/install-use-family.sh | sh
```

Windows (PowerShell; skips the macOS-only uses):

```powershell
irm https://raw.githubusercontent.com/leeguooooo/plugins/main/install-use-family.ps1 | iex
```

A skill that already exists as a real folder is left alone and reported. Some uses (wechat-use, iphone-use) have installers that keep their skill folder in step with the CLI they install; leave those. A copy from `npx skills add` can be deleted so the installer links an updatable checkout instead. A link you made yourself (to your own checkout) is kept. The installer doesn't install CLIs; it lists the missing ones with their one-line installers. memory-use also needs `memory-use init --repo <owner>/<notes>` once (`--create` for a new private notes repo).

**Upgrading.** Every CLI in the family has `<name> upgrade` (updates the CLI and its skill, `--check` to only look) and prints one line on stderr when a newer release exists, at most once a day; see [docs/upgrade.md](docs/upgrade.md). To upgrade everything at once:

```sh
curl -fsSL https://raw.githubusercontent.com/leeguooooo/plugins/main/upgrade-use-family.sh | sh
```

Claude Code plugins alone: `claude plugin update <name>@leeguooooo-plugins`, then `/reload-plugins`.

ChatGPT on the web and mobile can't use these: the uses drive your own browser, mailbox and chat apps, and ChatGPT only installs plugins from OpenAI's directory.

<!-- use-family:start — this section is generated from .claude-plugin/marketplace.json by .github/workflows/auto-sync-versions.yml; edit descriptions there, not here -->

### [chrome-use](https://github.com/leeguooooo/chrome-use)

Browser automation CLI for AI agents — drive a real, logged-in Chrome with snapshot/@ref structured reads, stealth, and multi-agent tab isolation. The skill teaches agents the CLI; an MCP server mode (chrome-use mcp) covers no-shell hosts.

**Claude Code:** `/plugin install chrome-use@leeguooooo-plugins`

---

### [cookie-use](https://github.com/leeguooooo/cookie-use)

Agent-friendly multi-account session manager — capture, store, list, switch, and apply logged-in sessions for any website, across browsers and profiles. Encrypted local vault, built on chrome-use.

**Claude Code:** `/plugin install cookie-use@leeguooooo-plugins`

---

### [iphone-use](https://github.com/leeguooooo/iphone-use)

Computer-use, but for the iPhone — agents see and drive a real phone over macOS iPhone Mirroring. Low-latency WebRTC video, near-native touch, HTTP API + MCP.

**Claude Code:** `/plugin install iphone-use@leeguooooo-plugins`

---

### [image-use](https://github.com/leeguooooo/image-use)

Use your ChatGPT subscription to generate images from the command line — no OPENAI_API_KEY, no gateway, no daemon. Zero-dep Python CLI + AI-agent skill.

**Claude Code:** `/plugin install image-use@leeguooooo-plugins`

---

### [mail-use](https://github.com/leeguooooo/mail-use)

Email for AI agents — read, search, send and triage Gmail / QQ / 163 / any IMAP from the CLI or MCP. Part of the *-use family.

**Claude Code:** `/plugin install mail-use@leeguooooo-plugins`

---

### [message-use](https://github.com/leeguooooo/message-use)

iMessage & SMS for AI agents through macOS Messages — read, search, watch and send texts, and pull verification codes (短信验证码) out of incoming messages with `message-use code --wait`. Read-only database access; sending previews until confirmed.

**Claude Code:** `/plugin install message-use@leeguooooo-plugins`

---

### [paste-use](https://github.com/leeguooooo/paste-use)

Pastyx clipboard history for AI agents — list, search and read what you copied (text, links, code, images with recognised text, files), re-copy an old clip, or put text on the clipboard. Reads the app's local database read-only (no sign-in, works offline); secret-looking values are masked by default. macOS and Windows.

**Claude Code:** `/plugin install paste-use@leeguooooo-plugins`

---

### [wechat-use](https://github.com/leeguooooo/wechat-use)

WeChat CLI and MCP for macOS Apple Silicon and experimental Windows x64. Windows includes a standalone runtime without system Python; macOS also supports HTTP Bridge and Wechaty.

**Claude Code:** `/plugin install wechat-use@leeguooooo-plugins`

---

### [profile-use](https://github.com/leeguooooo/profile-use)

Safely fill registration, signup, checkout, banking, KYC, and onboarding forms from a private local personal profile — privacy-first, consent before submission.

**Claude Code:** `/plugin install profile-use@leeguooooo-plugins`

---

### [memory-use](https://github.com/leeguooooo/memory-use)

Portable long-term memory for AI coding agents — Markdown notes in a private git repo you own. Recall before work, write back after, background autosync, secret-scan hook, one-line new-computer setup.

**Claude Code:** `/plugin install memory-use@leeguooooo-plugins`

---

### [ocs](https://github.com/leeguooooo/open-cross-session)

open-cross-session — AI coding agents talking to each other: Claude Code, Codex and Pi sessions on this machine, and on paired machines on the same LAN over a mutually authenticated, encrypted link. Message, wake, delegate, get notified when a peer goes idle. One static binary, no server.

**Claude Code:** `/plugin install ocs@leeguooooo-plugins`

---

### [bitwarden-use](https://github.com/leeguooooo/bitwarden-use)

Bitwarden/Vaultwarden CLI with an ssh-agent-style background agent and FIDO2 passkey extraction — headless passkey logins, vault lookups, and a built-in SSH agent.

**Claude Code:** `/plugin install bitwarden-use@leeguooooo-plugins`

---

### [discord-use](https://github.com/leeguooooo/discord-use)

Fast REST-only Discord CLI + MCP server in one ~6 MB Rust binary. Drop-in replacement for mcp-discord — no gateway, no Node.js, sub-second start.

**Claude Code:** `/plugin install discord-use@leeguooooo-plugins`

---

### [chatgpt-use](https://github.com/leeguooooo/chatgpt-use)

Turn a ChatGPT web subscription into a coding-agent backend — no API key, no Codex billing. Ask/plan/review/delegate via the logged-in web conversation; built on chrome-use.

**Claude Code:** `/plugin install chatgpt-use@leeguooooo-plugins`

---

<!-- use-family:end -->

## More plugins coming

New plugins will be added here as they are released. Star the repo to follow updates.
