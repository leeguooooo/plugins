#!/bin/sh
# Every marketplace entry declares a license, and a remote entry pinned to a tag
# is pinned to the tag of its own version.
#   sh tests/marketplace.test.sh
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
python3 - "$ROOT/.claude-plugin/marketplace.json" <<'PY'
import json, sys
plugins = json.load(open(sys.argv[1], encoding="utf-8"))["plugins"]
missing = [p["name"] for p in plugins if not str(p.get("license", "")).strip()]
if missing:
    sys.exit("FAIL: no license in marketplace.json: " + ", ".join(missing))
for p in plugins:
    src = p.get("source")
    if not isinstance(src, dict):
        continue
    ref = src.get("ref", "main")
    if ref != "main" and ref != "v" + p["version"]:
        sys.exit(f"FAIL: {p['name']}: ref {ref} does not match version {p['version']}")
PY
echo "ok marketplace"
