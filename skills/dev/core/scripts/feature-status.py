#!/usr/bin/env python3
"""Print a compact, deterministic feature status summary."""
import json
import pathlib
import sys
from fixes import read_fixes, TERMINAL_STATUSES


def load(path):
    return json.loads(path.read_text())


if len(sys.argv) != 3:
    raise SystemExit("Usage: feature-status.py <PROJECT-ROOT> <FEATURE-ID>")
root, feature_id = pathlib.Path(sys.argv[1]).resolve(), sys.argv[2]
folder = root / ".agent-workflow" / "features" / feature_id
req = load(folder / "spec" / "requirements.json")
tasks = load(folder / "tasks.json").get("tasks", [])
requirements = req.get("requirements", [])
counts = {state: sum(item.get("status") == state for item in requirements) for state in ("inferred", "confirmed", "blocked", "deprecated")}
done = sum(task.get("status") == "done" for task in tasks)
print(f"FEATURE: {feature_id}")
print("SOURCES: " + ", ".join(f"{key}={value}" for key, value in req["feature"].get("source_status", {}).items()))
print("REQUIREMENTS: " + ", ".join(f"{key}={value}" for key, value in counts.items()))
print(f"TASKS: done={done}/{len(tasks)}")
print("REQUIREMENT_BLOCKERS: present" if counts["blocked"] else "REQUIREMENT_BLOCKERS: none")
fixes = read_fixes(folder, feature_id).get('fixes', [])
open_fixes = sum(fix.get('status') not in TERMINAL_STATUSES for fix in fixes if isinstance(fix, dict))
print(f"FIXES: unresolved={open_fixes}/{len(fixes)}")
verified = sum(fix.get('status') == 'verified' for fix in fixes if isinstance(fix, dict))
closed = sum(fix.get('status') == 'closed' for fix in fixes if isinstance(fix, dict))
print(f"FIX_OUTCOMES: recorded_verified={verified}, recorded_closed={closed}; run validation to check evidence")
print("COMPLETION: not evaluated; review decisions, source applicability, tasks and current quality evidence")
