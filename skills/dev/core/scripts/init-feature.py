#!/usr/bin/env python3
"""Initialize a feature; no PRD parsing is claimed."""
import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
from prd_intake import new_intake

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('feature')
parser.add_argument('primary', type=pathlib.Path, help='first document or HTML source')
parser.add_argument('root', nargs='?', type=pathlib.Path, default=pathlib.Path('.'))
parser.add_argument('--source', action='append', type=pathlib.Path, default=[], help='additional document or HTML source; repeatable')
args = parser.parse_args()
feature, root = args.feature, args.root.resolve()
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", feature):
    raise SystemExit("Invalid feature ID")
sources = [args.primary.resolve()] + [p.resolve() for p in args.source]
if not root.is_dir() or not all(p.is_file() and not p.is_symlink() for p in sources):
    raise SystemExit("Project directory and each source file must exist and be regular files")
if len(set(sources)) != len(sources):
    raise SystemExit("Duplicate source file")
folder = root / ".agent-workflow" / "features" / feature
folder.mkdir(parents=True, exist_ok=False)
(folder / "sources").mkdir()
(folder / "spec").mkdir()
registered = []
for number, source in enumerate(sources, 1):
    if source.suffix.lower() in {'.html', '.htm'}:
        kind = 'html'
    else:
        kind = 'document'
    source_name = ('prd-original' if number == 1 else 'prd-part-%02d' % number) + source.suffix
    shutil.copy2(source, folder / 'sources' / source_name)
    registered.append({'id': 'SRC-%02d' % number, 'path': 'sources/' + source_name, 'kind': kind})
paths = [row['path'] for row in registered]
doc = {"feature": {"id": feature, "title": "", "status": "drafted", "workflow_version": 2,
                   "impact_required": True,
                   "history_regression_required": True,
                   "source_status": {"prd": "present", "api": "unknown", "figma": "unknown"},
                   "source_notes": {}, "prd_path": paths[0], "prd_paths": paths}, "requirements": []}
(folder / "spec/requirements.json").write_text(json.dumps(doc, indent=2) + "\n")
for name, key in (("tasks", "tasks"), ("decisions", "decisions"), ("traceability", "links"), ("fixes", "fixes")):
    (folder / (name + ".json")).write_text(json.dumps({"feature_id": feature, key: []}, indent=2) + "\n")
intake = new_intake(feature)
intake["sources"] = registered
(folder / "spec/prd-intake.json").write_text(json.dumps(intake, indent=2) + "\n")
subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("render-workspace.py")), str(root), feature], check=True)
print("FEATURE_CREATED: " + str(folder))
