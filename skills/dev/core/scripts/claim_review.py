#!/usr/bin/env python3
"""Bind a focused, independent claim-to-evidence review to current Verify inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from impact import digest, snapshot as impact_snapshot
from verification import load_plan, state, context, manual_evidence_stamp, row_evidence_stamp, check_currency


def identity(root, folder):
    from acceptance_contract import enabled, capture_assessment
    if enabled(load_plan(folder)): return capture_assessment(root,folder)[0]
    req = json.loads((folder / 'spec/requirements.json').read_text())
    plan = load_plan(folder)
    stamp, head = context(root, folder, plan)
    source_paths = set(req.get('feature', {}).get('prd_paths', []))
    intake_path = folder / 'spec/prd-intake.json'
    if intake_path.is_file():
        intake = json.loads(intake_path.read_text())
        source_paths.update(s.get('path') for s in intake.get('sources', []) if isinstance(s, dict))
    sources = {}
    for name in sorted(source_paths):
        if not isinstance(name, str) or not name.startswith('sources/') or '..' in Path(name).parts:
            raise ValueError('invalid source path in review input')
        path = folder / name
        if path.is_symlink() or not path.resolve().is_relative_to(folder.resolve()):
            raise ValueError('unsafe source path in review input')
        sources[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    active = [r for r in plan['items'] if r['source'] != 'system:no-gates' and not r['source'].startswith('gate:')]
    execution_view = check_currency(root, folder)
    claims = []
    by_id = {r['id']: r for r in req.get('requirements', [])}
    for row in active:
        rid = row['source'].split(':')[1] if row['source'].startswith('requirement:') else None
        parent = by_id.get(rid, {})
        outcome = state(row, stamp, row_evidence_stamp(root, folder, row, execution_view))
        claims.append({'id': row['id'], 'requirement_statement': parent.get('statement', ''),
                       'expected': row['expected'], 'mode': row['mode'], 'result_status': outcome,
                       'result': row['history'][-1] if row['history'] else None})
    if plan.get('manual_scope_contract') == 1:
        scope = (execution_view or {}).get('_manual_scope', {})
        for claim in claims:
            if claim['id'] in scope.get('items', {}): claim['manual_scope'] = scope['items'][claim['id']]
    if plan.get('result_correction_reviews'):
        from result_corrections import links
        for claim in claims:
            row = next(r for r in active if r['id'] == claim['id'])
            corrections = links(root, plan, row)
            if corrections:
                claim['result_corrections'] = corrections
    impact = json.loads((folder / 'impact.json').read_text())
    if plan.get('adoption_reviews'):
        from evidence_adoption import links as adoption_links
        for claim in claims:
            claim['evidence_adoptions'] = adoption_links(plan, next(r for r in active if r['id'] == claim['id']))
    fix_doc = json.loads((folder / 'fixes.json').read_text()) if (folder / 'fixes.json').is_file() else None
    continuity = None
    from regression_continuity import present
    if present(fix_doc):
        from regression_continuity import summaries
        continuity = summaries(root, folder, fix_doc)
    binding = digest({'requirements': req['requirements'], 'sources': sources,
                      'intake': json.loads(intake_path.read_text()) if intake_path.is_file() else None,
                      'impact': impact_snapshot(root, impact)['digest'],
                      'claims': claims, **({'manual_scope_reviews': plan['manual_scope_reviews']} if plan.get('manual_scope_contract') == 1 else {}), **({'device_continuity': {'summary': continuity, 'events': fix_doc['regression_continuity_reviews']}} if continuity is not None else {})})
    scope_refs = [{'event_id': e['id'], 'path': '.agent-workflow/features/' + folder.name + '/verification.json#manual_scope_reviews/' + e['id']} for e in plan.get('manual_scope_reviews', [])]
    work = None
    if plan.get('manual_scope_contract') == 1:
        reusable = [{'id': c['id'], 'ref': c['manual_scope']['review_ref'], 'event_id': c['manual_scope']['event_id']}
                    for c in claims if c.get('manual_scope',{}).get('state') == 'current' and c.get('result_status') in ('passed','retained')]
        work = {'reuse_applicability': reusable, 'assess': [c['id'] for c in claims if c['id'] not in {r['id'] for r in reusable}],
                'instruction': 'Cover all claims; inspect current prior finding and contradictions for reuse, do not repeat the same complete delta investigation without new cause. Not an automatic verdict.'}
    return {'feature_id': folder.name, 'input_digest': binding, 'code_revision': head, **({'review_work':work} if work is not None else {}),
            'source_hashes': sources, 'claims': claims, **({'manual_scope_review_refs': scope_refs} if scope_refs else {}), **({'device_continuity': continuity} if continuity is not None else {})}


def validate(root, folder):
    from acceptance_contract import enabled, resolve_claims
    try:
        if enabled(load_plan(folder)):
            return ['claim-to-evidence review unresolved: '+json.dumps(b) for b in resolve_claims(root,folder)['blockers']]
    except (OSError,ValueError,KeyError,TypeError) as exc: return ['invalid acceptance review: '+str(exc)]
    path = folder / 'claim-review.json'
    if path.is_symlink():
        return ['claim-to-evidence review must be a local regular file']
    if not path.is_file():
        return ['claim-to-evidence review missing']
    try:
        current = identity(root, folder)
        review = json.loads(path.read_text())
        if review.get('feature_id') != folder.name or review.get('input_digest') != current['input_digest']:
            return ['claim-to-evidence review stale; repeat on current requirements and evidence']
        rows = review.get('findings')
        expected = {r['id'] for r in current['claims']}
        if not isinstance(rows, list) or len(rows) != len(expected) or {r.get('id') for r in rows if isinstance(r, dict)} != expected:
            return ['claim-to-evidence review must cover every active acceptance row exactly once']
        errors = ['device continuity stale: ' + c['fix_id'] + ':' + c['test_id'] for c in current.get('device_continuity', []) if c['status'] != 'current']
        current_rows = {r['id']: r for r in current['claims']}
        for item in rows:
            name = item['id']
            allowed = ('supported', 'approved_waiver') if current_rows[name]['result_status'] == 'waived' else ('supported',)
            if item.get('verdict') not in allowed:
                errors.append('claim-to-evidence review unresolved: ' + name)
            if item.get('applicability_ref') is not None:
                prior = next((r for r in current.get('review_work',{}).get('reuse_applicability',[]) if r['id'] == name),None)
                if prior is None or item['applicability_ref'] != prior['ref']:
                    errors.append('claim-to-evidence applicability reference stale/unsupported: ' + name)
            for key in ('source_basis', 'required_scope', 'observed_scope', 'evidence_ref', 'counterexample_check'):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    errors.append('claim-to-evidence review lacks ' + key + ': ' + name)
        if not isinstance(review.get('reviewer'), str) or not review['reviewer'].strip():
            errors.append('claim-to-evidence review lacks reviewer identity')
        return errors
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return ['invalid claim-to-evidence review: ' + str(exc)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('capture', 'check', 'apply'))
    parser.add_argument('root', type=Path)
    parser.add_argument('feature_id')
    parser.add_argument('--request',type=Path); parser.add_argument('--review',type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.feature_id):
        parser.error('invalid feature ID')
    root = args.root.resolve()
    folder = root / '.agent-workflow/features' / args.feature_id
    try:
        if args.action == 'apply':
            from acceptance_contract import apply_assessment, read, project_views
            if not args.request or not args.review: raise ValueError('request and review required')
            apply_assessment(root,folder,read(args.request),read(args.review)); project_views(root,folder); return 0
        if args.action == 'capture':
            print(json.dumps(identity(root, folder), ensure_ascii=False, indent=2))
            return 0
        errors = validate(root, folder)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        errors = [str(exc)]
    for error in errors:
        print('CLAIM_REVIEW_ERROR: ' + error)
    if errors:
        return 1
    print('CLAIM_REVIEW_CURRENT')
    return 0


if __name__ == '__main__':
    sys.exit(main())
