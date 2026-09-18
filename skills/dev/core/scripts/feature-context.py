#!/usr/bin/env python3
"""Read-only feature selection. The Agent owns project-scoped session context."""
import argparse
import json
import pathlib
import re


def describe(root, feature_id):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", feature_id):
        raise ValueError("Invalid feature ID")
    folder = root / ".agent-workflow" / "features" / feature_id
    path = folder / "spec" / "requirements.json"
    if not path.resolve().is_relative_to(root):
        raise ValueError("Feature record escapes project")
    doc = json.loads(path.read_text(encoding="utf-8"))
    feature = doc.get("feature") if isinstance(doc, dict) else None
    if not isinstance(feature, dict) or feature.get("id") != feature_id:
        raise ValueError("Feature record ID mismatch")
    if not all(isinstance(feature.get(k), str) for k in ("title", "status")):
        raise ValueError("Feature title/status must be strings")
    return {"project": str(root), "id": feature_id,
            "title": feature["title"], "status": feature["status"]}


def inventory(root):
    base = root / ".agent-workflow" / "features"
    if not base.resolve().is_relative_to(root):
        raise ValueError("Feature directory escapes project")
    rows = []
    if base.exists():
        for folder in sorted(base.iterdir()):
            if folder.is_dir():
                try:
                    rows.append(describe(root, folder.name))
                except (OSError, ValueError) as exc:
                    rows.append({"id": folder.name, "error": str(exc)})
    return rows


def resolve(root, explicit=None, current=None, current_root=None):
    if explicit is not None:
        return describe(root, explicit)
    if not current or not current_root or pathlib.Path(current_root).resolve() != root:
        raise ValueError("No selected feature for this project; run list then use <ID>")
    return describe(root, current)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("list", "use", "resolve"))
    parser.add_argument("project", type=pathlib.Path)
    parser.add_argument("--feature")
    parser.add_argument("--current")
    parser.add_argument("--current-project")
    args = parser.parse_args()
    root = args.project.resolve()
    try:
        if not root.is_dir():
            raise ValueError("Project directory does not exist")
        if args.action == "list":
            result = {"project": str(root), "features": inventory(root)}
        elif args.action == "use":
            if not args.feature:
                raise ValueError("use requires --feature")
            result = describe(root, args.feature)
        else:
            result = resolve(root, args.feature, args.current, args.current_project)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(1, "FEATURE_CONTEXT_ERROR: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
