---
name: use-family
description: Routing guide for the *-use family (chrome-use, mail-use, image-use, wechat-use, discord-use, iphone-use, profile-use, bitwarden-use, cookie-use, chatgpt-use, memory-use, ocs). Use when a task spans more than one of them or it is unclear which to pick — signing up for a site, logging in, fetching a verification code, filling a form with personal data, switching accounts, messaging someone, setting up a new computer — or when the user asks "用哪个 use", "use 家族", "这些 use 怎么配合".
---

# use-family

Each `*-use` does one thing well. This skill says which one to reach for, and how to chain them without leaking anything.

## Who does what

| Layer | Use | Owns |
|---|---|---|
| Who I am | `profile-use` | Name, address, phone, IDs, bank details, family, document scans. Redacted by default. |
| | `bitwarden-use` | Passwords, passkeys, TOTP, secret keys. Reads prompt Touch ID outside its reveal folders. |
| | `cookie-use` | Logged-in sessions per site; many accounts on one site. Built on chrome-use. |
| How we did it | `memory-use` | Infra notes: NAS, VPN, servers, decisions, rollbacks — in the user's own private git repo, synced across computers. |
| Hands | `chrome-use` | The user's real, logged-in Chrome: navigate, read, fill, click, screenshot. |
| | `iphone-use` | A real iPhone through iPhone Mirroring: apps with no API. |
| Voice | `mail-use` | Every mailbox: search, read, send; verification codes and receipts. |
| | `wechat-use`, `discord-use` | Messages and history on WeChat and Discord. |
| Teammates | `ocs` | The other AI agents: Claude Code, Codex and Pi sessions on this machine, and on paired machines on the same LAN (`<address>@<peer>`). Message, wake, delegate, get notified when one goes idle. |
| Second brain | `chatgpt-use` | The user's ChatGPT web subscription as an extra reviewer or planner. Built on chrome-use. |
| | `image-use` | Image generation on the user's own subscriptions: ChatGPT web first, Codex fallback, optional Gemini. |

Pick by target:

- A web page → `chrome-use`. A native macOS app → the host's own computer use (Claude Code: enable `computer-use` in `/mcp`; Codex: its built-in computer use); `peekaboo` for scripted or non-interactive runs. A phone app → `iphone-use`.
- A personal value to type into a form → `profile-use values`. A password or TOTP → `bitwarden-use` (via `profile-use login --domain`). Never the other way round.
- Another agent session — hand off work, ask a question, wait for it to finish → `ocs` (`ocs who`, then `ocs dm <name> "…"`; `--notify-when-idle` instead of polling). An agent on another computer the user paired → `ocs dm <address>@<peer>`; pairing (`ocs lan pair`) lets that machine prompt this one's agents, so only when the user asks.
- A durable fact about the person → `profile-use`. A durable fact about how a machine or service is set up → `memory-use`, which stores only pointers to profile-use, never the values.

## Recipes

**Sign up for a site**
1. `chrome-use` opens the signup page. Check the real domain first.
2. `profile-use values <fields>` for name, email, phone, address; ask before any high-sensitivity field.
3. `mail-use` finds the verification mail and extracts the code.
4. Generate and store the new password in `bitwarden-use`; never echo it.
5. Stop before the final submit and get the user's explicit yes.
6. `cookie-use` saves the session if the user juggles accounts there. Any gotcha → `memory-use`.

**Log in**
`profile-use login --domain <host>` matches the vault entry by its stored URI without revealing; add `--reveal` only at the moment of filling (one Touch ID). Several matches → ask which, using `--name`/`--user`.

**Reach someone**
A person: use the channel the user named. Another agent (a Claude, Codex or Pi session): `ocs`, never the user's chat apps. Draft first; send only after a yes. Never paste profile or vault values into a message unless the user asked for exactly that.

**New computer**
On the old computer, `memory-use migrate` first. On the new one:
1. `curl -fsSL https://raw.githubusercontent.com/leeguooooo/memory-use/main/install.sh | sh -s -- --repo <owner>/<notes>` brings back the notes and `setup-new-computer.md`; follow that guide.
2. `profile-use restore --identity-rbw "profile-use age key"` brings the encrypted profile back.

## Upgrade

Each CLI prints `<name> X is available` on stderr when a newer release exists (at most once a day). Tell the user and offer `<name> upgrade`, which updates the CLI and its skill; `<name> upgrade --check` only looks. When the user says "升级 use 全家" / "upgrade everything", run `curl -fsSL https://raw.githubusercontent.com/leeguooooo/plugins/main/upgrade-use-family.sh | sh` after they agree.

## Rules that hold across the family

1. Consent before anything outward-facing: submit, send, pay, upload a document.
2. Redacted by default. Raw values only at the moment of use, never in the final reply.
3. Never bypass a Touch ID or unlock prompt, and never handle the master password.
4. Before committing to any repo that could echo personal data, run `profile-use leak-scan --staged --all-profiles`.
5. A CLI is missing → this plugin's session-start check names the one-line installer; ask the user before running it.
