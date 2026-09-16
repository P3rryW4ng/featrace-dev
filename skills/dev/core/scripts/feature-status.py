#!/usr/bin/env python3
"""Print a compact, deterministic feature status summary."""
import json
import pathlib
import sys


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
print("COMPLETION: not evaluated; review decisions, source applicability, tasks and current quality evidence")
