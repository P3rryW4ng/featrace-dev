#!/usr/bin/env python3
"""Review a bounded index/annotation correction without pretending to rerun evidence."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

from impact import digest, path_name
import verification as v
from evidence_carry import project_files, source_identity


def text_at(folder, name):
    path_name(name)
    if not name.startswith('evidence/'):
        raise ValueError('metadata correction must stay in feature evidence directory')
    path = folder / name
    if path.is_symlink() or not path.resolve().is_relative_to(folder.resolve()):
        raise ValueError('unsafe annotation path')
    if not path.exists():
        return None
    text = path.read_bytes().decode('utf-8')
    # A command/output transcript is not metadata merely because it is text.
    if re.search(r'(?m)^(CMD:|OUT:)', text):
        raise ValueError('raw command/output transcript cannot be reclassified as an index; annotate it separately')
    return text


def scratch_path_name(name):
    if not isinstance(name, str) or not name.startswith('.agent-workflow/scratch/'):
        raise ValueError('archive original must stay in project-local ignored scratch')
    path_name(name[len('.agent-workflow/scratch/'):])


def archive_identity(root, additions):
    """Freeze local backed-up originals without emitting their raw contents."""
    if not isinstance(additions, list):
        raise ValueError('archive additions must be an explicit list')
    records = []
    for entry in additions:
        if not isinstance(entry, dict):
            raise ValueError('invalid archive addition')
        name, origin = entry.get('path'), entry.get('origin_path')
        path_name(name); scratch_path_name(origin)
        if not name.startswith('evidence/') or not origin.startswith('.agent-workflow/scratch/'):
            raise ValueError('archive destination must be evidence/ and original must be authorized ignored scratch')
        if entry.get('transformation') not in ('verbatim', 'redacted_extract') or not isinstance(entry.get('purpose'), str) or not entry['purpose'].strip():
            raise ValueError('archive addition requires transformation and purpose')
        scratch = root / '.agent-workflow/scratch'
        if scratch.is_symlink() or not scratch.resolve().is_relative_to(root.resolve()):
            raise ValueError('unsafe archive scratch root')
        source = root / origin
        if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to((root / '.agent-workflow/scratch').resolve()):
            raise ValueError('archive original missing or unsafe')
        # Follow the same project-local scratch rule; do not accept tracked/private arbitrary inputs.
        try:
            if not v.git(root, 'check-ignore', '--', origin).decode().strip():
                raise ValueError('archive original must be Git ignored')
        except Exception as exc:
            raise ValueError('archive original must be Git ignored') from exc
        records.append(dict(entry, origin_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), origin_size=source.stat().st_size))
    names = [r['path'] for r in records]
    if len(names) != len(set(names)):
        raise ValueError('duplicate archive destination')
    return records


def archived_file(folder, name):
    path_name(name)
    target = folder / name
    if not name.startswith('evidence/') or target.is_symlink() or not target.is_file() or not target.resolve().is_relative_to(folder.resolve()):
        raise ValueError('archive destination missing or unsafe')
    return {'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'size': target.stat().st_size}


def result_forms(inputs):
    if inputs.get('archive_additions'):
        return ('Original result unchanged after archive/index review; not re-executed',
                'archive/index correction reviewed; not re-executed', 'Fresh-context archive/index review: ')
    return ('Original result unchanged after metadata correction; not re-executed',
            'metadata correction reviewed; not re-executed', 'Fresh-context index/annotation review: ')


def capture(root, folder, metadata, additions=None):
    root = root.resolve()
    if folder.is_symlink() or not folder.resolve().is_relative_to(root):
        raise ValueError("unsafe feature directory")
    folder = folder.resolve()
    from feature_lifecycle import require_active
    require_active(v.read(folder / 'spec/requirements.json')['feature'])
    additions = archive_identity(root, additions or [])
    if not isinstance(metadata, list) or not (metadata or additions):
        raise ValueError('explicit index/annotation or archive addition scope required')
    names = []
    for entry in metadata:
        if not isinstance(entry, dict) or entry.get('role') not in ('index', 'annotation'):
            raise ValueError('explicit metadata role required; no extension-based exclusion')
        names.append(entry['path'])
    all_names = names + [r['path'] for r in additions]
    if len(all_names) != len(set(all_names)):
        raise ValueError('duplicate annotation/archive path')
    existing = {r['path'] for r in source_identity(root, folder)['evidence_files']}
    if any(r['path'] in existing or (folder / r['path']).exists() for r in additions):
        raise ValueError('archive additions must be new destinations; existing evidence cannot be replaced')
    before = {name: text_at(folder, name) for name in names}
    doc = v.load_plan(folder); stamp, head = v.context(root, folder, doc)
    req, _, impact = v.sources(root, folder)
    from evidence_carry import parent
    items, excluded = [], []
    for row in doc['items']:
        if row['history'] and row['history'][-1].get('retention_kind') in ('reviewed_carry', 'annotation_amend'):
            if v.state(row, stamp, v.manual_evidence_stamp(root, folder, row)) != 'retained':
                excluded.append({'item_id': row['id'], 'result_hash': digest(row['history'][-1]), 'reason': 'Already stale before capture; not eligible for this amendment'})
                continue
            items.append({'item_id': row['id'], 'source': row['source'], 'parent_claim': parent(req, impact, row),
                          'result_hash': digest(row['history'][-1]),
                          'tested_revision': row['history'][-1]['tested_revision'],
                          'semantic_digest': v.manual_evidence_stamp(root, folder, row)})
    if not items:
        raise ValueError('no current reviewed carry results to amend; reconcile prior staleness first')
    body = {'schema_version': 1, 'feature_id': folder.name, 'reviewed_revision': head,
            'metadata': metadata, 'before_text': before, 'plan_digest': digest(doc),
            'source_inputs': source_identity(root, folder), 'code_digest': digest(project_files(root)), 'items': items}
    if excluded:
        body['excluded_items'] = excluded
    if additions:
        body['schema_version'] = 2
        body['archive_additions'] = additions
    body['input_digest'] = digest(body)
    return body


def amend_inputs(root, folder, frozen):
    from feature_lifecycle import require_active
    require_active(v.read(folder / 'spec/requirements.json')['feature'])
    if frozen.get('schema_version') not in (1, 2) or frozen.get('feature_id') != folder.name:
        raise ValueError('invalid annotation snapshot identity')
    if frozen.get('input_digest') != digest({k: val for k, val in frozen.items() if k != 'input_digest'}):
        raise ValueError('annotation snapshot changed')
    doc = v.load_plan(folder)
    if digest(doc) != frozen['plan_digest'] or digest(project_files(root)) != frozen['code_digest']:
        raise ValueError('plan/code changed; annotation review cannot preserve a new result or implementation')
    current = source_identity(root, folder)
    old = frozen['source_inputs']
    if old['sources'] != current['sources'] or old['source_status_claims'] != current['source_status_claims']:
        raise ValueError('source authority changed; not an annotation-only correction')
    before = {r['path']: r['sha256'] for r in old['evidence_files']}
    after = {r['path']: r['sha256'] for r in current['evidence_files']}
    changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
    additions = frozen.get('archive_additions', [])
    if archive_identity(root, additions) != additions:
        raise ValueError('backed-up archive originals changed after capture')
    if any(r['path'] in before for r in additions):
        raise ValueError('archive addition attempts to overwrite original evidence')
    declared = sorted([m['path'] for m in frozen['metadata']] + [r['path'] for r in additions])
    if changed != declared:
        raise ValueError('review every metadata change and no raw change: ' + ', '.join(changed))
    after_text = {m['path']: text_at(folder, m['path']) for m in frozen['metadata']}
    archived = {r['path']: archived_file(folder, r['path']) for r in additions}
    for r in additions:
        if r['transformation'] == 'verbatim' and archived[r['path']]['sha256'] != r['origin_sha256']:
            raise ValueError('verbatim archive differs from backed-up original')
    if any(text is None for text in after_text.values()):
        raise ValueError('metadata deletion is not a supported annotation correction')
    items = {r['id']: r for r in doc['items']}
    for item in frozen['items']:
        row = items[item['item_id']]
        previous = row['history'][-1] if row['history'] else None
        if (not previous or previous.get('status') != 'retained'
                or previous.get('retention_kind') not in ('reviewed_carry', 'annotation_amend')
                or digest(previous) != item['result_hash']
                or previous.get('tested_revision') != item['tested_revision']
                or previous.get('evidence_digest') != item['semantic_digest']):
            raise ValueError('amendment requires a genuinely current retained predecessor; stale rows cannot be revived')
        if v.manual_evidence_stamp(root, folder, row, carry_sources=old) != item['semantic_digest']:
            raise ValueError('claim/decision/impact/traceability changed; not annotation-only')
    body = {'snapshot_digest': frozen['input_digest'], 'feature_id': folder.name,
            'before_text': frozen['before_text'], 'after_text': after_text,
            'metadata': frozen['metadata'], 'items': frozen['items'],
            'current_source_inputs': current, 'reviewed_revision': v.git(root, 'rev-parse', 'HEAD').decode().strip()}
    if frozen.get('excluded_items'):
        body['excluded_items'] = frozen['excluded_items']
    if additions:
        body['archive_additions'] = additions
        body['archived_files'] = archived
    body['input_digest'] = digest(body)
    return body


def validate_review(review, inputs):
    required_inputs = ('snapshot_digest', 'feature_id', 'before_text', 'after_text', 'metadata',
                       'items', 'current_source_inputs', 'reviewed_revision', 'input_digest')
    if not isinstance(inputs, dict) or any(key not in inputs for key in required_inputs):
        raise ValueError('annotation review inputs incomplete')
    if not isinstance(inputs['input_digest'], str) or len(inputs['input_digest']) != 64 or inputs['input_digest'] != digest({k: value for k, value in inputs.items() if k != 'input_digest'}):
        raise ValueError('annotation review input binding invalid')
    if not isinstance(inputs['metadata'], list) or not (inputs['metadata'] or inputs.get('archive_additions')) or not isinstance(inputs['before_text'], dict) or not isinstance(inputs['after_text'], dict):
        raise ValueError('annotation text/role inventory required')
    names = []
    for meta in inputs['metadata']:
        if not isinstance(meta, dict) or meta.get('role') not in ('index', 'annotation'):
            raise ValueError('invalid metadata classification')
        path_name(meta.get('path')); names.append(meta['path'])
    if len(names) != len(set(names)) or set(names) != set(inputs['before_text']) or set(names) != set(inputs['after_text']):
        raise ValueError('metadata/text scope mismatch')
    hashes = {r['path']: r['sha256'] for r in inputs['current_source_inputs']['evidence_files']}
    for name in names:
        text = inputs['after_text'][name]
        if not isinstance(text, str) or text == inputs['before_text'][name] or re.search(r'(?m)^(CMD:|OUT:)', text):
            raise ValueError('metadata is unchanged or contains raw command/output')
        if hashes.get(name) != hashlib.sha256(text.encode('utf-8')).hexdigest():
            raise ValueError('metadata text is not bound to current archived content')
    additions = inputs.get('archive_additions', [])
    archives = inputs.get('archived_files', {})
    if not isinstance(additions, list) or not all(isinstance(r, dict) for r in additions) or not isinstance(archives, dict):
        raise ValueError('invalid archived addition inventory')
    archive_names = []
    for r in additions:
        path_name(r.get('path')); scratch_path_name(r.get('origin_path'))
        if (not r['path'].startswith('evidence/') or not r['origin_path'].startswith('.agent-workflow/scratch/')
                or r.get('transformation') not in ('verbatim', 'redacted_extract')
                or not isinstance(r.get('purpose'), str) or not r['purpose'].strip()
                or not re.fullmatch(r'[0-9a-f]{64}', str(r.get('origin_sha256', '')))
                or not isinstance(r.get('origin_size'), int) or r['origin_size'] < 0):
            raise ValueError('invalid archive source identity')
        archive_names.append(r['path'])
        archive = archives.get(r['path'], {})
        if (archive.get('sha256') != hashes.get(r['path']) or not re.fullmatch(r'[0-9a-f]{64}', str(archive.get('sha256', '')))
                or not isinstance(archive.get('size'), int) or archive['size'] < 0):
            raise ValueError('archive output binding mismatch')
        if r['transformation'] == 'verbatim' and (archive['sha256'] != r['origin_sha256'] or archive['size'] != r['origin_size']):
            raise ValueError('verbatim archive source mismatch')
    if len(archive_names) != len(set(archive_names)) or set(archive_names) & set(names) or set(archive_names) != set(archives):
        raise ValueError('archive/metadata scope mismatch')
    accepted = ('supported', 'reviewed') if additions else ('supported',)
    if not isinstance(review, dict) or review.get('input_digest') != inputs['input_digest'] or review.get('status') not in accepted or review.get('independent_context') is not True:
        raise ValueError('fresh-context metadata review must support unchanged evidence meaning')
    for key in ('reviewer', 'classification_evidence', 'raw_evidence_unchanged', 'claim_meaning_unchanged', 'counterexample'):
        if not isinstance(review.get(key), str) or not review[key].strip():
            raise ValueError('annotation review lacks ' + key)
    verdicts = review.get('items')
    if not isinstance(verdicts, list) or not all(isinstance(r, dict) for r in verdicts) or sorted(r.get('item_id', '') for r in verdicts) != sorted(r['item_id'] for r in inputs['items']):
        raise ValueError('metadata review must account for each existing carry result')
    allowed = ('supported', 'affected', 'unknown', 'partial') if additions and review['status'] == 'reviewed' else ('supported',)
    if any(r.get('status') not in allowed or not isinstance(r.get('evidence'), str) or not r['evidence'].strip() for r in verdicts):
        raise ValueError('metadata correction exposes an affected/unknown claim; use targeted evidence review')

    if additions:
        assessment = review.get('archive_assessment')
        if not isinstance(assessment, list) or sorted(r.get('path', '') for r in assessment if isinstance(r, dict)) != sorted(archive_names) or len(assessment) != len(archive_names):
            raise ValueError('review each archive addition exactly once')
        for r in assessment:
            if r.get('status') != 'supported' or any(not isinstance(r.get(k), str) or not r[k].strip() for k in ('provenance', 'transformation_evidence', 'relevance_evidence')):
                raise ValueError('archive origin/transformation requires supported review')


@v.plan_mutation
def apply(root, folder, snapshot_path, review_path):
    frozen, review = v.read(snapshot_path), v.read(review_path)
    inputs = amend_inputs(root, folder, frozen)
    validate_review(review, inputs)
    doc = v.load_plan(folder); original = copy.deepcopy(doc)
    event = {'inputs': inputs, 'review': review}
    event['id'] = digest(event)
    doc.setdefault('annotation_reviews', []).append(event)
    supported = {r['item_id'] for r in review['items'] if r['status'] == 'supported'}
    actual, method, prefix = result_forms(inputs)
    for item in frozen['items']:
        if item['item_id'] not in supported:
            continue
        row = next(r for r in doc['items'] if r['id'] == item['item_id']); previous = row['history'][-1]
        receipt = {'schema_version': 1, 'item_id': row['id'], 'source_result_hash': digest(previous), 'review_id': event['id']}
        entry = v.result('retained', v.context(root, folder, doc)[0], previous['tested_revision'],
                         actual, prefix + review['classification_evidence'], method)
        entry.update(retention_kind='annotation_amend', reviewed_revision=inputs['reviewed_revision'],
                     changed_paths=[m['path'] for m in frozen['metadata']] + [r['path'] for r in inputs.get('archive_additions', [])],
                     reason=review['claim_meaning_unchanged'], source_result_digest=previous['digest'],
                     annotation_receipt=receipt, annotation_receipt_digest=digest(receipt))
        row['history'].append(entry); entry['evidence_digest'] = v.manual_evidence_stamp(root, folder, row)
    if amend_inputs(root, folder, frozen) != inputs or v.load_plan(folder) != original:
        raise ValueError('annotation inputs changed before save')
    v.save(folder / 'verification.json', doc); v.render(folder)
    print('EVIDENCE_ANNOTATION_REVIEWED: original test identity unchanged; no re-execution; retained=%d unresolved=%d excluded_stale=%d' % (len(supported), len(frozen['items']) - len(supported), len(frozen.get('excluded_items', []))))


def validated_reviews(doc):
    events = doc.get('annotation_reviews', [])
    if not isinstance(events, list):
        raise ValueError('invalid shared annotation reviews')
    ids = set()
    for event in events:
        if not isinstance(event, dict) or event.get('id') != digest({k: value for k, value in event.items() if k != 'id'}) or event['id'] in ids:
            raise ValueError('shared annotation review changed or duplicated')
        ids.add(event['id'])
        validate_review(event.get('review'), event.get('inputs', {}))
    return events


def validate_receipt(entry, previous, row, doc):
    receipt = entry.get('annotation_receipt')
    if not isinstance(receipt, dict) or entry.get('annotation_receipt_digest') != digest(receipt):
        raise ValueError('annotation receipt changed')
    if previous is None or previous.get('status') != 'retained' or previous.get('retention_kind') not in ('reviewed_carry', 'annotation_amend'):
        raise ValueError('annotation requires an existing reviewed carry, not a raw pass or withdrawal')
    if receipt.get('source_result_hash') != digest(previous) or receipt.get('item_id') != row['id']:
        raise ValueError('annotation receipt does not bind the prior result')
    event = next((r for r in validated_reviews(doc) if r['id'] == receipt.get('review_id')), None)
    if event is None:
        raise ValueError('annotation shared review missing')
    inputs = event['inputs']
    if inputs.get('input_digest') != digest({k: val for k, val in inputs.items() if k != 'input_digest'}):
        raise ValueError('annotation input digest changed')
    validate_review(event.get('review'), inputs)
    match = next((i for i in inputs['items'] if i['item_id'] == row['id']), None)
    verdict = next((r for r in event['review']['items'] if r['item_id'] == row['id']), None)
    if (not match or match['result_hash'] != digest(previous) or previous.get('evidence_digest') != match.get('semantic_digest')
            or not verdict or verdict['status'] != 'supported'):
        raise ValueError('annotation review row source mismatch')
    if entry['tested_revision'] != previous['tested_revision'] or entry.get('source_result_digest') != previous['digest'] or entry.get('reviewed_revision') != inputs.get('reviewed_revision'):
        raise ValueError('annotation changed original/current review identity')
    actual, method, prefix = result_forms(inputs)
    if (entry.get('actual') != actual
            or entry.get('method') != method
            or entry.get('evidence') != prefix + event['review']['classification_evidence']
            or entry.get('reason') != event['review']['claim_meaning_unchanged']):
        raise ValueError('annotation result must preserve metadata-only meaning; not a new execution')
    if entry.get('changed_paths') != [m['path'] for m in inputs['metadata']] + [r['path'] for r in inputs.get('archive_additions', [])]:
        raise ValueError('annotation change scope mismatch')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['capture', 'review-inputs', 'apply']); p.add_argument('root', type=Path); p.add_argument('feature_id')
    p.add_argument('--metadata', type=Path); p.add_argument('--additions', type=Path); p.add_argument('--snapshot', type=Path); p.add_argument('--review', type=Path)
    args = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.feature_id):
        p.error('invalid feature ID')
    root = args.root.resolve(); folder = root / '.agent-workflow/features' / args.feature_id
    try:
        if args.action == 'capture':
            if not args.metadata and not args.additions: p.error('capture requires --metadata and/or --additions')
            print(json.dumps(capture(root, folder, v.read(args.metadata) if args.metadata else [], v.read(args.additions) if args.additions else []), ensure_ascii=False, indent=2))
        elif args.action == 'review-inputs':
            if not args.snapshot: p.error('review-inputs requires --snapshot')
            print(json.dumps(amend_inputs(root, folder, v.read(args.snapshot)), ensure_ascii=False, indent=2))
        else:
            if not args.snapshot or not args.review: p.error('apply requires --snapshot --review')
            apply(root, folder, args.snapshot, args.review)
        return 0
    except (ValueError, OSError, KeyError, TypeError, UnicodeError) as exc:
        print('EVIDENCE_ANNOTATION_ERROR: ' + str(exc), file=sys.stderr); return 1


if __name__ == '__main__':
    sys.exit(main())
