#!/usr/bin/env python3
"""Create JSON workflow records without altering legacy YAML/Markdown records."""
import json
import pathlib
import sys
import re


if len(sys.argv) != 3:
    raise SystemExit("Usage: migrate-workspace.py <PROJECT-ROOT> <FEATURE-ID>")
root, feature_id = pathlib.Path(sys.argv[1]).resolve(), sys.argv[2]
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", feature_id):
    raise SystemExit("Invalid feature ID")
folder = root / ".agent-workflow" / "features" / feature_id
target = folder / "spec" / "requirements.json"
if any(p.exists() for p in (target, folder / "tasks.json", folder / "decisions.json", folder / "traceability.json")):
    raise SystemExit("Migration stopped: requirements.json already exists.")
legacy = folder / "spec" / "requirements.yaml"
if not legacy.exists():
    raise SystemExit("Migration stopped: no legacy requirements.yaml found.")
target.write_text(json.dumps({
    "feature": {"id": feature_id, "title": "", "status": "migration_required", "source_status": {"prd": "unknown", "api": "unknown", "figma": "unknown"}},
    "requirements": [],
    "migration_note": "Legacy YAML was preserved unchanged. Recreate atomic requirements from it before development."
}, indent=2) + "\n")
for name, key in (("tasks.json", "tasks"), ("decisions.json", "decisions"), ("traceability.json", "links")):
    (folder / name).write_text(json.dumps({"feature_id": feature_id, key: []}, indent=2) + "\n")
print("MIGRATION_SCAFFOLD_CREATED: legacy records were not modified")
