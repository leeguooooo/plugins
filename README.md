# leeguooooo/plugins

Developer plugins for Claude Code and Cursor.

## Add this marketplace

**Claude Code:**
```
/plugin marketplace add leeguooooo/plugins
```

**Cursor:** Open Settings → Plugins → Marketplace, then add `leeguooooo/plugins`.

---

## Plugins

### [language-coach](https://github.com/leeguooooo/prompt-language-coach)

Real-time language coaching in every prompt. Corrects your writing and provides natural, native-like expressions automatically. Supports any language pair.

**Claude Code:**
```
/plugin install language-coach@leeguooooo-plugins
/reload-plugins
/language-coach:language-coach setup
```

**Cursor:** Install **language-coach** from the marketplace, then run `/language-coach setup` in the AI panel.

---

### [zentao-plugin](https://github.com/leeguooooo/zentao-plugin)

Use ZenTao from Claude Code via the local zentao CLI. Inspect products, bugs, tasks, stories, and run self-test workflows.

**Claude Code:** `/plugin install zentao-plugin@leeguooooo-plugins`

---

### [yapi-plugin](https://github.com/leeguooooo/yapi-plugin)

Use YApi from Claude Code via the local yapi CLI. Inspect interfaces and sync API docs automatically.

**Claude Code:** `/plugin install yapi-plugin@leeguooooo-plugins`

---

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

Agent-native CLIs that let coding agents drive real, logged-in surfaces — a browser, a phone, WeChat, Discord, a password vault. Each plugin ships the agent skill; the CLI binary self-installs on first use (GitHub Release, no npm, no token).

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

### [wechat-use](https://github.com/leeguooooo/wechat-use)

macOS WeChat CLI + local HTTP bridge + Wechaty Puppet gRPC gateway — send messages, query sessions/contacts/chat history/images, and expose stable HTTP/gRPC surfaces for agent integration.

**Claude Code:** `/plugin install wechat-use@leeguooooo-plugins`

---

### [profile-use](https://github.com/leeguooooo/profile-use)

Safely fill registration, signup, checkout, banking, KYC, and onboarding forms from a private local personal profile — privacy-first, consent before submission.

**Claude Code:** `/plugin install profile-use@leeguooooo-plugins`

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

### [pixcake-use](https://github.com/leeguooooo/pixcake-use)

Local read-only PixCake probing CLI: snapshot/diff, SQLite inspection, verified pf-parameter codebook, RAW preview + approximate offline grade. Your own account, your own photos.

**Claude Code:** `/plugin install pixcake-use@leeguooooo-plugins`

---

<!-- use-family:end -->

## More plugins coming

New plugins will be added here as they are released. Star the repo to follow updates.
