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

## More plugins coming

New plugins will be added here as they are released. Star the repo to follow updates.
