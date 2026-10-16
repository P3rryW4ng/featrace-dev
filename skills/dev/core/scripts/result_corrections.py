#!/usr/bin/env python3
"""Append reviewed descriptive corrections; never rewrite or re-sign observations."""
import argparse
import copy
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import re
import sys

from impact import digest, git
import verification as v

_spec = importlib.util.spec_from_file_location('correction_handoff', Path(__file__).with_name('verify-handoff.py'))
handoff = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(handoff)
FIELDS = {'actual', 'evidence'}
BOUNDARY = 'Descriptive correction only; original result, tested identity and acceptance state unchanged; not a new execution or applicability review.'


def key(c):
    return (c['item_id'], c['history_index'], c['field'])


def require_text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('nonempty correction text required')


def validate_review(review, frozen):
    if (not isinstance(review, dict) or review.get('input_digest') != frozen['input_digest']
            or review.get('status') != 'supported' or review.get('independent_context') is not True):
        raise ValueError('current fresh-context correction review required; partial/unknown cannot be applied')
    if not re.fullmatch(r'[0-9a-f]{64}', str(frozen.get('input_digest', ''))):
        raise ValueError('invalid correction input digest')
    for name in ('reviewer', 'scope_evidence', 'coverage_unchanged', 'identity_unchanged', 'counterexample'):
        require_text(review.get(name))
    rows = review.get('corrections')
    expected = [key(c) for c in frozen['corrections']]
    if (not isinstance(rows, list) or len(rows) != len(expected)
            or sorted(key(c) for c in rows) != sorted(expected)):
        raise ValueError('review every exact correction once')
    for c in rows:
        if c.get('status') != 'metadata_only':
            raise ValueError('coverage changes need ordinary Verify, not descriptive correction')
        require_text(c.get('evidence'))


def validate_events(doc):
    events = doc.get('result_correction_reviews', [])
    if not isinstance(events, list):
        raise ValueError('invalid result correction history')
    previous = {}
    all_rows = doc['items'] + doc['retired']
    event_ids = set()
    for event in events:
        if (not isinstance(event, dict) or event.get('id') != digest({k: val for k, val in event.items() if k != 'id'})
                or event['id'] in event_ids or event.get('feature_id') != doc['feature_id']):
            raise ValueError('result correction event changed or duplicated')
        event_ids.add(event['id'])
        require_text(event.get('at'))
        if not re.fullmatch(r'[0-9a-f]{40,64}', str(event.get('reviewed_revision', ''))):
            raise ValueError('invalid correction review revision')
        changes = event.get('corrections')
        if not isinstance(changes, list) or not changes:
            raise ValueError('empty correction event')
        if len({key(c) for c in changes}) != len(changes):
            raise ValueError('duplicate correction target')
        validate_review(event.get('review'), event)
        for c in changes:
            index = c.get('history_index')
            if (not isinstance(index, int) or isinstance(index, bool) or index < 0 or c.get('field') not in FIELDS):
                raise ValueError('only recorded actual/evidence fields may be corrected')
            matches = [r for r in all_rows if r.get('id') == c.get('item_id') and r.get('mode') == 'manual'
                       and index < len(r.get('history', [])) and digest(r['history'][index]) == c.get('original_result_hash')]
            if not matches:
                raise ValueError('original corrected result missing or changed')
            origin = matches[0]['history'][index]
            if origin.get('status') not in ('passed', 'retained') or origin.get('tested_revision') != c.get('tested_revision'):
                raise ValueError('correction changed original tested identity or result kind')
            target = key(c)
            prior_id, prior_text = previous.get(target, (None, origin[c['field']]))
            if (c.get('previous_correction_id') != prior_id or c.get('before_hash') != digest(prior_text)
                    or c.get('original_field_hash') != digest(origin[c['field']])):
                raise ValueError('correction sequence/source changed')
            require_text(c.get('replacement')); require_text(c.get('reason'))
            if c['replacement'] == prior_text:
                raise ValueError('correction must change descriptive text')
            files = c.get('support_files')
            if (not isinstance(files, dict) or not files
                    or any(not isinstance(state, dict) or state.get('state') != 'file'
                           or not re.fullmatch(r'[0-9a-f]{64}', str(state.get('sha256', ''))) for state in files.values())):
                raise ValueError('correction needs bound supporting files')
            for path in files:
                handoff.relative(path)
                allowed = ('.agent-workflow/features/' + doc['feature_id'] + '/evidence/',
                           '.agent-workflow/features/' + doc['feature_id'] + '/sources/')
                if path.startswith('.agent-workflow/') and not path.startswith(allowed):
                    raise ValueError('non-durable correction support path')
            previous[target] = (event['id'], c['replacement'])
    return events


def links(root, doc, row):
    """Exact result links, never implicit replacements or acceptance overrides."""
    out = []
    latest = {key(c): e['id'] for e in doc.get('result_correction_reviews', []) for c in e['corrections']}
    for event in doc.get('result_correction_reviews', []):
        for c in event['corrections']:
            if c['item_id'] != row['id']:
                continue
            index = c['history_index']
            if index >= len(row['history']) or digest(row['history'][index]) != c['original_result_hash']:
                continue
            states = {p: handoff.file_state(root, p) for p in c['support_files']}
            out.append({'correction_id': event['id'], 'history_index': index, 'field': c['field'],
                        'original_result_hash': c['original_result_hash'], 'tested_revision': c['tested_revision'],
                        'replacement': c['replacement'], 'reason': c['reason'],
                        'correction_state': 'current_note' if latest[key(c)] == event['id'] else 'superseded_note',
                        'support_files': c['support_files'], 'support_current': states == c['support_files'],
                        'support_now': states, 'previous_correction_id': c['previous_correction_id'],
                        'target': 'latest_record' if index == len(row['history']) - 1 else 'historical_record',
                        'reviewed_revision': event['reviewed_revision'], 'boundary': BOUNDARY})
    return out


def capture(root, folder, changes):
    root = root.resolve()
    if folder.is_symlink() or not folder.resolve().is_relative_to(root):
        raise ValueError('unsafe feature directory')
    folder = folder.resolve()
    if handoff.file_state(root, '.agent-workflow/features/' + folder.name + '/spec/requirements.json')['state'] != 'file':
        raise ValueError('unsafe or missing feature authority')
    from feature_lifecycle import require_active
    require_active(v.read(folder / 'spec/requirements.json')['feature'])
    doc = v.load_plan(folder)
    if not isinstance(changes, list) or not changes:
        raise ValueError('select explicit descriptive corrections')
    selected = []
    for c in changes:
        if not isinstance(c, dict) or set(c) != {'item_id', 'history_index', 'field', 'replacement', 'reason', 'support_refs'}:
            raise ValueError('invalid correction request fields')
        index = c['history_index']
        row = next((r for r in doc['items'] if r['id'] == c['item_id']), None)
        if (row is None or row['mode'] != 'manual' or not isinstance(index, int) or isinstance(index, bool)
                or index < 0 or index >= len(row['history']) or c['field'] not in FIELDS):
            raise ValueError('select a manual recorded actual/evidence field')
        origin = row['history'][index]
        if origin['status'] not in ('passed', 'retained'):
            raise ValueError('only recorded passed/retained descriptions; no withdrawal/waiver changes')
        for field in ('replacement', 'reason'): require_text(c[field])
        refs = c['support_refs']
        if not isinstance(refs, list) or not refs or any(not isinstance(p, str) for p in refs) or len(set(refs)) != len(refs):
            raise ValueError('explicit distinct supporting paths required')
        refs = [handoff.relative(p) for p in refs]
        allowed = ('.agent-workflow/features/' + folder.name + '/evidence/',
                   '.agent-workflow/features/' + folder.name + '/sources/')
        if any(p.startswith('.agent-workflow/') and not p.startswith(allowed) for p in refs):
            raise ValueError('support refs must be durable evidence/sources or project code, not scratch/derived records')
        files = {handoff.relative(p): handoff.file_state(root, p) for p in refs}
        if any(s['state'] != 'file' for s in files.values()):
            raise ValueError('supporting evidence missing or unsafe')
        prior_id, before = None, origin[c['field']]
        for event in doc.get('result_correction_reviews', []):
            for note in event['corrections']:
                if key(note) == key(c): prior_id, before = event['id'], note['replacement']
        if c['replacement'] == before: raise ValueError('no descriptive change')
        selected.append({'item_id': c['item_id'], 'history_index': index, 'field': c['field'],
                         'original_result_hash': digest(origin), 'original_field_hash': digest(origin[c['field']]),
                         'tested_revision': origin['tested_revision'], 'previous_correction_id': prior_id,
                         'before_hash': digest(before), 'replacement': c['replacement'], 'reason': c['reason'],
                         'support_files': files})
    if len({key(c) for c in selected}) != len(selected): raise ValueError('duplicate correction target')
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    refs = sorted({p for c in selected for p in c['support_files']})
    binding = handoff.capture(root, folder.name, head, refs)
    frozen = {'schema_version': 1, 'kind': 'result_description_correction', 'feature_id': folder.name,
              'reviewed_revision': head, 'corrections': selected, 'request': changes,
              'project_binding': binding, 'plan_hash': digest(doc)}
    frozen['input_digest'] = digest(frozen)
    return frozen


@v.plan_mutation
def apply(root, folder, snapshot, review_path):
    frozen = v.read(snapshot)
    fresh = capture(root, folder, frozen['request'])
    if fresh != frozen: raise ValueError('correction inputs stale; do not relabel the old review')
    review = v.read(review_path)
    validate_review(review, fresh)
    doc = v.load_plan(folder)
    original = copy.deepcopy(doc)
    body = {'at': datetime.now(timezone.utc).isoformat(), 'feature_id': folder.name,
            'reviewed_revision': fresh['reviewed_revision'], 'input_digest': fresh['input_digest'],
            'corrections': fresh['corrections'], 'review': review}
    body['id'] = digest(body)
    doc.setdefault('result_correction_reviews', []).append(body)
    doc['schema_version'] = max(2, doc['schema_version'])  # Never downgrade adoption-aware records.
    validate_events(doc)
    if capture(root, folder, fresh['request']) != fresh or v.load_plan(folder) != original:
        raise ValueError('correction inputs changed before save')
    v.save(folder / 'verification.json', doc)
    v.render(folder)
    return body


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['capture', 'apply']); p.add_argument('root', type=Path); p.add_argument('feature_id')
    p.add_argument('--changes', type=Path); p.add_argument('--snapshot', type=Path); p.add_argument('--review', type=Path)
    a = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', a.feature_id): p.error('invalid feature ID')
    root = a.root.resolve(); folder = root / '.agent-workflow/features' / a.feature_id
    try:
        if a.action == 'capture':
            if not a.changes: p.error('capture requires --changes')
            import json
            print(json.dumps(capture(root, folder, v.read(a.changes)), ensure_ascii=False, indent=2))
        else:
            if not a.snapshot or not a.review: p.error('apply requires --snapshot --review')
            apply(root, folder, a.snapshot, a.review)
            print('RESULT_DESCRIPTION_CORRECTED: history and freshness unchanged; no new execution')
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print('RESULT_CORRECTION_ERROR: ' + str(exc), file=sys.stderr); return 1


if __name__ == '__main__': sys.exit(main())
