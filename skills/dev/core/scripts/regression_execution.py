#!/usr/bin/env python3
"""Bind an actually executed device regression to its fix without claiming CI execution."""
import argparse
import copy
import json
from pathlib import Path
import re
import sys

from impact import digest, path_name, git
from evidence_carry import project_files, source_identity
from verification import read, save, plan_mutation


def evidence_hashes(folder, paths):
    import hashlib
    if not isinstance(paths, list) or not paths or len(paths) != len(set(paths)):
        raise ValueError('distinct archived evidence paths required')
    result = {}
    for name in paths:
        path_name(name)
        if not name.startswith('evidence/'):
            raise ValueError('execution evidence must be feature-local evidence files')
        p = folder / name
        if not p.is_file() or p.is_symlink() or not p.resolve().is_relative_to(folder.resolve()):
            raise ValueError('execution evidence missing or unsafe: ' + name)
        result[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def validate_execution(execution):
    if not isinstance(execution, dict) or execution.get('kind') != 'device' or execution.get('status') != 'passed' or execution.get('returncode') != 0:
        raise ValueError('actual successful device test execution required')
    for key in ('tested_revision', 'executed_at', 'environment', 'coverage'):
        if not isinstance(execution.get(key), str) or not execution[key].strip():
            raise ValueError('execution lacks ' + key)
    command, cases = execution.get('command'), execution.get('executed_cases')
    if not isinstance(command, list) or not command or not all(isinstance(v, str) and v.strip() for v in command):
        raise ValueError('exact executed command arguments required; not a command template')
    if not isinstance(cases, list) or not cases or not all(isinstance(v, str) and v.strip() for v in cases) or len(cases) != len(set(cases)):
        raise ValueError('executed regression cases required; compilation alone is not test execution')
    if execution.get('failed_cases') != [] or execution.get('skipped_cases') != []:
        raise ValueError('failed or skipped targeted cases cannot pass regression coverage')
    for key in ('test_files', 'evidence_refs', 'package_identity_refs'):
        values = execution.get(key)
        if not isinstance(values, list) or not values or not all(isinstance(v, str) for v in values) or len(values) != len(set(values)):
            raise ValueError('execution lacks distinct ' + key)
        for value in values:
            path_name(value)


def identity(root, folder, fix_id, test_id, execution):
    root = root.resolve()
    if folder.is_symlink() or not folder.resolve().is_relative_to(root):
        raise ValueError("unsafe feature directory")
    folder = folder.resolve()
    validate_execution(execution)
    fixes = read(folder / 'fixes.json')
    fix = next((f for f in fixes['fixes'] if f['id'] == fix_id), None)
    if not fix or test_id not in fix.get('regression_test_ids', []):
        raise ValueError('keep the declared FIX-to-TEST link before recording execution')
    req = read(folder / 'spec/requirements.json')
    tasks = read(folder / 'tasks.json')
    from fixes import validate_regression_scope
    errors = validate_regression_scope(fix, req['requirements'], tasks['tasks'])
    if errors:
        raise ValueError('; '.join(errors))
    if git(root, 'rev-parse', execution['tested_revision'] + '^{commit}').decode().strip() != execution['tested_revision']:
        raise ValueError('execution requires an available full tested revision')
    before = project_files(root, execution['tested_revision'])
    current = project_files(root)
    if before != current:
        raise ValueError('executed project tree differs from current tree; run affected regression')
    for path in execution['test_files']:
        if path not in before or before[path]['mode'] == '120000' or before[path]['kind'] != 'blob':
            raise ValueError('test source unavailable at executed revision: ' + path)
    refs = sorted(set(execution['evidence_refs'] + execution['package_identity_refs']))
    authority = None
    if (folder / 'spec/prd-intake.json').exists():
        sources = source_identity(root, folder)
        authority = {key: sources[key] for key in ('sources', 'source_status_claims')}
    content = {'feature_id': folder.name, 'fix_id': fix_id, 'test_id': test_id,
               'fix': {k: v for k, v in fix.items() if k != 'regression_execution_history'},
               'requirements': req['requirements'], 'decisions': read(folder / 'decisions.json'),
               'code_digest': digest(current), 'execution': execution,
               'artifacts': evidence_hashes(folder, refs), 'source_authority': authority}
    return content


def capture(root, folder, fix_id, test_id, execution):
    content = identity(root, folder, fix_id, test_id, execution)
    return {'schema_version': 1, 'inputs': content, 'input_digest': digest(content)}


def validate_receipt(entry):
    if not isinstance(entry, dict) or entry.get('schema_version') != 1:
        raise ValueError('invalid regression execution receipt')
    body = {k: value for k, value in entry.items() if k != 'receipt_digest'}
    if entry.get('receipt_digest') != digest(body):
        raise ValueError('regression execution receipt changed')
    inputs, review = entry.get('inputs'), entry.get('review')
    if not isinstance(inputs, dict) or entry.get('input_digest') != digest(inputs):
        raise ValueError('invalid regression execution input binding')
    validate_execution(inputs.get('execution'))
    if not isinstance(review, dict) or review.get('input_digest') != entry['input_digest'] or review.get('status') != 'supported':
        raise ValueError('regression execution review missing or mismatched')
    for key in ('reviewer', 'assertion_evidence', 'original_identity_evidence', 'routine_check_reason'):
        if not isinstance(review.get(key), str) or not review[key].strip():
            raise ValueError('execution review lacks ' + key)
    if not isinstance(inputs.get('artifacts'), dict) or not inputs['artifacts']:
        raise ValueError('execution lacks archived evidence hashes')


@plan_mutation
def apply(root, folder, snapshot_path, review_path):
    from feature_lifecycle import require_active
    require_active(read(folder / 'spec/requirements.json')['feature'])
    frozen, review = read(snapshot_path), read(review_path)
    inputs = frozen['inputs']
    if capture(root, folder, inputs['fix_id'], inputs['test_id'], inputs['execution']) != frozen:
        raise ValueError('execution inputs stale; preserve result and recapture')
    entry = dict(frozen, review=review)
    entry['receipt_digest'] = digest(entry)
    validate_receipt(entry)
    doc = read(folder / 'fixes.json'); original = copy.deepcopy(doc)
    fix = next(f for f in doc['fixes'] if f['id'] == inputs['fix_id'])
    history = fix.setdefault('regression_execution_history', [])
    if not isinstance(history, list):
        raise ValueError('invalid regression execution history')
    history.append(entry)
    if read(folder / 'fixes.json') != original:
        raise ValueError('fix record changed during execution registration')
    if capture(root, folder, inputs['fix_id'], inputs['test_id'], inputs['execution']) != frozen or read(folder / 'fixes.json') != original:
        raise ValueError('execution inputs changed before save; preserve review and recapture')
    save(folder / 'fixes.json', doc)
    print('REGRESSION_EXECUTION_RECORDED: executed device coverage; routine gate unchanged')


def current_evidence(root, folder, fix, test_id):
    history = fix.get('regression_execution_history', [])
    if not isinstance(history, list):
        raise ValueError('invalid regression execution history')
    latest = None
    for entry in history:
        validate_receipt(entry)
        if entry['inputs'].get('test_id') == test_id:
            latest = entry
    if latest is None:
        return False
    inputs = latest['inputs']
    if inputs.get('fix_id') != fix['id'] or inputs.get('feature_id') != folder.name:
        raise ValueError('regression execution belongs to another fix/feature')
    return identity(root, folder, fix['id'], test_id, inputs['execution']) == inputs


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['capture', 'apply'])
    p.add_argument('root', type=Path); p.add_argument('feature_id')
    p.add_argument('--fix'); p.add_argument('--test'); p.add_argument('--execution', type=Path)
    p.add_argument('--snapshot', type=Path); p.add_argument('--review', type=Path)
    args = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.feature_id):
        p.error('invalid feature ID')
    root = args.root.resolve(); folder = root / '.agent-workflow/features' / args.feature_id
    try:
        if args.action == 'capture':
            if not args.fix or not args.test or not args.execution:
                p.error('capture requires --fix --test --execution')
            print(json.dumps(capture(root, folder, args.fix, args.test, read(args.execution)), ensure_ascii=False, indent=2))
        else:
            if not args.snapshot or not args.review:
                p.error('apply requires --snapshot --review')
            apply(root, folder, args.snapshot, args.review)
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('REGRESSION_EXECUTION_ERROR: ' + str(exc), file=sys.stderr); return 1


if __name__ == '__main__':
    sys.exit(main())
