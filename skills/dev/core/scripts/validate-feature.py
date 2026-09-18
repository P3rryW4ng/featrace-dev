#!/usr/bin/env python3
"""Validate the deterministic records for one feature workspace."""
import argparse
import json
import pathlib
import sys
import re
from prd_intake import validate_intake
from fixes import validate_fixes
from clarifications import validate_clarifications

REQUIREMENT_STATES = {"inferred", "confirmed", "blocked", "deprecated"}
TASK_STATES = {"planned", "in_progress", "blocked", "done"}


def read_json(path, errors):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        errors.append(f"missing required record: {path.name}")
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {path.name}: {exc.msg}")
    return {}


def required_string(value, label, errors):
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("draft", "develop", "check"), default="draft")
    parser.add_argument("root")
    parser.add_argument("feature_id")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.feature_id):
        return report(["invalid feature ID"], [])
    feature_dir = pathlib.Path(args.root).resolve() / ".agent-workflow" / "features" / args.feature_id
    errors, warnings = [], []
    req_doc = read_json(feature_dir / "spec" / "requirements.json", errors)
    task_doc = read_json(feature_dir / "tasks.json", errors)
    decision_doc = read_json(feature_dir / "decisions.json", errors)
    trace_doc = read_json(feature_dir / "traceability.json", errors)
    if errors:
        return report(errors, warnings)

    if not all(isinstance(d, dict) for d in (req_doc, task_doc, decision_doc, trace_doc)):
        return report(["records must be JSON objects"], [])
    feature = req_doc.get("feature", {})
    if not isinstance(feature, dict):
        return report(["feature must be an object"], [])
    if feature.get("id") != args.feature_id:
        errors.append("feature.id must match the feature directory")
    if not isinstance(feature.get("source_status"), dict):
        errors.append("feature.source_status must be an object")
    requirements = req_doc.get("requirements")
    tasks = task_doc.get("tasks")
    decisions = decision_doc.get("decisions")
    links = trace_doc.get("links")
    if not isinstance(requirements, list): errors.append("requirements must be an array")
    if not isinstance(tasks, list): errors.append("tasks must be an array")
    if not isinstance(decisions, list): errors.append("decisions must be an array")
    if not isinstance(links, list): errors.append("links must be an array")
    if errors:
        return report(errors, warnings)
    if args.stage in {"develop", "check"}:
        if feature.get("status") == "migration_required":
            errors.append("migration must be completed before development")
        if not any(isinstance(r, dict) and r.get("status") != "deprecated" for r in requirements):
            errors.append("at least one active requirement is required")
    for doc in (task_doc, decision_doc, trace_doc):
        if doc.get("feature_id") != args.feature_id:
            errors.append("record feature_id does not match feature directory")
    if not isinstance(feature.get("source_notes", {}), dict):
        return report(["feature.source_notes must be an object"], warnings)
    for kind, state in feature.get("source_status", {}).items():
        if state not in {"present", "missing", "unknown", "not_applicable"}:
            errors.append("invalid source state: " + kind)
        if state == "not_applicable" and not feature.get("source_notes", {}).get(kind):
            errors.append("not_applicable needs a reason: " + kind)
    if not requirements:
        warnings.append("no requirements have been decomposed from the PRD yet")

    requirement_ids, task_ids = set(), set()
    blocked = False
    for index, item in enumerate(requirements):
        label = f"requirement[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object"); continue
        rid = item.get("id")
        required_string(rid, f"{label}.id", errors)
        if not isinstance(rid, str):
            continue
        if rid in requirement_ids: errors.append(f"duplicate requirement id: {rid}")
        requirement_ids.add(rid)
        required_string(item.get("title"), f"{label}.title", errors)
        required_string(item.get("statement"), f"{label}.statement", errors)
        if item.get("status") not in REQUIREMENT_STATES:
            errors.append(f"{label}.status is invalid")
        if item.get("status") == "blocked": blocked = True
        sources = item.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append(f"{label}.sources must contain at least one source")
        else:
            for source in sources:
                if not isinstance(source, dict) or not source.get("type") or not source.get("ref"):
                    errors.append(f"{label}.sources entries require type and ref")
        for field in ("acceptance_criteria", "tasks", "tests", "assumptions"):
            if not isinstance(item.get(field, []), list): errors.append(f"{label}.{field} must be an array")
        if args.stage in {"develop", "check"} and item.get("status") != "deprecated":
            if not item.get("acceptance_criteria"): errors.append(f"{rid} needs acceptance criteria before development")
            if not item.get("tasks"): errors.append(f"{rid} needs at least one task before development")
            if not item.get("tests"): errors.append(f"{rid} needs at least one test before development")

    if errors:
        return report(errors, warnings)

    for index, task in enumerate(tasks):
        label = f"task[{index}]"
        if not isinstance(task, dict): errors.append(f"{label} must be an object"); continue
        tid = task.get("id")
        required_string(tid, f"{label}.id", errors)
        if not isinstance(tid, str):
            continue
        if tid in task_ids: errors.append(f"duplicate task id: {tid}")
        task_ids.add(tid)
        if task.get("status") not in TASK_STATES: errors.append(f"{label}.status is invalid")
        refs = task.get("requirement_ids")
        if not isinstance(refs, list) or not refs: errors.append(f"{label}.requirement_ids must not be empty")
        elif any(ref not in requirement_ids for ref in refs): errors.append(f"{label} references an unknown requirement")
        if args.stage == "check" and task.get("status") == "done" and not task.get("test_evidence") and not task.get("test_waiver"):
            errors.append(f"{tid} is done but has no test evidence or waiver")

    if errors:
        return report(errors, warnings)

    for item in requirements:
        if not isinstance(item, dict):
            continue
        rid = item.get("id")
        declared_tasks = item.get("tasks", [])
        if args.stage in {"develop", "check"} and any(task_id not in task_ids for task_id in declared_tasks):
            errors.append(f"{rid} declares a task that is missing from tasks.json")
        if args.stage in {"develop", "check"} and rid and not any(rid in task.get("requirement_ids", []) for task in tasks if isinstance(task, dict)):
            errors.append(f"{rid} is not linked from any task")

    for decision in decisions:
        if not isinstance(decision, dict): errors.append("decision entry must be an object"); continue
        required_string(decision.get("id"), "decision.id", errors)
        if args.stage in {"develop", "check"} and decision.get("status") in {"pending", "blocked"}:
            errors.append("unresolved decision: " + str(decision.get("id")))
        if decision.get("status") == "approved" and not decision.get("chosen"):
            errors.append(f"{decision.get('id')} is approved but has no chosen option")
    clarification_errors, clarification_warnings = validate_clarifications(decisions, args.stage)
    errors.extend(clarification_errors)
    warnings.extend(clarification_warnings)
    for link in links:
        if not isinstance(link, dict) or not link.get("requirement_id"):
            errors.append("each traceability link needs requirement_id")
        elif link["requirement_id"] not in requirement_ids:
            errors.append("traceability link references an unknown requirement")
    if args.stage in {"develop", "check"} and blocked:
        errors.append("blocked requirements must be resolved before development")
    if args.stage == "check":
        live = [r for r in requirements if r.get("status") != "deprecated"]
        traced = {link.get("requirement_id") for link in links if isinstance(link, dict)}
        missing = [r.get("id") for r in live if r.get("id") not in traced]
        if missing: errors.append("missing traceability for: " + ", ".join(missing))
    if not errors:
        intake_errors, intake_warnings = validate_intake(feature_dir, req_doc, args.stage)
        errors.extend(intake_errors)
        warnings.extend(intake_warnings)
    fix_errors, fix_warnings = validate_fixes(feature_dir, args.feature_id, requirements, tasks, decisions, args.stage)
    errors.extend(fix_errors)
    warnings.extend(fix_warnings)
    return report(errors, warnings)


def report(errors, warnings):
    for warning in warnings: print("WARNING: " + warning)
    for error in errors: print("ERROR: " + error)
    if errors: return 1
    print("FEATURE_VALID")
    return 0


if __name__ == "__main__":
    sys.exit(main())
