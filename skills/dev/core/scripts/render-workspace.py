#!/usr/bin/env python3
"""Render human-readable Markdown views from canonical JSON workflow records."""
import json
import pathlib
import sys
from prd_intake import render_intake
from fixes import render_fixes


def load(path):
    return json.loads(path.read_text())


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: render-workspace.py <PROJECT-ROOT> <FEATURE-ID>")
    feature_dir = pathlib.Path(sys.argv[1]).resolve() / ".agent-workflow" / "features" / sys.argv[2]
    req_doc = load(feature_dir / "spec" / "requirements.json")
    tasks = load(feature_dir / "tasks.json").get("tasks", [])
    decisions = load(feature_dir / "decisions.json").get("decisions", [])
    links = load(feature_dir / "traceability.json").get("links", [])
    feature = req_doc["feature"]
    spec = [f"# {feature['id']} — {feature.get('title') or 'Untitled feature'}", "", f"Status: {feature.get('status', 'drafted')}", ""]
    for item in req_doc.get("requirements", []):
        spec += [f"## {item.get('id', '?')} — {item.get('title', '')}", "", f"- Status: {item.get('status', '')}", f"- Statement: {item.get('statement', '')}", f"- Sources: {', '.join(s.get('ref', '') for s in item.get('sources', []))}", f"- Acceptance: {'; '.join(item.get('acceptance_criteria', []))}", f"- Tasks: {', '.join(item.get('tasks', []))}", f"- Tests: {', '.join(item.get('tests', []))}", ""]
    (feature_dir / "spec" / "spec.md").write_text("\n".join(spec))
    (feature_dir / "tasks.md").write_text("# Tasks\n\n" + "\n".join(f"- {t.get('id', '?')} [{t.get('status', '')}] {t.get('title', '')}" for t in tasks) + "\n")
    (feature_dir / "decisions.md").write_text("# Decisions\n\n" + "\n".join(f"## {d.get('id', '?')}\n\n- Status: {d.get('status', '')}\n- Chosen: {d.get('chosen', 'pending')}\n" for d in decisions))
    (feature_dir / "traceability.md").write_text("# Traceability\n\n" + "\n".join(f"- {x.get('requirement_id', '?')} → {x.get('task_id', '?')} → {', '.join(x.get('tests', []))}" for x in links) + "\n")
    render_intake(feature_dir)
    render_fixes(feature_dir, sys.argv[2])
    print("WORKSPACE_RENDERED")


if __name__ == "__main__":
    main()
