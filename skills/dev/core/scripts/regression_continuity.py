#!/usr/bin/env python3
"""Review applicability of an original device run; never manufacture execution."""
import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

from impact import digest, git, path_name
from evidence_carry import project_files, source_identity
from verification import read, save, plan_mutation

KIND = 'reviewed_device_continuity'
REVIEW_FIELDS = ('assertion_evidence', 'original_identity_evidence', 'dependency_evidence',
                 'authority_evidence', 'environment_evidence', 'counterexample_check', 'limits')


def present(doc):
    if not isinstance(doc, dict):
        return False
    if doc.get('regression_continuity_reviews'):
        return True
    fixes = doc.get('fixes', [])
    return isinstance(fixes, list) and any(
        isinstance(f, dict) and isinstance(f.get('regression_execution_history', []), list) and any(
            isinstance(e, dict) and e.get('schema_version') == 2 for e in f.get('regression_execution_history', []))
        for f in fixes)


def key(fix_id, test_id):
    return fix_id + ':' + test_id


def text(value):
    return isinstance(value, str) and bool(value.strip())


def source(doc, request, latest=True):
    from regression_execution import validate_receipt
    fix = next((f for f in doc['fixes'] if f['id'] == request['fix_id']), None)
    if not fix or (latest and request['test_id'] not in fix.get('regression_test_ids', [])):
        raise ValueError('keep the FIX-to-TEST link')
    history = fix.get('regression_execution_history', [])
    originals = []
    for i, entry in enumerate(history):
        validate_receipt(entry)
        if entry['inputs'].get('test_id') == request['test_id'] and entry['schema_version'] == 1:
            originals.append(i)
    index = request.get('source_index')
    if type(index) is not int or index not in originals or (latest and index != originals[-1]):
        raise ValueError('select the latest original execution; no derived source or older green')
    entry = history[index]
    if entry['inputs'].get('feature_id') != doc.get('feature_id') or entry['inputs'].get('fix_id') != fix['id']:
        raise ValueError('original execution belongs to another feature/FIX')
    return fix, entry


def validate_entry(entry):
    if not isinstance(entry, dict) or entry.get('schema_version') != 2 or entry.get('kind') != KIND:
        raise ValueError('unsupported device continuity receipt')
    if entry.get('receipt_digest') != digest({k: v for k, v in entry.items() if k != 'receipt_digest'}):
        raise ValueError('device continuity receipt changed')
    inputs = entry.get('inputs', {})
    for field in ('feature_id', 'fix_id', 'test_id', 'event_id', 'source_receipt_digest'):
        if not text(inputs.get(field)):
            raise ValueError('device continuity lacks ' + field)
    if type(inputs.get('source_index')) is not int or inputs['source_index'] < 0:
        raise ValueError('invalid original execution locator')


def validate_review(review, snapshot):
    if not isinstance(review, dict) or review.get('input_digest') != snapshot.get('input_digest'):
        raise ValueError('continuity review input mismatch')
    if review.get('context') != 'fresh' or not text(review.get('reviewer')):
        raise ValueError('fresh-context reviewer required; identity is an attestation, not machine proof')
    targets = {t['id']: t for t in snapshot['inputs']['targets']}
    findings = review.get('findings')
    if not isinstance(findings, list) or len(findings) != len(targets) or {f.get('id') for f in findings if isinstance(f, dict)} != set(targets):
        raise ValueError('review every selected FIX/TEST exactly once')
    for finding in findings:
        if finding.get('verdict') not in ('supported', 'affected', 'unknown', 'partial'):
            raise ValueError('invalid continuity verdict')
        for field in REVIEW_FIELDS:
            if not text(finding.get(field)):
                raise ValueError('review lacks ' + field)
        assessments = finding.get('changes')
        expected = {c['path'] for c in snapshot['inputs']['changes']}
        if not isinstance(assessments, list) or len(assessments) != len(expected) or {a.get('path') for a in assessments if isinstance(a, dict)} != expected:
            raise ValueError('investigate every changed path for each FIX/TEST')
        for assessment in assessments:
            if assessment.get('effect') not in ('unaffected', 'affected', 'unknown') or not text(assessment.get('evidence')):
                raise ValueError('changed-path assessment incomplete')
        if finding['verdict'] == 'supported' and any(a['effect'] != 'unaffected' for a in assessments):
            raise ValueError('supported finding contradicts changed-path assessment')
    selected = review.get('apply_targets')
    if not isinstance(selected, list) or not selected or len(selected) != len(set(selected)):
        raise ValueError('explicit distinct supported apply_targets required')
    supported = {f['id'] for f in findings if f['verdict'] == 'supported'}
    if not set(selected) <= supported:
        raise ValueError('cannot apply unknown/partial/affected or unreviewed targets')


def validate_document(doc):
    events = doc.get('regression_continuity_reviews', [])
    if not isinstance(events, list):
        raise ValueError('invalid device continuity event ledger')
    by_id = {}
    for event in events:
        if not isinstance(event, dict) or event.get('schema_version') != 1:
            raise ValueError('unsupported device continuity event')
        body = {k: v for k, v in event.items() if k != 'event_id'}
        if event.get('event_id') != digest(body) or event['event_id'] in by_id:
            raise ValueError('device continuity event changed or duplicated')
        snapshot = event.get('snapshot', {})
        if snapshot.get('schema_version') != 1 or snapshot.get('input_digest') != digest(snapshot.get('inputs')):
            raise ValueError('device continuity frozen input changed')
        if snapshot['inputs'].get('feature_id') != doc.get('feature_id') or not text(event.get('reviewed_at')):
            raise ValueError('device continuity event belongs to another feature or lacks review time')
        validate_review(event.get('review'), snapshot)
        by_id[event['event_id']] = event
    used = {}
    for fix in doc['fixes']:
        for entry in fix.get('regression_execution_history', []):
            if entry.get('schema_version') != 2:
                continue
            validate_entry(entry)
            inp = entry['inputs']; event = by_id.get(inp['event_id'])
            ident = key(inp['fix_id'], inp['test_id'])
            if not event or inp['fix_id'] != fix['id'] or inp['feature_id'] != doc.get('feature_id') or ident not in event['review']['apply_targets']:
                raise ValueError('missing, cross-FIX or unselected continuity event')
            targets = event['snapshot']['inputs']['targets']
            target = next((t for t in targets if t['id'] == ident), None)
            if not target or inp['source_index'] != target['source_index'] or inp['source_receipt_digest'] != target['source_receipt_digest']:
                raise ValueError('continuity source locator differs from reviewed source')
            _, origin = source(doc, dict(fix_id=fix['id'], test_id=inp['test_id'], source_index=inp['source_index']), latest=False)
            if origin['receipt_digest'] != inp['source_receipt_digest']:
                raise ValueError('original device receipt changed')
            used.setdefault(inp['event_id'], []).append(ident)
    for ident, event in by_id.items():
        if sorted(used.get(ident, [])) != sorted(event['review']['apply_targets']):
            raise ValueError('orphan, duplicate or incomplete continuity batch')


def check_worktree(root, tree):
    """Do not let assume-unchanged/skip-worktree hide actual tracked input bytes."""
    import hashlib
    import stat
    algorithm = git(root, 'rev-parse', '--show-object-format').decode().strip()
    if algorithm not in ('sha1', 'sha256'):
        raise ValueError('unsupported Git object identity')
    from managed_links import inspect
    for name in tree: path_name(name)
    entries = {n: {'mode': e['mode'], 'oid': e['blob']} for n, e in tree.items()}
    links, members = inspect(root, entries, entries, clean=True)
    for name, expected in tree.items():
        if name in links or name in members: continue
        path_name(name)
        path = root
        for component in Path(name).parts:
            path /= component
            if path.is_symlink():
                raise ValueError('symlink input cannot certify device continuity: ' + name)
        before = path.stat()
        if expected['kind'] != 'blob' or not stat.S_ISREG(before.st_mode):
            raise ValueError('nonregular/submodule input cannot certify continuity: ' + name)
        mode = '100755' if before.st_mode & 0o111 else '100644'
        h = hashlib.new(algorithm)
        h.update(('blob ' + str(before.st_size) + '\0').encode())
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(block)
        after = path.stat()
        if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_mode) != (after.st_ino, after.st_size, after.st_mtime_ns, after.st_mode):
            raise ValueError('input moved during continuity capture: ' + name)
        if mode != expected['mode'] or h.hexdigest() != expected['blob']:
            raise ValueError('actual input differs from committed continuity target: ' + name)


def semantic_identity(root, folder, requests, target_revision=None):
    from regression_execution import evidence_hashes
    root = root.resolve()
    if Path(git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != root:
        raise ValueError('device continuity requires the Git project root')
    if folder.is_symlink() or not folder.resolve().is_relative_to(root):
        raise ValueError('unsafe feature directory')
    if not isinstance(requests, list) or not requests:
        raise ValueError('explicit continuity requests required')
    doc = read(folder / 'fixes.json')
    validate_document(doc)
    req = read(folder / 'spec/requirements.json'); decisions = read(folder / 'decisions.json')
    tasks = read(folder / 'tasks.json')
    if doc.get('feature_id') != folder.name:
        raise ValueError('fix document belongs to another feature')
    current = project_files(root)  # Also rejects dirty business/index/untracked inputs.
    check_worktree(root, current)
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    revision = target_revision or head
    if git(root, 'rev-parse', revision + '^{commit}').decode().strip() != revision:
        raise ValueError('full current target revision required')
    git(root, 'merge-base', '--is-ancestor', revision, head)
    if project_files(root, revision) != current:
        raise ValueError('current target tree changed')
    # Keep workflow commits from rewriting the reviewed code revision.
    regress = read(folder / 'regression-review.json') if (folder / 'regression-review.json').is_file() else None
    authority = None
    if (folder / 'spec/prd-intake.json').is_file():
        src = source_identity(root, folder)
        authority = {k: src[k] for k in ('sources', 'source_status_claims')}
    targets, changes, seen = [], {}, set()
    for request in requests:
        if not isinstance(request, dict):
            raise ValueError('invalid continuity request')
        fid, tid = request.get('fix_id'), request.get('test_id')
        if not text(fid) or not text(tid) or key(fid, tid) in seen:
            raise ValueError('distinct explicit FIX/TEST pairs required')
        ident = key(fid, tid); seen.add(ident)
        fix, origin = source(doc, request)
        from fixes import validate_regression_scope
        errors = validate_regression_scope(fix, req['requirements'], tasks['tasks'])
        if errors:
            raise ValueError('; '.join(errors))
        if fix.get('status') != 'verified':
            raise ValueError('unverified or withdrawn fix cannot be certified by continuity')
        # Do not select an old green over a current structured failure. Historical
        # prior_results are retained for the reviewer, not treated as current.
        plan_path = folder / 'verification.json'
        if plan_path.is_file():
            for row in read(plan_path).get('items', []):
                history = row.get('history', [])
                if tid in row.get('test_ids', []) and history and history[-1].get('status') == 'failed':
                    raise ValueError('current verification failure conflicts with device continuity')
        if isinstance(regress, dict):
            for disposition in regress.get('dispositions', []):
                result = disposition.get('result', {})
                if disposition.get('candidate_id') == folder.name + ':' + fid and isinstance(result, dict) and result.get('status') == 'failed':
                    raise ValueError('current regression failure conflicts with device continuity')
        old = origin['inputs']; execution = old['execution']
        tested = execution['tested_revision']
        if git(root, 'rev-parse', tested + '^{commit}').decode().strip() != tested:
            raise ValueError('original full tested revision unavailable')
        git(root, 'merge-base', '--is-ancestor', tested, revision)
        before = project_files(root, tested)
        if old.get('code_digest') != digest(before):
            raise ValueError('original tested tree binding changed')
        refs = sorted(set(execution['evidence_refs'] + execution['package_identity_refs']))
        if evidence_hashes(folder, refs) != old.get('artifacts'):
            raise ValueError('original archived execution/package evidence changed')
        for field in ('expected', 'requirement_ids', 'regression_test_ids', 'regression_scope_notes'):
            if fix.get(field) != old['fix'].get(field):
                raise ValueError('original FIX requirements/cases changed: ' + field)
        related = set(fix.get('requirement_ids', []))
        relevant_tasks = [t for t in tasks['tasks'] if t.get('id') in fix.get('task_ids', [])]
        related.update(x for t in relevant_tasks for x in t.get('requirement_ids', []))
        current_req = [x for x in req['requirements'] if x['id'] in related]
        old_req = [x for x in old['requirements'] if x['id'] in related]
        if not related or current_req != old_req:
            raise ValueError('related requirement changed or unavailable')
        deps = request.get('dependencies')
        if not isinstance(deps, list) or not deps or len(deps) != len(set(deps)) or not all(text(x) for x in deps):
            raise ValueError('explicit investigated dependencies required')
        paths = sorted(set(deps + execution['test_files'] + fix.get('code_paths', [])))
        scope = {}
        for path in paths:
            path_name(path)
            a, b = before.get(path), current.get(path)
            if not a or not b or a['kind'] != 'blob' or b['kind'] != 'blob' or a['mode'] not in ('100644', '100755') or b['mode'] not in ('100644', '100755'):
                raise ValueError('dependency unavailable/unsafe at original or target: ' + path)
            if path in execution['test_files'] and a != b:
                raise ValueError('original test source/assertion changed')
            scope[path] = {'original': a, 'target': b}
        delta = []
        for path in sorted(set(before) | set(current)):
            if before.get(path) != current.get(path):
                delta.append(path)
                changes.setdefault(path, {})[tested] = {'original': before.get(path), 'target': current.get(path)}
        patch = git(root, 'diff', '--no-ext-diff', '--no-textconv', '--binary', tested, revision, '--', '.', ':(exclude).agent-workflow')
        targets.append({'id': ident, 'fix_id': fid, 'test_id': tid,
                        'source_index': request['source_index'], 'source_receipt_digest': origin['receipt_digest'],
                        'execution_identity': {'tested_revision': tested, 'executed_at': execution['executed_at'],
                                               'package_identity_refs': execution['package_identity_refs'],
                                               'executed_case_count': len(execution['executed_cases'])},
                        'current_fix_digest': digest({k: v for k, v in fix.items() if k != 'regression_execution_history'}),
                        'related_requirements_digest': digest(current_req), 'related_tasks_digest': digest(relevant_tasks),
                        'read_refs': ['fixes.json#' + fid, 'spec/requirements.json', 'tasks.json', 'decisions.json'],
                        'dependencies': scope, 'original_artifacts': old['artifacts'],
                        'changed_paths': delta, 'patch_digest': digest(patch.hex())})
    if project_files(root) != current:
        raise ValueError('project tree changed during continuity capture')
    check_worktree(root, current)
    return {'feature_id': folder.name, 'target_revision': revision, 'target_tree_digest': digest(current),
            'decisions_digest': digest(decisions), 'source_authority': authority, 'regression_review_digest': digest(regress),
            'targets': targets, 'requests': requests,
            'changes': [{'path': p, 'comparisons': changes[p]} for p in sorted(changes)]}


def capture(root, folder, requests):
    inputs = semantic_identity(root, folder, requests)
    doc = read(folder / 'fixes.json')
    return {'schema_version': 1, 'inputs': inputs, 'input_digest': digest(inputs),
            'guard_digest': digest(doc)}


@plan_mutation
def apply(root, folder, snapshot_path, review_path):
    from feature_lifecycle import require_active
    require_active(read(folder / 'spec/requirements.json')['feature'])
    frozen, review = read(snapshot_path), read(review_path)
    if capture(root, folder, frozen['inputs']['requests']) != frozen:
        raise ValueError('device continuity inputs stale; recapture actual inputs')
    validate_review(review, frozen)
    doc = read(folder / 'fixes.json'); original = copy.deepcopy(doc)
    ledger = doc.setdefault('regression_continuity_reviews', [])
    if any(e['snapshot']['input_digest'] == frozen['input_digest'] for e in ledger):
        raise ValueError('device continuity already applied to these inputs')
    event = {'schema_version': 1, 'snapshot': frozen, 'review': review,
             'reviewed_at': datetime.now(timezone.utc).isoformat()}
    event['event_id'] = digest(event); ledger.append(event)
    for target in frozen['inputs']['targets']:
        if target['id'] not in review['apply_targets']:
            continue
        fix = next(f for f in doc['fixes'] if f['id'] == target['fix_id'])
        entry = {'schema_version': 2, 'kind': KIND,
                 'inputs': {k: target[k] for k in ('fix_id', 'test_id', 'source_index', 'source_receipt_digest')}}
        entry['inputs'].update(feature_id=folder.name, event_id=event['event_id'])
        entry['receipt_digest'] = digest(entry)
        fix['regression_execution_history'].append(entry)
    validate_document(doc)
    if capture(root, folder, frozen['inputs']['requests']) != frozen or read(folder / 'fixes.json') != original:
        raise ValueError('device continuity inputs changed before save')
    save(folder / 'fixes.json', doc)
    print('DEVICE_CONTINUITY_RECORDED: reviewed applicability; no device execution')


def current(root, folder, doc, fix, test_id, entry):
    validate_document(doc)
    event = next(e for e in doc['regression_continuity_reviews'] if e['event_id'] == entry['inputs']['event_id'])
    inputs = event['snapshot']['inputs']
    return semantic_identity(root, folder, inputs['requests'], inputs['target_revision']) == inputs


def summaries(root, folder, doc):
    validate_document(doc)
    result = []
    for fix in doc['fixes']:
        latest = {}
        for entry in fix.get('regression_execution_history', []):
            latest[entry['inputs']['test_id']] = entry
        for test_id, entry in latest.items():
            if entry.get('schema_version') != 2:
                continue
            event = next(e for e in doc['regression_continuity_reviews'] if e['event_id'] == entry['inputs']['event_id'])
            target = next(t for t in event['snapshot']['inputs']['targets'] if t['id'] == key(fix['id'], test_id))
            try:
                valid = current(root, folder, doc, fix, test_id, entry)
                status, reason = ('current' if valid else 'stale'), ''
            except (OSError, ValueError, KeyError, TypeError) as exc:
                status, reason = 'stale', str(exc)
            result.append({'fix_id': fix['id'], 'test_id': test_id, 'kind': KIND,
                           'source': {k: entry['inputs'][k] for k in ('source_index', 'source_receipt_digest')},
                           'execution_identity': target['execution_identity'], 'reviewed_at': event['reviewed_at'],
                           'reviewed_revision': event['snapshot']['inputs']['target_revision'],
                           'event_id': event['event_id'], 'status': status, 'reason': reason,
                           'new_execution': False})
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('capture', 'apply'))
    p.add_argument('root', type=Path); p.add_argument('feature_id')
    p.add_argument('--requests', type=Path); p.add_argument('--snapshot', type=Path); p.add_argument('--review', type=Path)
    a = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', a.feature_id):
        p.error('invalid feature ID')
    folder = a.root.resolve() / '.agent-workflow/features' / a.feature_id
    try:
        if a.action == 'capture':
            if not a.requests: p.error('capture requires --requests')
            print(json.dumps(capture(a.root, folder, read(a.requests)), ensure_ascii=False, indent=2))
        else:
            if not a.snapshot or not a.review: p.error('apply requires --snapshot --review')
            apply(a.root, folder, a.snapshot, a.review)
        return 0
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        print('DEVICE_CONTINUITY_ERROR: ' + str(exc), file=sys.stderr); return 1


if __name__ == '__main__':
    sys.exit(main())
