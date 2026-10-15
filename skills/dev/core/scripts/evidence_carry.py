#!/usr/bin/env python3
"""Freeze and apply a reviewed carry-forward of a stale manual observation."""
import argparse
import copy
import json
from pathlib import Path
import sys

from impact import digest, git, path_name
import verification as v


REFERENCE_ACTUAL = 'Original observation retained by reference; no new execution.'


def observation_ref(row, observation):
    return {'item_id': row['id'], 'history_index': row['history'].index(observation),
            'result_hash': digest(observation), 'tested_revision': observation['tested_revision']}


class UncommittedBusinessChanges(ValueError):
    """Capture requires clean code; freshness queries only mark it stale."""
    def __init__(self, paths):
        self.paths = paths
        super().__init__('commit/review business worktree changes before carry capture: ' + ', '.join(paths))



def project_files(root, revision=None):
    """Content and mode identities, reconstructed from Git, not old receipts."""
    if revision:
        out = git(root, 'ls-tree', '-r', '-z', revision).split(b'\0')
        files = {}
        for item in out:
            if not item:
                continue
            meta, raw = item.split(b'\t', 1)
            mode, kind, oid = meta.decode().split()
            name = raw.decode('utf-8', 'surrogateescape')
            if name.startswith('.agent-workflow/'):
                continue
            files[name] = {'mode': mode, 'kind': kind, 'blob': oid}
        return files
    groups = [git(root, 'diff', '--name-only', '-z'),
              git(root, 'diff', '--cached', '--name-only', '-z'),
              git(root, 'ls-files', '--others', '--exclude-standard', '-z')]
    dirty = sorted({raw.decode('utf-8', 'surrogateescape') for group in groups
                    for raw in group.split(b'\0') if raw and not raw.startswith(b'.agent-workflow/')})
    if dirty:
        raise UncommittedBusinessChanges(dirty)
    return project_files(root, git(root, 'rev-parse', 'HEAD').decode().strip())


def historical(root, folder, revision, name):
    rel = (folder / name).relative_to(root).as_posix()
    try:
        return json.loads(git(root, 'show', revision + ':' + rel))
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError('historical contract unavailable: ' + rel) from exc


def parent(req, impact, row):
    source = row['source'].split(':')
    if source[0] == 'requirement':
        found = next((r for r in req['requirements'] if r['id'] == source[1]), None)
        return copy.deepcopy(found)
    if source[0] == 'impact':
        found = next((b for b in impact['behaviors'] if b['id'] == source[1]), None)
        if found is None:
            return None
        found = {k: value for k, value in found.items() if k != 'verification'}
        return {'behavior': found, 'requirements': [r for r in req['requirements']
                                                   if r['id'] in found.get('requirement_ids', [])]}
    return None


def source_identity(root, folder):
    import importlib.util
    spec = importlib.util.spec_from_file_location('carry_verify_inputs', Path(__file__).with_name('verify-inputs.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    inventory = module.collect(root.resolve(), folder.name)
    fatal = [issue for issue in inventory['issues_to_review']
             if issue in ('feature_source_index_missing_or_invalid', 'prd_intake_missing',
                          'prd_intake_source_index_invalid', 'source_indices_disagree',
                          'no_source_paths_identified', 'source_unavailable')]
    if fatal:
        raise ValueError('source inputs unavailable: ' + ', '.join(fatal))
    import hashlib
    evidence = []
    directory = folder / 'evidence'
    if directory.is_symlink():
        raise ValueError('unsafe evidence directory')
    if directory.exists():
        for path in sorted(directory.rglob('*')):
            if path.is_symlink():
                raise ValueError('unsafe evidence link')
            if path.is_file():
                evidence.append({'path': path.relative_to(folder).as_posix(),
                                 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    return {'sources': inventory['sources'], 'evidence_files': evidence,
            'source_status_claims': inventory['source_status_claims']}


def original_observation(row, previous):
    """Follow the validated contiguous retention chain, never skip a withdrawal."""
    index = row['history'].index(previous)
    revision = previous['tested_revision']
    while row['history'][index]['status'] == 'retained':
        if index == 0 or row['history'][index]['tested_revision'] != revision:
            raise ValueError('retention chain lacks the original tested observation')
        index -= 1
    origin = row['history'][index]
    if origin['status'] != 'passed' or origin['tested_revision'] != revision:
        raise ValueError('retention chain cannot bypass a withdrawal or changed tested identity')
    return origin



def input_snapshot(root, folder, item_id, contract_revision=None):
    from feature_lifecycle import require_active
    root = root.resolve()
    if folder.is_symlink():
        raise ValueError("unsafe feature directory")
    folder = folder.resolve()
    if not folder.is_relative_to(root):
        raise ValueError("feature directory outside project")
    doc = v.load_plan(folder)
    stamp, head = v.context(root, folder, doc)
    req, _, impact = v.sources(root, folder)
    require_active(req['feature'])
    row = next((r for r in doc['items'] if r['id'] == item_id), None)
    if row is None or row['mode'] != 'manual' or parent(req, impact, row) is None or not row['history']:
        raise ValueError('select an existing manual requirement/impact row')
    previous = row['history'][-1]
    if previous['status'] not in ('passed', 'retained'):
        raise ValueError('only the latest passed/retained result may be reviewed; do not revive withdrawn evidence')
    if v.state(row, stamp, v.manual_evidence_stamp(root, folder, row)) != 'stale':
        raise ValueError('only stale evidence needs carry review')
    observation = original_observation(row, previous)
    if contract_revision is None and previous['status'] == 'retained':
        # Reuse only a locator in an already validated receipt, never search for
        # a convenient green commit or reuse a prior relevance verdict.
        for entry in row['history'][row['history'].index(observation) + 1:]:
            binding = entry.get('carry_receipt', {}).get('contract_record')
            if binding is not None and binding.get('source_result_hash') == digest(observation):
                contract_revision = binding['revision']
                break
    base = previous['tested_revision']
    if git(root, 'rev-parse', base + '^{commit}').decode().strip() != base:
        raise ValueError('original tested_revision must be an available full commit')
    git(root, 'merge-base', '--is-ancestor', base, head)
    records_at = contract_revision or base
    if contract_revision is not None:
        if git(root, 'rev-parse', records_at + '^{commit}').decode().strip() != records_at:
            raise ValueError('contract_revision must be an available full commit')
        git(root, 'merge-base', '--is-ancestor', base, records_at)
        git(root, 'merge-base', '--is-ancestor', records_at, head)
        tested_tree = project_files(root, base)
        # Check the interval too: a changed-and-reverted implementation is not
        # a record-only history. Do not pick a convenient later green contract.
        interval = git(root, 'rev-list', '--ancestry-path', base + '..' + records_at).decode().splitlines()
        if any(project_files(root, rev) != tested_tree for rev in interval):
            raise ValueError('business tree changed before contract was recorded; obtain current evidence')
    old_req = historical(root, folder, records_at, 'spec/requirements.json')
    old_impact = historical(root, folder, records_at, 'impact.json')
    old_parent, new_parent = parent(old_req, old_impact, row), parent(req, impact, row)
    if old_parent is None or old_parent != new_parent:
        raise ValueError('full parent claim changed or is unavailable; obtain evidence for the current claim')
    old_plan = historical(root, folder, records_at, 'verification.json')
    old_row = next((r for r in old_plan['items'] if r['id'] == item_id), None)
    contract = lambda r: {k: value for k, value in r.items() if k != 'history'}
    if old_row is None or contract(old_row) != contract(row):
        raise ValueError('row contract changed or unavailable; obtain current evidence')
    if contract_revision is not None:
        if not old_row.get('history') or observation != old_row['history'][-1]:
            raise ValueError('recorded contract does not contain the exact original result')
        # Existing authority at the tested revision must not be replaced by a
        # later matching contract. Missing records need explicit review below.
        for name, later in [('spec/requirements.json', old_req), ('impact.json', old_impact)]:
            rel = (folder / name).relative_to(root).as_posix()
            exists = git(root, 'ls-tree', base, '--', rel)
            if exists:
                earlier = historical(root, folder, base, name)
                pair = (earlier, old_impact) if name.startswith('spec/') else (old_req, earlier)
                if parent(*pair, row) != new_parent:
                    raise ValueError('parent claim at tested revision differs from recorded contract')
    before, now = project_files(root, base), project_files(root)
    changed = sorted(p for p in before.keys() | now.keys() if before.get(p) != now.get(p))
    paths = ['spec/requirements.json', 'decisions.json', 'impact.json', 'spec/prd-intake.json', 'traceability.json']
    old_records = {p: historical(root, folder, records_at, p) for p in paths}
    current_records = {p: v.read(folder / p) for p in paths}
    # Bind ignored registered sources too. Missing authority must be investigated, not carried.
    source_inputs = source_identity(root, folder)

    payload = {'schema_version': 1, 'feature_id': folder.name, 'item_id': item_id,
               'reviewed_revision': head, 'current_digest': stamp,
               'source_result': previous, 'source_result_hash': digest(previous),
               'row_contract': {k: value for k, value in row.items() if k != 'history'},
               'parent_claim': new_parent, 'source_revision': base,
               'before_records': old_records, 'current_records': current_records,
               'changed_paths': changed, 'before_project_digest': digest(before), 'current_project_digest': digest(now),
               'changed_records': sorted(p for p in paths if old_records[p] != current_records[p]),
               'source_inputs': source_inputs}
    if contract_revision is not None or previous['status'] == 'retained':
        payload['original_observation'] = copy.deepcopy(observation)
    if contract_revision is not None:
        payload['contract_record'] = {'revision': records_at, 'tested_revision': base,
                                      'source_result_hash': digest(observation),
                                      'records_digest': digest(old_records),
                                      'row_contract_digest': digest(contract(old_row))}
    payload['input_digest'] = digest(payload)
    return payload


def validate_assessment(review, item_id, input_digest, changed_paths, changed_records):
    if not isinstance(input_digest, str) or len(input_digest) != 64 or not all(c in '0123456789abcdef' for c in input_digest):
        raise ValueError('invalid carry input digest')
    if not isinstance(changed_paths, list) or not isinstance(changed_records, list):
        raise ValueError('invalid carry change inventories')
    required = ('reviewer', 'method', 'claim_evidence', 'dependency_evidence',
                'contract_evidence', 'environment_evidence', 'counterexample')
    if not isinstance(review, dict) or review.get('input_digest') != input_digest or review.get('item_id') != item_id:
        raise ValueError('review does not match frozen inputs')
    if review.get('status') != 'supported' or review.get('independent_context') is not True:
        raise ValueError('fresh-context review must support the complete claim; partial/unknown requires targeted evidence')
    if any(not isinstance(review.get(k), str) or not review[k].strip() for k in required):
        raise ValueError('review requires actual claim/dependency/contract/environment evidence and counterexample')
    paths = review.get('dependencies')
    if not isinstance(paths, list) or not paths or not all(isinstance(p, str) for p in paths) or len(paths) != len(set(paths)):
        raise ValueError('review requires distinct investigated dependency files')
    for name in paths:
        path_name(name)
    for key, expected in [('changes', changed_paths), ('record_changes', changed_records)]:
        changes = review.get(key)
        if not isinstance(changes, list) or not all(isinstance(c, dict) for c in changes) or sorted(c.get('path', '') for c in changes) != expected:
            raise ValueError('review every changed ' + ('workflow record' if key == 'record_changes' else 'project path') + ' exactly once')
        if any(c.get('relationship') != 'unaffected' or not isinstance(c.get('evidence'), str) or not c['evidence'].strip() for c in changes):
            raise ValueError('affected/unknown contract or file change needs current targeted evidence')
    return paths


@v.plan_mutation
def apply(root, folder, snapshot, review):
    frozen = v.read(snapshot)
    records_at = frozen.get('contract_record', {}).get('revision')
    fresh = input_snapshot(root, folder, frozen['item_id'], records_at)
    if fresh != frozen:
        raise ValueError('carry inputs stale; preserve review and recapture')
    verdict = v.read(review)
    paths = validate_assessment(verdict, fresh['item_id'], fresh['input_digest'], fresh['changed_paths'], fresh['changed_records'])
    validate_origin(verdict, fresh['source_revision'], fresh['source_inputs'])
    if 'contract_record' in fresh:
        validate_contract_record(fresh['contract_record'], verdict, previous_hash=digest(fresh['original_observation']))
    before, now = project_files(root, fresh['source_revision']), project_files(root)
    for name in paths:
        path_name(name)
        if (name not in before or before[name] != now.get(name)
                or before[name]['kind'] != 'blob' or before[name]['mode'] == '120000'):
            raise ValueError('dependency changed or historical content unavailable: ' + name)
    doc = v.load_plan(folder)
    original_plan = copy.deepcopy(doc)
    row = next(r for r in doc['items'] if r['id'] == fresh['item_id'])
    previous = row['history'][-1]
    receipt = {'input_digest': fresh['input_digest'], 'source_result_hash': digest(previous),
               'review': verdict, 'current_project_digest': fresh['current_project_digest'],
               'parent_claim_digest': digest(fresh['parent_claim']), 'item_id': fresh['item_id'],
               'reviewed_revision': fresh['reviewed_revision'], 'source_inputs': fresh['source_inputs'],
               'changed_paths': fresh['changed_paths'], 'changed_records': fresh['changed_records']}
    receipt['original_observation_ref'] = observation_ref(row, original_observation(row, previous))
    if 'contract_record' in fresh:
        receipt['contract_record'] = fresh['contract_record']
    entry = v.result('retained', fresh['current_digest'], previous['tested_revision'],
                     REFERENCE_ACTUAL,
                     'Fresh-context relevance review at ' + fresh['reviewed_revision'] + ': ' + verdict['claim_evidence'],
                     'reviewed carry-forward; not re-executed')
    entry.update(retention_kind='reviewed_carry', reviewed_revision=fresh['reviewed_revision'],
                 source_result_digest=previous['digest'], changed_paths=fresh['changed_paths'],
                 reason=verdict['dependency_evidence'], carry_receipt=receipt,
                 carry_receipt_digest=digest(receipt))
    row['history'].append(entry)
    entry['evidence_digest'] = v.manual_evidence_stamp(root, folder, row)
    # Do not use a review completed against a moving project/plan.
    if (input_snapshot(root, folder, fresh['item_id'], records_at) if records_at else
            input_snapshot_from_previous(root, folder, fresh['item_id'])) != fresh:
        raise ValueError('inputs changed before save')
    if v.load_plan(folder) != original_plan:
        raise ValueError('verification plan/results changed during carry review; no results applied')
    v.save(folder / 'verification.json', doc)
    v.render(folder)
    return entry


def input_snapshot_from_previous(root, folder, item_id):
    # The appended entry is still only in memory; disk remains the frozen source.
    return input_snapshot(root, folder, item_id)


def validate_contract_record(binding, review, previous_hash):
    import re
    if (not isinstance(binding, dict) or binding.get('source_result_hash') != previous_hash
            or any(not isinstance(binding.get(k), str) or not re.fullmatch(r'[0-9a-f]{40,64}', binding[k])
                   for k in ('revision', 'tested_revision'))
            or any(not isinstance(binding.get(k), str) or not re.fullmatch(r'[0-9a-f]{64}', binding[k])
                   for k in ('records_digest', 'row_contract_digest'))):
        raise ValueError('invalid historical contract binding')
    assessment = review.get('contract_record')
    if (not isinstance(assessment, dict) or assessment.get('revision') != binding['revision']
            or assessment.get('tested_revision') != binding['tested_revision']
            or not isinstance(assessment.get('explanation'), str) or not assessment['explanation'].strip()):
        raise ValueError('review the recorded contract chronology and original observation explicitly')


def validate_origin(review, source_revision, source_inputs):
    origin = review.get('original_identity')
    if not isinstance(origin, dict) or origin.get('revision') != source_revision or origin.get('worktree_verified') is not True:
        raise ValueError('original observation needs proved code/worktree identity, not recorded HEAD alone')
    if not isinstance(origin.get('explanation'), str) or not origin['explanation'].strip():
        raise ValueError('original code/package binding explanation required')
    refs = origin.get('evidence_refs')
    available = {r['path'] for r in source_inputs.get('evidence_files', []) + source_inputs.get('sources', [])}
    if not isinstance(refs, list) or not refs or not all(isinstance(p, str) and p in available for p in refs):
        raise ValueError('cite accessible archived original identity evidence; unexplained dirty worktree requires retest')


def validate_receipt(entry, previous, item):
    receipt = entry.get('carry_receipt')
    if not isinstance(receipt, dict) or entry.get('carry_receipt_digest') != digest(receipt):
        raise ValueError('invalid carry receipt digest')
    if previous is None or previous['status'] not in ('passed', 'retained') or receipt.get('source_result_hash') != digest(previous):
        raise ValueError('carry receipt does not bind the original complete result')
    review = receipt.get('review', {})
    validate_assessment(review, item['id'], receipt.get('input_digest'), receipt.get('changed_paths'), receipt.get('changed_records'))
    validate_origin(review, previous['tested_revision'], receipt.get('source_inputs', {}))
    observation = previous
    if 'original_observation' in receipt:
        observation = original_observation(item, previous)
        if receipt['original_observation'] != observation:
            raise ValueError('carry receipt changed the original observation chain')
    if 'original_observation_ref' in receipt:
        observation = original_observation(item, previous)
        if receipt['original_observation_ref'] != observation_ref(item, observation):
            raise ValueError('carry receipt changed the original observation reference')
    if 'contract_record' in receipt:
        binding = receipt['contract_record']
        validate_contract_record(binding, review, digest(observation))
        if binding['tested_revision'] != previous['tested_revision']:
            raise ValueError('record binding changed original tested identity')
    if receipt.get('item_id') != item['id'] or entry.get('changed_paths') != receipt.get('changed_paths') or entry.get('reviewed_revision') != receipt.get('reviewed_revision'):
        raise ValueError('carry receipt does not match row/review identity')
    expected_actual = REFERENCE_ACTUAL if 'original_observation_ref' in receipt else 'Original observation retained; no new execution: ' + previous['actual']
    if entry.get('actual') != expected_actual or entry.get('method') != 'reviewed carry-forward; not re-executed':
        raise ValueError('carry changed original observation or execution claim')
    if review.get('status') != 'supported' or review.get('independent_context') is not True or review.get('input_digest') != receipt.get('input_digest'):
        raise ValueError('invalid carry review')
    if entry.get('tested_revision') != previous['tested_revision'] or entry.get('source_result_digest') != previous['digest']:
        raise ValueError('carry changed original tested identity')
    if not entry.get('reviewed_revision') or not receipt.get('current_project_digest'):
        raise ValueError('carry lacks current review identity')


@v.plan_mutation
def minimize_copies(root, folder, item_ids):
    """Replace only uncommitted helper copies, never original observations/prose."""
    doc = v.load_plan(folder)
    before = copy.deepcopy(doc)
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    committed = historical(root, folder, head, 'verification.json')
    if not item_ids or len(item_ids) != len(set(item_ids)):
        raise ValueError('select distinct carry rows')
    changed = 0
    for item_id in item_ids:
        row = next((r for r in doc['items'] if r['id'] == item_id), None)
        old = next((r for r in committed['items'] if r['id'] == item_id), None)
        if row is None or old is None or row['history'][:len(old['history'])] != old['history']:
            raise ValueError('committed history must remain unchanged')
        old_history = copy.deepcopy(row['history'])
        for index in range(len(old['history']), len(row['history'])):
            entry = row['history'][index]
            if entry.get('retention_kind') == 'annotation_amend':
                raise ValueError('annotation-bound history needs separate review; no copies changed')
            if entry.get('retention_kind') != 'reviewed_carry':
                continue
            previous = row['history'][index - 1]
            receipt = entry['carry_receipt']
            if ('original_observation' not in receipt and entry['actual'] == REFERENCE_ACTUAL
                    and receipt['source_result_hash'] == digest(previous)):
                continue
            old_result_hash = digest(old_history[index])
            old_receipt_hash = old_history[index]['carry_receipt_digest']
            origin = original_observation(row, previous)
            # Rebind an immediate predecessor only after validating the complete
            # old plan. All review prose and all observation facts stay identical.
            receipt['source_result_hash'] = digest(previous)
            receipt.pop('original_observation', None)
            receipt['original_observation_ref'] = observation_ref(row, origin)
            entry['actual'] = REFERENCE_ACTUAL
            receipt['copy_minimization'] = {'previous_result_hash': old_result_hash,
                                             'previous_receipt_digest': old_receipt_hash,
                                             'reason': 'Remove redundant helper copies; original observation unchanged'}
            entry['carry_receipt_digest'] = digest(receipt)
            if entry != old_history[index]:
                changed += 1
    if not changed:
        raise ValueError('no uncommitted helper copies to minimize')
    # Existing other receipt families/shared reviews may bind a changed result.
    # Validate the complete candidate before saving; never recalculate those binds.
    import tempfile
    with tempfile.TemporaryDirectory() as temp:
        candidate = Path(temp) / folder.name
        candidate.mkdir()
        v.save(candidate / 'verification.json', doc)
        v.load_plan(candidate)
    if v.load_plan(folder) != before or git(root, 'rev-parse', 'HEAD').decode().strip() != head:
        raise ValueError('plan or HEAD changed before save')
    v.save(folder / 'verification.json', doc)
    v.render(folder)
    return changed


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['capture', 'apply', 'minimize-copies'])
    p.add_argument('root', type=Path)
    p.add_argument('feature_id')
    p.add_argument('--item', action='append')
    p.add_argument('--snapshot', type=Path)
    p.add_argument('--contract-revision', help='Explicit full commit storing the original contract/result; capture only')
    p.add_argument('--review', type=Path)
    args = p.parse_args()
    if not re_feature(args.feature_id):
        p.error('invalid feature ID')
    root = args.root.resolve()
    folder = root / '.agent-workflow/features' / args.feature_id
    try:
        if args.action != 'capture' and args.contract_revision:
            p.error('--contract-revision is capture-only; apply uses the frozen binding')
        if args.action == 'capture':
            if not args.item:
                p.error('capture requires --item')
            if len(args.item) != 1: p.error('capture requires one --item')
            print(json.dumps(input_snapshot(root, folder, args.item[0], args.contract_revision), ensure_ascii=False, indent=2))
        elif args.action == 'minimize-copies':
            count = minimize_copies(root, folder, args.item)
            print('EVIDENCE_COPIES_MINIMIZED: %d; no new execution; refresh affected review/delivery bindings' % count)
        else:
            if not args.snapshot or not args.review:
                p.error('apply requires --snapshot and --review')
            apply(root, folder, args.snapshot, args.review)
            print('EVIDENCE_CARRIED: original tested revision retained; not re-executed')
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print('EVIDENCE_CARRY_ERROR: ' + str(exc), file=sys.stderr)
        return 1


def re_feature(value):
    import re
    return re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', value) and value not in ('.', '..')



if __name__ == '__main__':
    sys.exit(main())
