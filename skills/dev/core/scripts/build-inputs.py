#!/usr/bin/env python3
"""Show one Build task's relevant frozen authority without creating another record."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                     separators=(',', ':')).encode()).hexdigest()


def read_record(root, name, hashes, required=True):
    target = root
    for part in Path(name).parts:
        target = target / part
        if target.is_symlink():
            raise ValueError('symlink authority is not supported: ' + name)
    if not target.is_file():
        if required:
            raise ValueError('required authority missing: ' + name)
        return None
    raw = target.read_bytes()
    hashes[name] = hashlib.sha256(raw).hexdigest()
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError('invalid authority JSON: ' + name) from exc
    if not isinstance(value, dict):
        raise ValueError('authority must be an object: ' + name)
    return value


def rows(doc, key, name):
    value = doc.get(key)
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ValueError('invalid ' + name + '.' + key)
    return value


def scoped(row, requirements):
    linked = row.get('requirement_ids')
    if linked is None:
        return True  # No explicit linkage means a possible cross-cutting rule.
    if not isinstance(linked, list) or any(not isinstance(item, str) for item in linked):
        return True  # Do not silently omit malformed or uncertain authority.
    return not linked or bool(set(linked) & requirements)


def collect(root, feature_id, task_id):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', feature_id):
        raise ValueError('invalid feature ID')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', task_id):
        raise ValueError('invalid task ID')
    root = Path(root).resolve()
    prefix = '.agent-workflow/features/' + feature_id + '/'
    hashes = {}

    def read(name, required=True):
        return read_record(root, prefix + name, hashes, required)

    spec = read('spec/requirements.json')
    if not isinstance(spec.get('feature'), dict) or spec['feature'].get('id') != feature_id:
        raise ValueError('requirements feature ID mismatch')
    tasks_doc = read('tasks.json')
    if tasks_doc.get('feature_id', feature_id) != feature_id:
        raise ValueError('tasks feature ID mismatch')
    tasks = rows(tasks_doc, 'tasks', 'tasks')
    selected = [task for task in tasks if task.get('id') == task_id]
    if len(selected) != 1:
        raise ValueError('select exactly one existing task: ' + task_id)
    task = selected[0]
    ids = task.get('requirement_ids')
    if not isinstance(ids, list) or not ids or any(not isinstance(item, str) for item in ids):
        raise ValueError('task requirement_ids missing or invalid')
    selected_ids = set(ids)
    requirements = rows(spec, 'requirements', 'requirements')
    matching = [row for row in requirements if row.get('id') in selected_ids]
    if len(matching) != len(selected_ids):
        raise ValueError('task references a missing requirement')
    if any(row.get('status') != 'confirmed' for row in matching):
        raise ValueError('task requirement is not confirmed')

    decisions_doc = read('decisions.json')
    decisions = rows(decisions_doc, 'decisions', 'decisions')
    relevant_decisions = [row for row in decisions if scoped(row, selected_ids)]
    impact = read('impact.json')
    behaviors = rows(impact, 'behaviors', 'impact')
    relevant_behaviors = [row for row in behaviors
                          if row.get('kind') == 'preserve' or scoped(row, selected_ids)]
    trace_doc = read('traceability.json')
    links = rows(trace_doc, 'links', 'traceability')
    trace = [row for row in links if row.get('requirement_id') in selected_ids]
    task_review = read('task-review.json', required=False)
    regression = read('regression-review.json', required=False)
    if task_review is not None and (not isinstance(task_review.get('current'), dict)
                                    or not isinstance(task_review.get('review'), dict)):
        raise ValueError('invalid task-review digest index')
    if regression is not None and (not isinstance(regression.get('candidates'), list)
                                   or not isinstance(regression.get('dispositions'), list)):
        raise ValueError('invalid regression-review index')
    missing = [name for name, value in [('task-review.json', task_review),
                                        ('regression-review.json', regression)] if value is None]

    return {'schema_version': 1, 'kind': 'build_task_view', 'feature_id': feature_id,
            'task_id': task_id, 'task': task,
            'requirements': matching, 'decisions': relevant_decisions,
            'impact': {'base_revision': impact.get('base_revision'),
                       'reviewed_change_paths': impact.get('allowed_paths'),
                       'mechanisms': impact.get('mechanisms'),
                       'behaviors': relevant_behaviors},
            'traceability': trace,
            'review_index': {
                'task_semantics': None if task_review is None else {
                    'current_digest': (task_review.get('current') or {}).get('digest'),
                    'reviewed_digest': (task_review.get('review') or {}).get('digest')},
                'historical_regression': None if regression is None else {
                    'candidates': len(regression.get('candidates', [])),
                    'dispositions': len(regression.get('dispositions', []))}},
            'record_sha256': hashes, 'input_digest': digest(hashes),
            'missing_optional_records': missing,
            'omitted_explicitly_unrelated': {
                'requirements': len(requirements) - len(matching),
                'tasks': len(tasks) - 1,
                'decisions': len(decisions) - len(relevant_decisions),
                'impact_behaviors': len(behaviors) - len(relevant_behaviors)},
            'authority': 'read-only starting view; frozen records and original sources remain authoritative',
            'expand_when_needed': ['Read original sources cited by the selected requirements.',
                                   'Inspect callers, shared state and old behavior beyond task-owned paths.',
                                   'Read full decisions, impact or historical review when linkage is uncertain.',
                                   'Stop and return to Scope when a new dependency or product conflict appears.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('frozen_root', type=Path, help='RUN/inputs, not the live primary checkout')
    parser.add_argument('feature_id')
    parser.add_argument('task_id')
    args = parser.parse_args()
    try:
        print(json.dumps(collect(args.frozen_root, args.feature_id, args.task_id),
                         ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print('BUILD_INPUTS_ERROR: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
