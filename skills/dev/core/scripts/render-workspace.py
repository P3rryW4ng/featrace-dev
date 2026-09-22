#!/usr/bin/env python3
"""Render human-readable Markdown views from canonical JSON workflow records."""
import json
import pathlib
import sys
from prd_intake import render_intake
from revisions import inspect
from feature_lifecycle import metadata
from fixes import render_fixes
from clarifications import render_decisions
from impact import render_impact
from verification import render as render_verification
from regression_review import render as render_regression_review
from task_review import render as render_task_review


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
    modules, archive = metadata(feature)
    spec += ["Archived: " + str(archive["archived"]), "Modules: " + (", ".join(modules) or "unclassified"), ""]
    scope = feature.get('module_scope')
    if isinstance(scope, dict):
        capability = scope.get('capability') if isinstance(scope.get('capability'), dict) else {}
        spec += ["Module scope: " + str(scope.get('status', 'invalid')),
                 "Capability: " + (str(capability.get('name', '')) + " (" + str(capability.get('id', 'none')) + ")" if capability else "none")]
        for row in scope.get('assignments', []) if isinstance(scope.get('assignments'), list) else []:
            if isinstance(row, dict):
                spec.append("- Module role: %s = %s — %s" % (row.get('module_id', '?'), row.get('role', '?'), row.get('responsibility', '')))
        if scope.get('note'):
            spec.append("Scope note: " + str(scope['note']))
        spec.append("")
    for item in req_doc.get("requirements", []):
        spec += [f"## {item.get('id', '?')} — {item.get('title', '')}", "", f"- Status: {item.get('status', '')}", f"- Statement: {item.get('statement', '')}", f"- Sources: {', '.join(s.get('ref', '') for s in item.get('sources', []))}", f"- Acceptance: {'; '.join(item.get('acceptance_criteria', []))}", f"- Tasks: {', '.join(item.get('tasks', []))}", f"- Tests: {', '.join(item.get('tests', []))}", ""]
    baseline, revisions, pending = inspect(feature_dir, req_doc)
    if baseline:
        accepted = max((x['version'] for x in baseline['deliveries']), default=0)
        spec += ["Confirmed baseline: v" + str(baseline['version']), "Verified baseline: " + str(accepted), ""]
        lines = ['# Requirement revisions', '', 'Confirmed: v' + str(baseline['version']), 'Verified: ' + str(accepted), '']
        applied = {e['id']: e for e in baseline['applied']}
        cancelled = {e['id'] for e in baseline['cancelled']}
        for rid, revision in revisions.items():
            state = 'applied v' + str(applied[rid]['version']) if rid in applied else ('cancelled' if rid in cancelled else 'pending')
            lines += ['## ' + rid + ' — ' + state, '', revision['reason'], '', 'Impact: ' + revision['impact_review'], '', '```json', json.dumps(revision['changes'], ensure_ascii=False, indent=2), '```', '']
        (feature_dir / 'revisions.md').write_text('\n'.join(lines))
    (feature_dir / "spec" / "spec.md").write_text("\n".join(spec))
    (feature_dir / "tasks.md").write_text("# Tasks\n\n" + "\n".join(f"- {t.get('id', '?')} [{t.get('status', '')}] {t.get('title', '')}" for t in tasks) + "\n")
    render_decisions(feature_dir, decisions)
    (feature_dir / "traceability.md").write_text("# Traceability\n\n" + "\n".join(f"- {x.get('requirement_id', '?')} → {x.get('task_id', '?')} → {', '.join(x.get('tests', []))}" for x in links) + "\n")
    render_intake(feature_dir)
    render_fixes(feature_dir, sys.argv[2])
    render_impact(feature_dir)
    render_verification(feature_dir)
    render_regression_review(feature_dir)
    render_task_review(feature_dir)
    print("WORKSPACE_RENDERED")


if __name__ == "__main__":
    main()
