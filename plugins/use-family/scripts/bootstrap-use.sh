#!/bin/sh
# Keep the manager bundled with this trusted plugin available, without opting in to scheduling.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
command -v python3 >/dev/null 2>&1 || exit 0
# Exit 75: another session is installing the same copy right now; nothing to do or report.
rc=0; python3 "$ROOT/use.py" install --local >/dev/null 2>&1 || rc=$?
[ "$rc" = 0 ] || [ "$rc" = 75 ] || echo "use-family: could not install the use command; run: python3 \"$ROOT/use.py\" install --local" >&2
# Existing consent lives in config.json; this hook never enables automatic upgrades.
if python3 - <<'PY'
import json,os,pathlib,sys
p=pathlib.Path(os.environ.get('USE_MANAGER_STATE',str(pathlib.Path.home()/'.local/state/use-family')))/'config.json'
try: sys.exit(0 if json.loads(p.read_text()).get('enabled') else 1)
except (OSError,ValueError): sys.exit(1)
PY
then
  exit 0  # The independent daily scheduler owns upgrades; do not block session startup.
fi
exec sh "$ROOT/sync-clis.sh"
