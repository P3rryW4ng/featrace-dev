#!/usr/bin/env python3
"""Track semantic task wording separately from task progress and execution evidence."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile


PROGRESS_FIELDS = {
    'status', 'test_evidence', 'test_waiver', 'verification', 'implementation_revision',
    'started_at', 'completed_at', 'assignee',
}


def text(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value):
    return isinstance(value, list) and all(text(item) for item in value)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def semantic_tasks(tasks):
    if not isinstance(tasks, list):
        raise ValueError('tasks must be an array')
    result, ids = [], set()
    for item in tasks:
        if not isinstance(item, dict) or not text(item.get('id')) or item['id'] in ids:
            raise ValueError('tasks need unique non-empty IDs')
        ids.add(item['id'])
        result.append({key: copy.deepcopy(value) for key, value in item.items() if key not in PROGRESS_FIELDS})
    return sorted(result, key=lambda item: item['id'])


def snapshot(tasks):
    values = semantic_tasks(tasks)
    return {'digest': digest(values), 'tasks': values}


def changed_ids(before, after):
    old = {item['id']: item for item in before}
    new = {item['id']: item for item in after}
    return sorted(task_id for task_id in set(old) | set(new) if old.get(task_id) != new.get(task_id))


def affected_requirements(before, after, task_ids):
    ids = set(task_ids)
    values = set()
    for item in list(before) + list(after):
        if item.get('id') in ids and strings(item.get('requirement_ids', [])):
            values.update(item['requirement_ids'])
    return sorted(values)


def read(path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_atomic(path, value):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def validate_history(history):
    if not isinstance(history, list):
        raise ValueError('history must be an array')
    seen = set()
    for entry in history:
        payload = copy.deepcopy(entry) if isinstance(entry, dict) else {}
        history_id = payload.pop('history_id', None)
        if (not isinstance(entry, dict) or not text(history_id) or history_id in seen
                or history_id != digest(payload) or not isinstance(entry.get('review'), dict)):
            raise ValueError('invalid or duplicate task review history')
        seen.add(history_id)
    return seen


def validate_task_review(folder, req_doc, tasks, stage):
    errors, warnings = [], []
    required = req_doc.get('feature', {}).get('task_review_required', False)
    if not isinstance(required, bool):
        return ['feature.task_review_required must be boolean'], []
    strict = stage in ('develop', 'check')
    path = folder / 'task-review.json'
    if not path.exists():
        message = 'task semantic review missing; sync and review tasks before business-code edits'
        (errors if required and strict else warnings).append(message)
        return errors, warnings
    try:
        doc = read(path)
        if (not isinstance(doc, dict) or doc.get('schema_version') != 1
                or doc.get('feature_id') != folder.name):
            raise ValueError('identity/schema mismatch')
        current = snapshot(tasks)
        if doc.get('current') != current:
            errors.append('task semantic review is stale; run sync and review changed tasks')
            return errors, warnings
        validate_history(doc.get('history', []))
        review = doc.get('review')
        if not isinstance(review, dict) or review.get('digest') != current['digest']:
            prior = review.get('tasks', []) if isinstance(review, dict) and isinstance(review.get('tasks'), list) else []
            changed = changed_ids(prior, current['tasks'])
            if strict:
                errors.append('task semantics need review: ' + (', '.join(changed) or 'unknown'))
            else:
                warnings.append('task semantics need review: ' + (', '.join(changed) or 'unknown'))
            return errors, warnings
        review_payload = copy.deepcopy(review)
        review_id = review_payload.pop('review_id', None)
        previous = doc['history'][-1]['review'].get('tasks', []) if doc['history'] else []
        expected_tasks = changed_ids(previous, current['tasks'])
        expected_requirements = affected_requirements(previous, current['tasks'], expected_tasks)
        if (not text(review_id) or review_id != digest(review_payload)
                or not text(review.get('reviewer')) or not text(review.get('notes'))
                or not strings(review.get('changed_task_ids')) or not review.get('changed_task_ids')
                or not strings(review.get('requirement_ids')) or not review.get('requirement_ids')
                or not strings(review.get('evidence_refs')) or not review.get('evidence_refs')
                or review.get('tasks') != current['tasks']
                or review.get('changed_task_ids') != expected_tasks
                or review.get('requirement_ids') != expected_requirements):
            errors.append('task semantic review needs reviewer, notes, changed tasks, requirements and evidence')
        return errors, warnings
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return ['invalid task semantic review: ' + str(exc)], warnings


def render(folder):
    doc = read(folder / 'task-review.json')
    if not isinstance(doc, dict):
        return
    review = doc.get('review', {}) if isinstance(doc.get('review'), dict) else {}
    current = doc.get('current', {}) if isinstance(doc.get('current'), dict) else {}
    prior = review.get('tasks', []) if isinstance(review.get('tasks'), list) else []
    changed = changed_ids(prior, current.get('tasks', [])) if isinstance(current.get('tasks'), list) else []
    lines = ['# Task semantic review', '', 'Generated view; edit tasks.json, then use task_review.py.', '',
             '- Current digest: ' + current.get('digest', ''),
             '- Reviewed digest: ' + review.get('digest', ''),
             '- Pending task IDs: ' + (', '.join(changed) or 'none'),
             '- Reviewer: ' + review.get('reviewer', ''),
             '- Notes: ' + review.get('notes', ''),
             '- Evidence: ' + ', '.join(review.get('evidence_refs', [])),
             '- Prior reviews: ' + str(len(doc.get('history', []))), '']
    (folder / 'task-review.md').write_text('\n'.join(lines))


def load_workspace(root, feature_id):
    root = Path(root).resolve()
    folder = root / '.agent-workflow/features' / feature_id
    req_path, tasks_path = folder / 'spec/requirements.json', folder / 'tasks.json'
    req, task_doc = read(req_path), read(tasks_path)
    if (not isinstance(req, dict) or req.get('feature', {}).get('id') != feature_id
            or not isinstance(task_doc, dict) or task_doc.get('feature_id') != feature_id):
        raise ValueError('requirements/tasks identity mismatch')
    return folder, req_path, req, task_doc.get('tasks')


def sync(root, feature_id):
    folder, req_path, req, tasks = load_workspace(root, feature_id)
    current = snapshot(tasks)
    path = folder / 'task-review.json'
    old = read(path, {})
    if not isinstance(old, dict):
        raise ValueError('existing task review must be an object')
    history = copy.deepcopy(old.get('history', []))
    validate_history(history)
    review = copy.deepcopy(old.get('review', {}))
    if not isinstance(review, dict):
        raise ValueError('existing task review must contain an object review')
    record = {'schema_version': 1, 'feature_id': feature_id, 'current': current,
              'review': review, 'history': history}
    req['feature']['task_review_required'] = True
    write_atomic(req_path, req)
    write_atomic(path, record)
    render(folder)
    prior = review.get('tasks', []) if isinstance(review.get('tasks'), list) else []
    return record, changed_ids(prior, current['tasks'])


def review(root, feature_id, reviewer, notes, task_ids, requirement_ids, evidence_refs):
    record, changed = sync(root, feature_id)
    folder, _, _, _ = load_workspace(root, feature_id)
    old_review = record.get('review', {})
    before = old_review.get('tasks', []) if isinstance(old_review.get('tasks'), list) else []
    affected = affected_requirements(before, record['current']['tasks'], changed)
    if not changed:
        raise ValueError('task semantics are already current')
    if sorted(set(task_ids)) != changed:
        raise ValueError('reviewed task IDs must exactly match changed tasks: ' + ', '.join(changed))
    if sorted(set(requirement_ids)) != affected:
        raise ValueError('reviewed requirement IDs must exactly match affected requirements: ' + ', '.join(affected))
    if not all(text(value) for value in (reviewer, notes)) or not strings(evidence_refs) or not evidence_refs:
        raise ValueError('reviewer, notes and evidence refs are required')
    history = record['history']
    known = validate_history(history)
    if old_review.get('digest'):
        archived = {'review': copy.deepcopy(old_review), 'superseded_by_digest': record['current']['digest']}
        archived['history_id'] = digest(archived)
        if archived['history_id'] not in known:
            history.append(archived)
    new_review = {'digest': record['current']['digest'], 'tasks': copy.deepcopy(record['current']['tasks']),
                  'reviewed_at': datetime.now(timezone.utc).isoformat(), 'reviewer': reviewer,
                  'notes': notes, 'changed_task_ids': changed, 'requirement_ids': affected,
                  'evidence_refs': evidence_refs}
    new_review['review_id'] = digest(new_review)
    record['review'] = new_review
    write_atomic(folder / 'task-review.json', record)
    render(folder)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('sync', 'show'):
        command = sub.add_parser(action)
        command.add_argument('project', type=Path)
        command.add_argument('feature_id')
    command = sub.add_parser('review')
    command.add_argument('project', type=Path)
    command.add_argument('feature_id')
    command.add_argument('--reviewer', required=True)
    command.add_argument('--notes', required=True)
    command.add_argument('--task', action='append', default=[])
    command.add_argument('--requirement', action='append', default=[])
    command.add_argument('--evidence', action='append', default=[])
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.feature_id):
        parser.error('invalid feature ID')
    try:
        if args.action == 'sync':
            record, changed = sync(args.project, args.feature_id)
            print('TASK_REVIEW_SYNCED: changed=%s current=%s reviewed=%s' %
                  (','.join(changed) or 'none', record['current']['digest'], record.get('review', {}).get('digest', '')))
        elif args.action == 'review':
            record = review(args.project, args.feature_id, args.reviewer, args.notes,
                            args.task, args.requirement, args.evidence)
            print('TASK_REVIEW_RECORDED: digest=' + record['review']['digest'])
        else:
            folder, _, _, _ = load_workspace(args.project, args.feature_id)
            print(json.dumps(read(folder / 'task-review.json', {}), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print('TASK_REVIEW_ERROR: ' + str(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
