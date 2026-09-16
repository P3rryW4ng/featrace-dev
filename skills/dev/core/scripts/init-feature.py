#!/usr/bin/env python3
"""Initialize a feature; no PRD parsing is claimed."""
import json
import pathlib
import re
import shutil
import subprocess
import sys

if len(sys.argv) not in (3, 4):
    raise SystemExit("Usage: init-feature.py <ID> <PRD-FILE> [PROJECT]")
feature, source = sys.argv[1], pathlib.Path(sys.argv[2]).resolve()
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", feature):
    raise SystemExit("Invalid feature ID")
root = pathlib.Path(sys.argv[3] if len(sys.argv) == 4 else ".").resolve()
if not root.is_dir() or not source.is_file():
    raise SystemExit("Project directory and PRD file must exist")
folder = root / ".agent-workflow" / "features" / feature
folder.mkdir(parents=True, exist_ok=False)
(folder / "sources").mkdir()
(folder / "spec").mkdir()
source_name = "prd-original" + source.suffix
shutil.copy2(source, folder / "sources" / source_name)
doc = {"feature": {"id": feature, "title": "", "status": "drafted", "source_status": {"prd": "present", "api": "unknown", "figma": "unknown"}, "source_notes": {}, "prd_path": "sources/" + source_name}, "requirements": []}
(folder / "spec/requirements.json").write_text(json.dumps(doc, indent=2) + "\n")
for name, key in (("tasks", "tasks"), ("decisions", "decisions"), ("traceability", "links")):
    (folder / (name + ".json")).write_text(json.dumps({"feature_id": feature, key: []}, indent=2) + "\n")
subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("render-workspace.py")), str(root), feature], check=True)
print("FEATURE_CREATED: " + str(folder))
