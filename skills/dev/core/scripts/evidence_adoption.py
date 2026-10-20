#!/usr/bin/env python3
"""Review adoption of original observations after an approved interpretation correction.

This is not execution, ordinary carry, or a way to waive an observed failure.
Snapshots may include uncommitted workflow records; business code must be clean.
"""
from acceptance_contract import refuse_legacy

import argparse
import copy
from datetime import datetime, timezone
from pathlib import Path
import sys

from impact import digest, git
import verification as v
from evidence_carry import parent, project_files, source_identity
from result_corrections import handoff


def text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('nonempty adoption rationale required')


def contract(row):
    return {k: val for k, val in row.items() if k not in ('history', 'retention', 'manual_scope_ref')}


def locate(doc, ref):
    if not isinstance(ref, dict) or set(ref) != {'collection', 'item_id', 'history_index'}:
        raise ValueError('explicit source collection, row and history index required')
    if ref['collection'] not in ('items', 'retired'):
        raise ValueError('invalid source collection')
    rows = [r for r in doc[ref['collection']] if r.get('id') == ref['item_id']]
    index = ref['history_index']
    if (len(rows) != 1 or rows[0].get('mode') != 'manual' or not isinstance(index, int)
            or isinstance(index, bool) or index < 0 or index != len(rows[0]['history']) - 1):
        raise ValueError('select unique latest original manual observation; do not skip a later withdrawal')
    result = rows[0]['history'][index]
    if result.get('status') not in ('passed', 'unavailable') or 'retention_kind' in result:
        raise ValueError('failed, waived or derived results are not original observations')
    for field in ('actual', 'evidence', 'at', 'tested_revision', 'method'):
        text(result.get(field))
    return rows[0], result


def files(root, folder, refs):
    if not isinstance(refs, list) or not refs or len(set(refs)) != len(refs):
        raise ValueError('distinct durable evidence paths required')
    prefix = '.agent-workflow/features/' + folder.name + '/'
    states = {}
    for name in refs:
        name = handoff.relative(name)
        if not name.startswith((prefix + 'evidence/', prefix + 'sources/')):
            raise ValueError('adoption support must be archived in feature evidence/sources')
        state = handoff.file_state(root, name)
        if state['state'] != 'file':
            raise ValueError('missing or unsafe adoption support')
        states[name] = state
    return states


def capture(root, folder, requests):
    root = root.resolve()
    if folder.is_symlink() or not folder.resolve().is_relative_to(root):
        raise ValueError('unsafe feature directory')
    folder = folder.resolve()
    doc = v.load_plan(folder); refuse_legacy(doc)
    stamp, head = v.context(root, folder, doc)
    from feature_lifecycle import require_active
    req = v.read(folder / 'spec/requirements.json')
    require_active(req['feature'])
    impact = v.read(folder / 'impact.json')
    decisions = v.read(folder / 'decisions.json')['decisions']
    current_project = project_files(root)
    if not isinstance(requests, list) or not requests:
        raise ValueError('explicit adoption requests required')
    selected = []
    for request in requests:
        if not isinstance(request, dict) or set(request) != {'item_id', 'source', 'contract_ref', 'decision_id', 'evidence_refs'}:
            raise ValueError('invalid adoption request fields')
        targets = [r for r in doc['items'] if r['id'] == request['item_id'] and r['mode'] == 'manual']
        if len(targets) != 1:
            raise ValueError('select a current manual target')
        row = targets[0]
        if row['history'] and row['history'][-1]['status'] in ('failed', 'waived', 'unavailable'):
            raise ValueError('target withdrawal/failure needs ordinary Verify, not adoption')
        if v.state(row, stamp, v.manual_evidence_stamp(root, folder, row)) not in ('not_run', 'stale'):
            raise ValueError('target must be unrun or stale')
        source_row, observation = locate(doc, request['source'])
        if source_row['source'] != row['source']:
            raise ValueError('source must be the same requirement/impact slot, not another claim')
        chosen = [d for d in decisions if d.get('id') == request['decision_id']]
        if len(chosen) != 1 or chosen[0].get('status') != 'approved':
            raise ValueError('approved interpretation decision required')
        text(chosen[0].get('approval_ref'))
        contract_ref = handoff.relative(request['contract_ref'])
        scratch_prefix = '.agent-workflow/scratch/' + folder.name + '/'
        if contract_ref.startswith(scratch_prefix):
            import subprocess
            if subprocess.run(['git', '-C', str(root), 'check-ignore', '-q', '--', contract_ref], check=False).returncode:
                raise ValueError('temporary recovered contract must be ignored')
            contract_state = handoff.file_state(root, contract_ref)
            if contract_state['state'] != 'file':
                raise ValueError('missing or unsafe recovered contract input')
            # The recovered contract is archived in the immutable review event.
            # Its provenance must already be durable; adding evidence files here
            # would unnecessarily stale unrelated existing carry receipts.
            support = files(root, folder, request['evidence_refs'])
        else:
            support = files(root, folder, [contract_ref] + request['evidence_refs'])
            contract_state = support[contract_ref]
        archived = v.read(root / contract_ref)
        # The archive is a provenance claim, NOT proof of its historical date.
        # Review must verify its origin against independent archived records.
        expected = {'feature_id': folder.name, 'row_contract': contract(source_row),
                    'result_hash': digest(observation), 'tested_revision': observation['tested_revision'],
                    'observed_at': observation['at']}
        if any(archived.get(k) != val for k, val in expected.items()) or not isinstance(archived.get('parent_claim'), dict):
            raise ValueError('archived source contract/observation identity mismatch')
        old_parent = archived['parent_claim']
        if source_row['source'].startswith('requirement:'):
            parts = source_row['source'].split(':')
            criteria = old_parent.get('acceptance_criteria', [])
            index = int(parts[2]) - 1
            if (old_parent.get('id') != parts[1] or not isinstance(criteria, list)
                    or index < 0 or index >= len(criteria) or criteria[index] != source_row['expected']):
                raise ValueError('archived parent does not contain the original acceptance contract')
        elif (old_parent.get('behavior', {}).get('id') != source_row['source'].split(':')[1]
              or old_parent['behavior'].get('statement') != source_row['expected']
              or not isinstance(old_parent.get('requirements'), list)):
            raise ValueError('archived parent does not contain the original behavior contract')
        provenance = archived.get('provenance_refs')
        if not isinstance(provenance, list) or not provenance or not set(provenance) <= set(request['evidence_refs']):
            raise ValueError('contract chronology requires archived provenance refs')
        source_revision = git(root, 'rev-parse', '--verify', '--end-of-options', observation['tested_revision'] + '^{commit}').decode().strip()
        if source_revision != observation['tested_revision']:
            raise ValueError('original tested revision must be a full commit identity')
        git(root, 'merge-base', '--is-ancestor', source_revision, 'HEAD')
        before = project_files(root, source_revision)
        changed = sorted(p for p in before.keys() | current_project.keys() if before.get(p) != current_project.get(p))
        selected.append({'item_id': row['id'], 'source': request['source'],
                         'source_result_hash': digest(observation), 'source_contract': archived,
                         'source_history_digest': digest(source_row['history']),
                         'contract_input': {'path': contract_ref, **contract_state},
                         'target_contract': contract(row), 'parent_claim': parent(req, impact, row),
                         'decision': chosen[0], 'support_files': support,
                         'changed_paths': changed, 'before_project_digest': digest(before)})
    if len({r['item_id'] for r in selected}) != len(selected):
        raise ValueError('duplicate adoption target')
    refs = sorted({p for row in selected for p in row['support_files']} | {row['contract_input']['path'] for row in selected})
    frozen = {'schema_version': 1, 'kind': 'interpretation_evidence_adoption', 'feature_id': folder.name,
              'request': requests, 'rows': selected, 'reviewed_revision': head,
              'current_digest': stamp, 'project_digest': digest(current_project),
              'source_inputs': source_identity(root, folder), 'plan_hash': digest(doc),
              'binding': handoff.capture(root, folder.name, head, refs)}
    frozen['input_digest'] = digest(frozen)
    return frozen


def validate_review(review, frozen):
    if (not isinstance(review, dict) or review.get('input_digest') != frozen['input_digest']
            or review.get('independent_context') is not True or review.get('status') != 'supported'):
        raise ValueError('fresh-context supported adoption review required; partial/unknown rejected')
    text(review.get('reviewer'))
    verdicts = review.get('rows')
    if (not isinstance(verdicts, list) or len(verdicts) != len(frozen['rows'])
            or sorted(r.get('item_id', '') for r in verdicts) != sorted(r['item_id'] for r in frozen['rows'])):
        raise ValueError('review every adoption target exactly once')
    for row in frozen['rows']:
        verdict = next(r for r in verdicts if r['item_id'] == row['item_id'])
        if (verdict.get('status') != 'supported' or verdict.get('change_kind') != 'interpretation_correction'
                or verdict.get('coverage_expanded') is not False or verdict.get('contradictions') != []):
            raise ValueError('changed behavior, expanded claim, conflicts or partial support require new evidence')
        for key in ('claim_evidence', 'contract_provenance', 'decision_scope', 'source_status_explanation',
                    'history_review', 'environment_evidence', 'counterexample'):
            text(verdict.get(key))
        identity = verdict.get('original_identity', {})
        if (identity.get('revision') != row['source_contract']['tested_revision']
                or identity.get('worktree_verified') is not True):
            raise ValueError('original tested tree identity must be verified')
        text(identity.get('explanation'))
        identity_refs = identity.get('evidence_refs')
        if not isinstance(identity_refs, list) or not identity_refs or not set(identity_refs) <= row['support_files'].keys():
            raise ValueError('original identity requires archived supporting paths')
        changes = verdict.get('changes')
        if (not isinstance(changes, list) or sorted(c.get('path', '') for c in changes) != row['changed_paths']
                or any(c.get('relationship') != 'unaffected' for c in changes)):
            raise ValueError('review every business change; affected/unknown rejected')
        for change in changes: text(change.get('evidence'))
        dependencies = verdict.get('dependencies')
        if not isinstance(dependencies, list) or not dependencies or len(set(dependencies)) != len(dependencies):
            raise ValueError('investigated dependency paths required')
        for path in dependencies: handoff.relative(path)


def validate_receipt(doc, row, entry):
    ref = entry.get('adoption_receipt')
    receipts = [e for e in doc.get('adoption_reviews', []) if e.get('digest') == ref]
    if len(receipts) != 1:
        raise ValueError('adoption review reference missing or ambiguous')
    receipt = receipts[0]
    if (entry.get('status') != 'retained' or row.get('mode') != 'manual'
            or doc.get('schema_version') not in (3, 4, 5)
            or receipt.get('digest') != digest({k: val for k, val in receipt.items() if k != 'digest'})):
        raise ValueError('invalid adoption receipt/schema/digest')
    frozen = receipt.get('inputs', {})
    if frozen.get('input_digest') != digest({k: val for k, val in frozen.items() if k != 'input_digest'}):
        raise ValueError('adoption frozen input changed')
    validate_review(receipt.get('review'), frozen)
    selected = [r for r in frozen['rows'] if r['item_id'] == row['id']]
    if len(selected) != 1 or frozen['feature_id'] != doc['feature_id']:
        raise ValueError('adoption target mismatch')
    selected = selected[0]
    # Resolve across retirement moves without duplicating private observations.
    ref = selected['source']
    matches = [r for r in doc['items'] + doc['retired'] if r.get('id') == ref['item_id']
               and len(r.get('history', [])) > ref['history_index']
               and digest(r['history'][ref['history_index']]) == selected['source_result_hash']]
    if len(matches) != 1:
        raise ValueError('adoption original observation missing or changed')
    source_row = matches[0]
    origin = source_row['history'][ref['history_index']]
    if (digest(source_row['history'][:ref['history_index'] + 1]) != selected['source_history_digest']
            or origin['status'] not in ('passed', 'unavailable') or 'retention_kind' in origin
            or entry['tested_revision'] != origin['tested_revision']
            or entry.get('observed_at') != origin['at']
            or entry.get('adoption_source') != selected['source']
            or entry.get('reviewed_revision') != frozen['reviewed_revision']):
        raise ValueError('adoption original history or execution identity changed')


def links(doc, row):
    out = []
    for entry in row['history']:
        if entry.get('retention_kind') != 'interpretation_adoption':
            continue
        event = next(e for e in doc['adoption_reviews'] if e['digest'] == entry['adoption_receipt'])
        selected = next(r for r in event['inputs']['rows'] if r['item_id'] == row['id'])
        out.append({'receipt': entry['adoption_receipt'], 'source': selected['source'],
                    'source_result_hash': selected['source_result_hash'],
                    'original_tested_revision': entry['tested_revision'], 'observed_at': entry['observed_at'],
                    'adopted_at': entry['at'], 'reviewed_revision': entry['reviewed_revision'],
                    'contract': selected['source_contract'], 'support_files': selected['support_files'],
                    'review': next(r for r in event['review']['rows'] if r['item_id'] == row['id']),
                    'boundary': 'Applicability review of original observation; not a new execution.'})
    return out


def validate_events(doc):
    events = doc.get('adoption_reviews')
    if not isinstance(events, list) or not events or len({e.get('digest') for e in events}) != len(events):
        raise ValueError('schema 3 requires unique adoption review events')
    for event in events:
        if event.get('digest') != digest({k: val for k, val in event.items() if k != 'digest'}):
            raise ValueError('adoption review digest changed')
        for selected in event['inputs']['rows']:
            matches = [(row, entry) for row in doc['items'] + doc['retired']
                       if row['id'] == selected['item_id'] for entry in row['history']
                       if entry.get('adoption_receipt') == event['digest']]
            if len(matches) != 1:
                raise ValueError('adoption review target missing or duplicated')
            validate_receipt(doc, *matches[0])


@v.plan_mutation
def apply(root, folder, snapshot, review_path):
    frozen = v.read(snapshot)
    fresh = capture(root, folder, frozen['request'])
    if fresh != frozen:
        raise ValueError('adoption inputs stale; preserve review and recapture')
    review = v.read(review_path)
    validate_review(review, fresh)
    current_project = project_files(root)
    for selected in fresh['rows']:
        before = project_files(root, selected['source_contract']['tested_revision'])
        verdict = next(r for r in review['rows'] if r['item_id'] == selected['item_id'])
        for name in verdict['dependencies']:
            if (name not in before or before[name] != current_project.get(name)
                    or before[name]['kind'] != 'blob' or before[name]['mode'] == '120000'):
                raise ValueError('adoption dependency changed or unavailable; obtain new evidence')
    doc = v.load_plan(folder); refuse_legacy(doc)
    original = copy.deepcopy(doc)
    doc['schema_version'] = max(3, doc['schema_version'])  # Older readers must fail closed.
    receipt = {'inputs': fresh, 'review': review}
    # Do not embed the whole project snapshot or original observation prose.
    # Binding is hashed; semantic input and per-file provenance remain inspectable.
    receipt['digest'] = digest(receipt)
    doc.setdefault('adoption_reviews', []).append(receipt)
    now = datetime.now(timezone.utc).isoformat()
    for selected in fresh['rows']:
        row = next(r for r in doc['items'] if r['id'] == selected['item_id'])
        source_row, observation = locate(original, selected['source'])
        entry = v.result('retained', fresh['current_digest'], observation['tested_revision'],
                         'Original observation adopted for the corrected interpretation; no new execution.',
                         'See adoption receipt and archived evidence; original observation retained by reference.',
                         'independent interpretation adoption')
        entry.update(retention_kind='interpretation_adoption', observed_at=observation['at'], at=now,
                     reviewed_revision=fresh['reviewed_revision'], adoption_receipt=receipt['digest'],
                     adoption_source=selected['source'],
                     changed_paths=selected['changed_paths'], reason='Approved interpretation correction; independently reviewed original observation.')
        row.pop('manual_scope_ref', None)
        row['history'].append(entry)
        entry['evidence_digest'] = v.manual_evidence_stamp(root, folder, row)
        validate_receipt(doc, row, entry)
    if capture(root, folder, fresh['request']) != fresh or v.load_plan(folder) != original:
        raise ValueError('adoption inputs changed before save')
    v.save(folder / 'verification.json', doc)
    v.render(folder)
    return {'adopted': [r['item_id'] for r in fresh['rows']], 'new_execution': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['capture', 'apply'])
    parser.add_argument('root', type=Path); parser.add_argument('feature_id')
    parser.add_argument('--requests', type=Path); parser.add_argument('--snapshot', type=Path)
    parser.add_argument('--review', type=Path); parser.add_argument('--output', type=Path)
    args = parser.parse_args(); root = args.root.resolve()
    if not __import__('re').fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.feature_id):
        raise ValueError('invalid feature ID')
    folder = root / '.agent-workflow/features' / args.feature_id
    if args.action == 'capture':
        if not args.requests or not args.output: parser.error('capture requires --requests and --output')
        scratch = root / '.agent-workflow/scratch'
        if (scratch.is_symlink() or (root / '.agent-workflow').is_symlink() or args.output.is_symlink()
                or not args.output.resolve().is_relative_to(scratch.resolve())
                or handoff.file_state(root, args.output.resolve().relative_to(root).as_posix())['state'] == 'unavailable'):
            raise ValueError('snapshot output must be under ignored scratch')
        frozen = capture(root, folder, v.read(args.requests))
        args.output.parent.mkdir(parents=True, exist_ok=True); v.save(args.output, frozen)
        print('ADOPTION_CAPTURED ' + frozen['input_digest'])
    else:
        if not args.snapshot or not args.review: parser.error('apply requires --snapshot and --review')
        import json
        print(json.dumps(apply(root, folder, args.snapshot, args.review)))


if __name__ == '__main__':
    try: main()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print('EVIDENCE_ADOPTION_ERROR: ' + str(exc), file=sys.stderr); sys.exit(2)
