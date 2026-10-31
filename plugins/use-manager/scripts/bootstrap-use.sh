#!/bin/sh
# Install the `use` manager bundled with this plugin: offline, idempotent, never a downgrade,
# never scheduling. Session startup must not fail because of it.
ROOT=${USE_PLUGIN_ROOT:+$USE_PLUGIN_ROOT/scripts}
ROOT=${ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)}
[ -n "${USE_NO_MANAGER:-}" ] && exit 0
command -v python3 >/dev/null 2>&1 || exit 0
# Exit 75: another session is installing the same copy right now; nothing to do or report.
rc=0; python3 "$ROOT/use.py" install --local >/dev/null 2>&1 || rc=$?
[ "$rc" = 0 ] || [ "$rc" = 75 ] || echo "use-manager: could not install the use command; run: python3 \"$ROOT/use.py\" install --local" >&2
exit 0
