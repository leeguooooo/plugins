# Upgrade use itself and update the installed use family

Install the self-contained Python 3.9+ manager from a checksum-verified GitHub Release:

```sh
curl -fsSL https://raw.githubusercontent.com/leeguooooo/plugins/main/install-use.sh | sh
use upgrade              # upgrade only the use manager
use upgrade --check      # check only the manager release
use update               # update installed family tools
use update --check
use install image-use     # install a missing member CLI (ask the user first)
use report                # last result; does not run another upgrade
use report --verbose      # all channels, failures and preserved paths
use status --json
```

`use update` updates only installed family CLIs, clean Git skill checkouts and installed
Claude/Codex family plugins. `use upgrade` separately upgrades the manager itself. It does not bulk-install
missing family members. Each CLI keeps ownership of its installer, app and skill refresh.
`use update motion-use chrome-use` selects a subset. Unknown names are refused.
`use upgrade` does not accept family names and never inventories or updates their CLIs,
skills or plugins. Self-update results are kept in `last-manager-report.json` (`use report --manager`); `use report`
continues to show the last family update.

New scheduled jobs run `use update --automatic`. Jobs installed before this split still
use `use upgrade --automatic`; that internal form retains its family-update meaning,
including the existing consent, interval and opt-out checks. Refreshing an already enabled
macOS schedule rewrites its file without restarting the loaded job. Scheduling stays opt-in.

`use install image-use` installs a missing member's CLI on request: it runs that member's own
`install.sh` (the line doctor.sh prints) and reads the CLI back from PATH; an installed CLI is left
alone. When a member's plugin is installed but its CLI is missing, the use-family session-start check
names this command; the agent still asks the user before running it, since an installer writes to
their machine. POSIX only; on Windows run the member's `install.ps1`. While another process holds
the install or upgrade lock, `use` exits 75 and the session-start hooks stay silent.

The default terminal output shows one live progress line, then a summary grouped by tool.
Current versions stay out of the summary; a skill checkout whose pull moved `HEAD` is listed
with its old and new commit. Problems are grouped per tool, one line per channel, each followed
by a `→` command that reproduces or inspects it (`<tool> upgrade`, `<tool> --help`,
`git -C <path> status`); owner output itself is never echoed. Skill copies that differ from
every known release are grouped separately from failed upgrades.
In a terminal the summary is coloured: green `✓` for updates, red `✗` for failures, yellow `!` for
items that need attention, with tool names in one aligned column. Piped output, `NO_COLOR` and
`TERM=dumb` print plain text; `FORCE_COLOR` turns colour on without a terminal. `--verbose` shows every
channel and path; `--json` retains the structured report without terminal progress output.
Git history divergence is reported with its cause; the manager never resets local commits.

### How `use` gets installed

- **Claude Code:** every `*-use` marketplace entry (and `use-family`) depends on the
  `use-manager` plugin, so installing any one of them installs it too. Its `startup`
  SessionStart hook runs `use.py install --local` from the plugin's own copy: no network,
  idempotent, never a downgrade (a newer installed manager is kept), never enables scheduling,
  and it never fails session start. `USE_NO_MANAGER=1` skips it. Users who installed a plugin
  before the dependency existed get it with the next marketplace auto-update, or with
  `claude plugin update <plugin>@leeguooooo-plugins` and `/reload-plugins`.
- **Codex / plain `install.sh`:** `install-use.sh` above. Product installers call it too.
- `plugins/use-manager/scripts/use.py` is canonical. `plugins/use-family/scripts/use.py` is a
  byte-identical copy kept for older raw URLs; tests and the release workflow refuse a drift.

### Copied skills

A copied skill (for example `~/.claude/skills/message-use`) counts as current when every file
in it is byte-identical to the same path in the installed owner plugin, even when that plugin
is a whole repository. A copy carrying an owner installer's `.<name>-release` marker whose
`skill_sha256` still matches its `SKILL.md` is installer-owned and left to that installer.
Anything else differing is preserved and reported.

### English and Chinese

```sh
use --lang en update
use update --lang zh
use --lang en report --verbose
USE_LANG=zh use report
```

`--lang en|zh|auto` works before or after the command. It overrides `USE_LANG`, then
the terminal locale is used. Chinese locales select Chinese; other locales fall back
to English. C/POSIX locales select English in auto mode. Help, progress, summaries and
manager-owned errors use the same language. JSON keys, status codes and stored reasons
remain stable English data, independent of the display language. Third-party tool logs
retain their original language.

### Version checks and rate limits

The manager installs a CLI only after a newer target version is confirmed. Current CLIs
are not reinstalled; Git skills and plugins are still refreshed through their own channels.
If a version check fails, the existing CLI is retained and the installer is not run.

Existing `GH_TOKEN` / `GITHUB_TOKEN` values are honored. Otherwise the manager can reuse
the current `gh` login for github.com: its token stays in memory and is passed only to
upgrade subprocesses, never written to configuration or reports. Known token values are
redacted from captured output and logs. No login is created or changed.

A confirmed GitHub API limit defers the remaining CLI checks instead of repeating owner
requests. Anonymous limits are cached until their reported reset time; authenticated checks
do not reuse that anonymous cache. HTTP 403 alone is reported as access denied, not proof of
a rate limit. Deferred checks and retained skill copies are shown separately from failures.

On Windows, install Python 3.9+ first, then run in PowerShell:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/leeguooooo/plugins/main/install-use.ps1)))
use update
```

The installer creates `~/.local/bin/use` (`use.cmd` with CRLF on Windows). Add that directory
to PATH if it is not already there. Installing the manager does not enable a scheduler.
The trusted use-family plugin and Git skill installer can install this small manager locally;
unknown executables are preserved, and an older plugin bootstrap never downgrades it.

## Daily automatic upgrades

```sh
use auto enable           # consent to daily upgrades on this machine
use auto status --json    # enabled state, registration, busy state and last report
use auto disable
```

`--hours 24` is the default; `use auto enable --hours 48` changes it. A per-user launchd agent
(macOS), systemd user timer (Linux), or Task Scheduler task (Windows) wakes hourly, and the
manager attempts upgrades at most once per configured interval. No agent session needs to
be open. macOS runs once when first registered; Linux/Windows use their next trigger. A
registered timer does not prove that upgrades succeeded: inspect the last report.

Automatic upgrades are opt-in. `CI`, `USE_NO_AUTOUPDATE`, `USE_NO_AUTO_UPGRADE` and per-member variables such as
`MAIL_USE_NO_AUTO_UPGRADE` suppress automatic actions when present in the worker's environment.
Use `use auto disable` for a durable off switch. Disabling stops future upgrades; it does not
kill a tool already being updated. No other agent session, shared daemon or remote host is
stopped or upgraded by the manager. Interactive authentication/trust requirements remain
attention items; the worker never accepts a newly displayed marketplace command with `-y`.

## What is checked

- **CLIs:** the owner's `upgrade --check`, then `upgrade`, then a version readback. A zero exit
  code that leaves a known required version uninstalled is a failure. Unknown target versions
  remain unverified; newer development versions are retained.
- **Skills:** only clean Git checkouts are pulled with `--ff-only`. Dirty or modified copies
  are preserved and reported for attention. An unmodified copy that matches a known installed
  plugin snapshot can be refreshed with a retained backup; its baseline is then tracked by the
  manager. Copies without a verifiable owner baseline remain manual. Installer-owned skills
  stay with their CLI.
- **Claude:** only installed family plugin IDs and scopes are updated. Marketplace refreshes
  are limited to the markets those plugins use. Plugin failures propagate; missing bundle
  dependencies are not installed behind the user's back.
- **Codex:** uses its native `plugin list --json` and targeted `plugin marketplace upgrade`.
  Installed versions, installed set and enabled state are read back. If a marketplace refresh
  would include a plugin outside the requested family/subset, it is preserved and reported
  for attention. Local/admin-owned markets remain owned by their host. See the
  [official marketplace refresh documentation](https://developers.openai.com/plugins/build/plugins).
- **Thermo:** uses the public thermo-use installer, which installs the signed App if missing
  and links its CLI. An existing App updates through Thermo's own update mechanism. The
  manager reads the official appcast and installed App version; a submitted update request
  or relink alone is not reported as a completed App upgrade. It never installs/restarts the
  privileged fan helper. Pending UI/app updates remain visible.

One ordinary failure does not stop the remaining members. A process lock prevents two
manager runs from upgrading concurrently; the OS releases it after a crash, without PID
killing or stale-lock deletion. Each child command is bounded, and automatic attempts are
throttled even after failure. Use a manual `use update` after resolving an attention item.

`--check` checks CLI update availability and inventories the other installed channels; it
never runs their upgrade operations. It does not claim to have fetched fresh plugin/skill
catalogues. `--json` provides per-channel results. Exit 0 means all attempted items were
verified/current/completed; exit 2 means failed, manual, pending or unverified items remain.
New plugin code takes effect in a new host session; the manager does not restart your chat.

State: `~/.local/state/use-family/` (`config.json`, `last-attempt.json`, `last-report.json`,
private `upgrade.log`). `USE_MANAGER_STATE`, `USE_MANAGER_HOME`, `USE_MANAGER_BIN` and the
existing `USE_FAMILY_DIR` support isolated installations/tests. Log output may contain the
owner tools' diagnostics and stays private instead of being copied into status JSON.

The older `upgrade-use-family.sh` command delegates to this manager. The existing CLI/plugin
upgrade convention remains in [upgrade.md](upgrade.md).
