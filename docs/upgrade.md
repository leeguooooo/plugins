# Upgrade convention for the *-use family

People install a use in different ways: the Claude Code plugin, `npx skills add`, a repo's
`install.sh`, a git clone, or `install-use-family.sh`. Whatever the route, everyone ends up
with the CLI and a SKILL.md. So the upgrade path lives in those two places.

## 1. `<name> upgrade`

Every use that ships a CLI has an `upgrade` subcommand with the same behaviour:

| Invocation | Does |
|---|---|
| `<name> upgrade` | Installs the latest GitHub release of the CLI through the same route it was installed with (normally the repo's `install.sh` / release binary), then refreshes the skill (section 3). Prints what changed. |
| `<name> upgrade --check` | Changes nothing. Prints `<name> <current> -> <latest>` or `<name> <current> is up to date`. |
| `<name> upgrade --json` | Same as `--check`, as JSON (below). |

`--json` output:

```json
{
  "name": "chrome-use",
  "current": "1.5.140",
  "latest": "1.5.141",
  "update_available": true,
  "skills": [
    {"channel": "claude-plugin", "path": "...", "update": "claude plugin update chrome-use@leeguooooo-plugins"}
  ]
}
```

Exit codes: `0` success (upgraded, or already current, or a check that ran), `2` the check or
download failed (network, GitHub API). An update being available is not an error.

- The latest version is the newest non-prerelease GitHub release of `leeguooooo/<name>`
  (tag `vX.Y.Z`). Use `https://api.github.com/repos/leeguooooo/<name>/releases/latest`
  with a short timeout; honour `GITHUB_TOKEN` if set.
- If a use already has an equivalent command (`update`), keep it and add `upgrade` as the
  name the docs use. Do not break existing commands.
- Never ask for or handle credentials. Never upgrade without being invoked — except that a
  Claude Code plugin install keeps its CLI at the plugin's version (section 6).

## 2. Daily "new version" notice

Any CLI invocation may check for a newer release, at most once per 24 hours:

- Cache the result in `${XDG_CACHE_HOME:-~/.cache}/<name>/update-check.json`
  (`{"checked_at": <unix>, "latest": "X.Y.Z"}`). Network timeout 2 seconds; any failure is
  silent and still updates `checked_at` so an offline machine is not retried every call.
- When the cached latest is newer than the running version, print exactly one line to
  **stderr**, never stdout (stdout may be JSON another program parses):
  `<name> <latest> is available (you have <current>). Upgrade: <name> upgrade`
- Skip the check and the notice when any of these is set: `CI`,
  `<NAME>_NO_UPDATE_CHECK` (upper-case name, `-` → `_`, e.g. `CHROME_USE_NO_UPDATE_CHECK`),
  or the family-wide `USE_NO_UPDATE_CHECK`. Also skip for `upgrade`, `--version` and `--help`.
- The check must not slow the command down: use the cache when fresh; when stale, check
  with the 2 s timeout (or in the background if the language makes that easy).

Agents see stderr, so they learn about the update without the user knowing any command.

## 3. Refreshing the skill

Upgrading the binary does not move a SKILL.md that was copied elsewhere. `upgrade` looks for
the skill in each place below and refreshes what it finds:

| Channel | How to detect | Refresh |
|---|---|---|
| Claude Code plugin | `~/.claude/plugins/installed_plugins.json` has a key starting `"<name>@` | run `claude plugin update <name>@leeguooooo-plugins` if `claude` is on PATH, else print it |
| Git checkout | `~/.agents/skills/<name>` (or `~/.claude/skills/<name>`, `~/.codex/skills/<name>`) resolves inside a git work tree | `git -C <root> pull --ff-only`; on failure print why, don't force |
| Copied folder (e.g. `npx skills add`) | a real directory with a SKILL.md | print `npx skills update <name>` (don't run it) |
| Installer-managed | the use's own installer owns the folder (wechat-use, iphone-use) | the installer run in step 1 already refreshed it |

Report each skill found with its channel in the output and in `--json` (`skills` array).

## 4. SKILL.md "Upgrade" section

Every SKILL.md gets this section (adapt names; keep it short):

```markdown
## Upgrade

When any `<name>` command prints `<name> X is available`, tell the user and offer to run
`<name> upgrade` (it updates the CLI and this skill). Check without changing anything:
`<name> upgrade --check`. The user may also just say "升级 <name>" / "upgrade <name>".

If the skill came from somewhere `upgrade` can't refresh:
- Claude Code plugin: `claude plugin update <name>@leeguooooo-plugins`
- Whole family: `curl -fsSL https://raw.githubusercontent.com/leeguooooo/plugins/main/upgrade-use-family.sh | sh`
```

## 5. Whole family

`upgrade-use-family.sh` in this repo runs `<name> upgrade` for every installed use and
refreshes skills installed by `install-use-family.sh` and Claude Code plugins.
use-family is a bundle plugin: it fails to load while any plugin it depends on is missing
(Claude Code has no optional dependencies). Marketplace auto-update installs dependencies a new
version adds; a manual `claude plugin update` does not, so the script installs any that are
missing.

## 6. Plugin installs: the CLI follows the plugin

Claude Code auto-updates plugins (turn it on per marketplace: `/plugin` → Marketplaces →
leeguooooo-plugins → Enable auto-update; it is off by default for third-party marketplaces).
That only moves SKILL.md, so at session start the CLI is brought to the plugin's version:

- **use-family** (`plugins/use-family/scripts/sync-clis.sh`): for every installed
  `<name>@leeguooooo-plugins` whose CLI reports an older version than the plugin, runs
  `<name> upgrade`. A CLI without `upgrade` is only named with its installer, never run: some
  installers do more than swap a binary. Log: `~/.cache/use-family/auto-upgrade.log`; a version
  that did not install is retried at most hourly.
- **A use may carry its own hook** when it must work without use-family; it then installs
  exactly the plugin's version. bitwarden-use does this (`hooks/sync-cli.sh`, declared inline in
  its marketplace entry, since a `strict: false` entry with `skills` cannot load a hooks file),
  and use-family skips it.
- Output: one line on stdout per CLI upgraded or failed (the agent sees it); nothing when all
  are current.
- Off: `USE_NO_AUTO_UPGRADE` or `CI`; per use `<NAME>_NO_AUTO_UPGRADE`
  (e.g. `MAIL_USE_NO_AUTO_UPGRADE`, `BITWARDEN_USE_NO_AUTO_UPGRADE`).
