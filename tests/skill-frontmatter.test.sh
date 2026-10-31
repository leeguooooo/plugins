#!/bin/sh
# Each SKILL.md kept in this repo has frontmatter with a matching name and a usable description.
# Member skills live in their own repos and are linted there.
#   sh tests/skill-frontmatter.test.sh
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
python3 - "$ROOT" <<'PY'
import pathlib, re, sys
root = pathlib.Path(sys.argv[1])
skills = sorted((root / "plugins").glob("*/skills/*/SKILL.md"))
if not skills:
    sys.exit("FAIL: no SKILL.md found")
for path in skills:
    head = re.match(r"---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
    if not head:
        sys.exit(f"FAIL: {path}: no frontmatter")
    fields = dict(re.findall(r"^(\w+): *(.*)$", head.group(1), re.M))
    if fields.get("name") != path.parent.name:
        sys.exit(f"FAIL: {path}: name must be {path.parent.name}")
    if not 20 <= len(fields.get("description", "")) <= 1024:
        sys.exit(f"FAIL: {path}: description must be 20-1024 characters")
PY
echo "ok skill frontmatter"
