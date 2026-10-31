#!/bin/sh
# Every marketplace entry declares a license.
#   sh tests/marketplace.test.sh
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
python3 - "$ROOT/.claude-plugin/marketplace.json" <<'PY'
import json, sys
plugins = json.load(open(sys.argv[1], encoding="utf-8"))["plugins"]
missing = [p["name"] for p in plugins if not str(p.get("license", "")).strip()]
if missing:
    sys.exit("FAIL: no license in marketplace.json: " + ", ".join(missing))
PY
echo "ok marketplace"
