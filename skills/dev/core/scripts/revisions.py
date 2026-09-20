"""Opt-in semantic requirement baselines and immutable revision proposals."""
import copy
import hashlib
import json
from pathlib import Path
import re

FIELDS = ("id", "title", "statement", "status", "acceptance_criteria", "assumptions")
KINDS = {"interpretation_correction", "clarification", "requirement_change"}


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def string_list(value):
    return isinstance(value, list) and all(nonempty(x) for x in value) and len(set(value)) == len(value)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def semantics(requirements):
    if not isinstance(requirements, list) or any(not isinstance(x, dict) for x in requirements):
        raise ValueError("requirements must be objects")
    ids = [x.get("id") for x in requirements]
    if not string_list(ids):
        raise ValueError("unique requirement IDs required")
    return [{k: x.get(k, [] if k in {"acceptance_criteria", "assumptions"} else None) for k in FIELDS}
            for x in requirements]


def apply_changes(requirements, changes):
    if not isinstance(changes, list) or not changes:
        raise ValueError("non-empty changes required")
    result = copy.deepcopy(requirements)
    touched = set()
    added = set()
    for c in changes:
        if not isinstance(c, dict) or not nonempty(c.get("requirement_id")) or "before" not in c or "after" not in c:
            raise ValueError("each change needs requirement_id, field, before and after")
        rid, field = c["requirement_id"], c.get("field")
        if not isinstance(field, str) or (rid, field) in touched or rid in added:
            raise ValueError("duplicate/overlapping requirement change")
        item = next((x for x in result if x.get("id") == rid), None)
        if field == "$requirement":
            if item is not None or c["before"] is not None or not isinstance(c["after"], dict) or c["after"].get("id") != rid:
                raise ValueError("whole requirement operation only adds a new ID; retire with status=deprecated")
            result.append(copy.deepcopy(c["after"]))
            added.add(rid)
        else:
            if field not in FIELDS or field == "id" or item is None:
                raise ValueError("change targets an unknown requirement or unsupported semantic field")
            old = item.get(field, [] if field in {"acceptance_criteria", "assumptions"} else None)
            if old != c["before"]:
                raise ValueError("Before value mismatch: " + rid + "." + field)
            if old == c["after"]:
                raise ValueError("No-op change")
            item[field] = copy.deepcopy(c["after"])
        touched.add((rid, field))
    for item in semantics(result):
        if (item['status'] not in {'confirmed', 'deprecated'} or not nonempty(item['title'])
                or not nonempty(item['statement']) or not string_list(item['acceptance_criteria'])
                or not item['acceptance_criteria'] or not string_list(item['assumptions'])):
            raise ValueError("baseline requirements need confirmed/deprecated status and valid semantic fields")
    return result


def validate_proposal(doc, feature_id):
    if not isinstance(doc, dict) or doc.get("feature_id") != feature_id:
        raise ValueError("revision feature mismatch")
    if not re.fullmatch(r"CHG-[0-9]{3,}", str(doc.get("id", ""))):
        raise ValueError("invalid revision ID")
    if type(doc.get("base_version")) is not int or doc["base_version"] < 1 or not nonempty(doc.get("base_digest")):
        raise ValueError("revision needs base version and digest")
    if doc.get("kind") not in KINDS or not nonempty(doc.get("reason")) or not nonempty(doc.get("impact_review")):
        raise ValueError("revision kind, reason and impact_review required")
    for field in ("decision_ids", "evidence", "task_ids", "code_paths", "test_ids"):
        if not string_list(doc.get(field)):
            raise ValueError("revision " + field + " must be a unique string array")
    if not doc["evidence"] or not nonempty(doc.get("preserved_behavior")):
        raise ValueError("revision needs evidence and preserved_behavior")
    if not isinstance(doc.get("changes"), list) or not doc['changes']:
        raise ValueError("revision needs changes")


def proposals(folder, feature_id):
    directory = folder / "revisions"
    if directory.resolve() != directory:
        raise ValueError("symlinked revision directory rejected")
    result = {}
    if directory.exists():
        for path in sorted(directory.glob("CHG-*.json")):
            if path.is_symlink():
                raise ValueError("symlinked revision rejected")
            doc = json.loads(path.read_text())
            validate_proposal(doc, feature_id)
            if path.stem != doc['id']:
                raise ValueError("revision ID differs from filename")
            result[doc['id']] = doc
    return result


def inspect(folder, doc):
    b = doc.get("feature", {}).get("baseline")
    if b is None:
        return None, {}, []
    if (not isinstance(b, dict) or type(b.get('version')) is not int or b['version'] < 1
            or any(not isinstance(b.get(k), list) for k in ('initial_requirements', 'applied', 'cancelled', 'deliveries'))):
        raise ValueError("invalid feature.baseline")
    records = proposals(folder, doc['feature']['id'])
    reconstructed = semantics(b['initial_requirements'])
    version = 1
    handled = set()
    versions = {1: digest(reconstructed)}
    for event in b['applied']:
        if not isinstance(event, dict):
            raise ValueError("invalid applied event")
        rid = event.get('id')
        if rid in handled or rid not in records:
            raise ValueError("missing/duplicate applied revision")
        record = records[rid]
        if (event.get('proposal_digest') != digest(record) or record['base_version'] != version
                or record['base_digest'] != digest(reconstructed)):
            raise ValueError("applied revision modified or history chain broken")
        reconstructed = semantics(apply_changes(reconstructed, record['changes']))
        version += 1
        if event.get('version') != version or event.get('result_digest') != digest(reconstructed):
            raise ValueError("applied revision result differs")
        if not nonempty(event.get('at')) or not nonempty(event.get('decision_digest')):
            raise ValueError("applied revision lacks confirmation snapshot")
        handled.add(rid)
        versions[version] = digest(reconstructed)
    for event in b['cancelled']:
        if (not isinstance(event, dict) or event.get('id') not in records or event['id'] in handled
                or event.get('proposal_digest') != digest(records[event['id']]) or not nonempty(event.get('reason'))):
            raise ValueError("invalid cancelled revision")
        handled.add(event['id'])
    if version != b['version'] or digest(reconstructed) != b.get('digest') or digest(semantics(doc['requirements'])) != b['digest']:
        raise ValueError("baseline drift: use a reviewed revision instead of directly editing requirement meaning")
    for delivery in b['deliveries']:
        if (not isinstance(delivery, dict) or type(delivery.get('version')) is not int
                or delivery['version'] not in versions or delivery.get('requirements_digest') != versions[delivery['version']]
                or any(not nonempty(delivery.get(k)) for k in ('code_revision', 'evidence', 'evidence_sha256', 'at'))):
            raise ValueError("invalid baseline delivery evidence")
    pending = [v for k, v in records.items() if k not in handled]
    if len(pending) > 1:
        raise ValueError("multiple open revisions; resolve explicitly")
    return b, records, pending


def validate_revisions(folder, doc, stage):
    try:
        baseline, _, pending = inspect(folder, doc)
        if baseline is None:
            return [], []
        errors, warnings = [], []
        if pending:
            (errors if stage in {'develop', 'check'} else warnings).append("pending revision: " + pending[0]['id'])
        accepted = max((x['version'] for x in baseline['deliveries']), default=0)
        if accepted != baseline['version']:
            warnings.append("baseline v%d is confirmed but delivery has not been verified" % baseline['version'])
            if doc['feature'].get('status') == 'complete':
                errors.append("complete requires delivery evidence for the current baseline")
        return errors, warnings
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return ["revision: " + str(exc)], []


def binding(root, feature_id):
    from feature_lifecycle import read_record
    _, _, doc = read_record(root, feature_id)
    folder = root / '.agent-workflow/features' / feature_id
    baseline, _, pending = inspect(folder, doc)
    if pending: raise ValueError('Resolve pending revision before project checks')
    return {'feature_id': feature_id, 'version': baseline['version'] if baseline else None,
            'digest': baseline['digest'] if baseline else None}
