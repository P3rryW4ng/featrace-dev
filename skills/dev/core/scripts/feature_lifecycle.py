"""Small archive metadata contract; product status and source records stay independent."""
import json
import pathlib
import re


ARCHIVE_DRAFT_MARKER = "<!-- ARCHIVE_REPORT_DRAFT_REVIEW_REQUIRED -->"


def metadata(feature):
    modules = feature.get("modules", [])
    if (not isinstance(modules, list) or any(not isinstance(x, str) or not x.strip() or x != x.strip() for x in modules)
            or len(set(modules)) != len(modules)):
        raise ValueError("feature.modules must contain unique non-empty module labels")
    archive = feature.get("archive", {"archived": False, "history": []})
    if (not isinstance(archive, dict) or type(archive.get("archived")) is not bool
            or not isinstance(archive.get("history"), list)):
        raise ValueError("invalid feature.archive metadata")
    state = False
    for event in archive["history"]:
        if not isinstance(event, dict) or event.get("action") not in {"archive", "restore"}:
            raise ValueError("invalid archive history event")
        fields = ["at", "reason"]
        if event["action"] == "archive":
            fields += ["revision", "evidence", "evidence_sha256"]
        if any(not isinstance(event.get(k), str) or not event[k].strip() for k in fields):
            raise ValueError("incomplete archive history event")
        new_state = event["action"] == "archive"
        if new_state == state:
            raise ValueError("archive history must alternate archive and restore")
        state = new_state
    if state != archive["archived"]:
        raise ValueError("archive state does not match history")
    return modules, archive


def require_active(feature):
    if metadata(feature)[1]["archived"]:
        raise ValueError("Feature is archived; restore it before changing records or running develop/check")


def read_record(root, feature_id):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", feature_id):
        raise ValueError("Invalid feature ID")
    path = root / ".agent-workflow/features" / feature_id / "spec/requirements.json"
    if path.resolve() != path:
        raise ValueError("Refusing symlinked feature record path")
    original = path.read_bytes()
    doc = json.loads(original)
    if not isinstance(doc, dict) or not isinstance(doc.get("feature"), dict) or doc["feature"].get("id") != feature_id:
        raise ValueError("Feature ID does not match record")
    metadata(doc["feature"])
    return path, original, doc
