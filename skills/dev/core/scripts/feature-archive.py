#!/usr/bin/env python3
"""Archive/restore in place or classify by modules; never delete historical evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from feature_lifecycle import read_record, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("archive", "restore", "classify"))
    parser.add_argument("project", type=Path)
    parser.add_argument("feature_id")
    parser.add_argument("--reason", default="")
    parser.add_argument("--revision", default="")
    parser.add_argument("--evidence", default="delivery-report.md", help="feature-relative delivery report")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--module", action="append")
    group.add_argument("--clear-modules", action="store_true")
    args = parser.parse_args()
    root = args.project.resolve()
    path, original, doc = read_record(root, args.feature_id)
    feature = doc["feature"]
    modules, archive = metadata(feature)
    if args.action != "classify" and (args.module is not None or args.clear_modules):
        raise ValueError("Use classify to change modules")
    if args.action == "classify":
        if args.module is None and not args.clear_modules:
            raise ValueError("classify requires --module or --clear-modules")
        feature["modules"] = args.module or []
    else:
        target = args.action == "archive"
        if archive["archived"] == target:
            print("ARCHIVE_UNCHANGED")
            return 0
        if not args.reason.strip():
            raise ValueError("Archive/restore reason is required")
        event = {"action": args.action, "at": datetime.now(timezone.utc).isoformat(), "reason": args.reason.strip()}
        if target:
            if feature.get("status") != "complete":
                raise ValueError("Only complete features can be archived")
            live = [item for item in doc.get("requirements", []) if isinstance(item, dict) and item.get("status") != "deprecated"]
            if not live or any(item.get("status") != "confirmed" for item in live):
                raise ValueError("Active requirements must be confirmed")
            states = feature.get("source_status", {})
            if any(states.get(k) not in {"present", "not_applicable"} for k in ("prd", "api", "figma")):
                raise ValueError("Required source applicability must be resolved")
            folder = path.parent.parent
            tasks = json.loads((folder / "tasks.json").read_text()).get("tasks")
            if not isinstance(tasks, list) or not tasks or any(not isinstance(t, dict) or t.get("status") != "done" for t in tasks):
                raise ValueError("All tasks must be done")
            if not args.revision.strip():
                raise ValueError("Tested delivery revision is required")
            report = folder / args.evidence
            if Path(args.evidence).is_absolute() or not report.resolve().is_relative_to(folder) or report.resolve() != report or not report.is_file():
                raise ValueError("Evidence must be a regular feature-local report")
            contents = report.read_bytes()
            if not contents.strip():
                raise ValueError("Delivery report is empty")
            result = subprocess.run([sys.executable, str(Path(__file__).with_name("validate-feature.py")),
                                     "--stage", "check", str(root), args.feature_id], capture_output=True, text=True)
            if result.returncode:
                raise ValueError("Archive record check failed:\n" + result.stdout + result.stderr)
            event.update(revision=args.revision.strip(), evidence=report.relative_to(folder).as_posix(),
                         evidence_sha256=hashlib.sha256(contents).hexdigest())
        feature["archive"] = {"archived": target, "history": archive["history"] + [event]}
    metadata(feature)
    if doc == json.loads(original):
        print("ARCHIVE_UNCHANGED")
        return 0
    # Replace only canonical metadata, preserving sources, report and all history files.
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            temp = Path(stream.name)
            json.dump(doc, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        if path.read_bytes() != original:
            raise ValueError("Feature changed during operation; retry after reviewing current records")
        os.replace(temp, path)
    finally:
        if temp and temp.exists():
            temp.unlink()
    print("FEATURE_" + args.action.upper() + ": " + args.feature_id)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print("ARCHIVE_ERROR: " + str(exc), file=sys.stderr)
        sys.exit(1)
