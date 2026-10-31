# Connecting the use family to agent hosts

Each `*-use` is a CLI plus an agent skill (`SKILL.md`); some also serve MCP. A host needs the CLI on
`PATH`, or an MCP entry for tools that have one, and the skill where it looks for skills.

## Install on any host

```sh
curl -fsSL https://raw.githubusercontent.com/leeguooooo/plugins/main/install-use-family.sh | sh
use bootstrap   # link installed skills into each detected host
use doctor      # JSON: missing CLIs, outdated CLIs, skills per host
```

`use doctor` exits 2 when a CLI is missing. Neither command needs `~/.claude`.

| Variable | Effect |
|---|---|
| `USE_HOSTS` | `auto` (default) scans existing host folders; or a list such as `agents,grok`. Known hosts: `claude`, `codex`, `agents`, `grok`, `cursor` |
| `GROK_SKILLS_DIR` | Overrides the Grok skills folder |
| `USE_PLUGIN_ROOT` | Plugin root for the bundled scripts when the host has no `CLAUDE_PLUGIN_ROOT` |
| `USE_NO_AUTOUPDATE` | Stops `use`'s scheduled updates and use-family's session-start CLI sync. Explicit `use update` still runs. Member CLIs' own update checks use `<NAME>_NO_UPDATE_CHECK` for now |

## Hosts

- **Claude Code**: add the marketplace and install the plugins; see the [README](../README.md).
- **Codex**: see the Codex list in the [README](../README.md).
- **Grok CLI, Cursor**: `install-use-family.sh` and `use bootstrap` link skills into `~/.grok/skills` and `~/.cursor/skills`.
- **Grok Bot**: its agent runs in a cloud x86_64 Linux VM, so links on your computer do not reach it. Install inside that VM. macOS-only and device-bound tools will not work there.
- **Claude Desktop and other MCP hosts**: add a stdio entry for each tool that serves MCP.

## MCP servers

```json
{"mcpServers": {"discord-use": {"command": "discord-use", "args": ["mcp"], "env": {"DISCORD_TOKEN": "<token>"}}}}
```

| Plugin | Command | Setup | Platforms | Risk |
|---|---|---|---|---|
| chrome-use | see its README | Chrome extension | macOS, Windows, Linux | high: drives a logged-in browser |
| mail-use | see its README | mailbox account | all | high: reads and sends mail |
| discord-use | `discord-use mcp` | `DISCORD_TOKEN` | all | high: posts and deletes |
| iphone-use | see its README | paired device | macOS + iPhone | high: drives a real phone |
| android-use | see its README | adb; `ANDROID_SDK_ROOT`, `DEVICE_SERIAL` | all | high: drives a real phone |
| chatgpt-use | `chatgpt-use agent mcp` | ChatGPT login | all | medium: uses your account |

Other members are CLI-only today, so hosts without a shell cannot use them yet ([#59](https://github.com/leeguooooo/plugins/issues/59)).
Hosts with no hooks get no automatic memory-use recall ([#58](https://github.com/leeguooooo/plugins/issues/58)).

See [License and commercial use](../README.md#license-and-commercial-use) before shipping any of these in a product.
