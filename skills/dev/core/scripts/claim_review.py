#!/usr/bin/env python3
"""Bind a focused, independent claim-to-evidence review to current Verify inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from impact import digest, snapshot as impact_snapshot
from verification import load_plan, state, context, manual_evidence_stamp


def identity(root, folder):
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
    claims = []
    by_id = {r['id']: r for r in req.get('requirements', [])}
    for row in active:
        rid = row['source'].split(':')[1] if row['source'].startswith('requirement:') else None
        parent = by_id.get(rid, {})
        outcome = state(row, stamp, manual_evidence_stamp(root, folder, row) if row['mode'] == 'manual' else None)
        claims.append({'id': row['id'], 'requirement_statement': parent.get('statement', ''),
                       'expected': row['expected'], 'mode': row['mode'], 'result_status': outcome,
                       'result': row['history'][-1] if row['history'] else None})
    impact = json.loads((folder / 'impact.json').read_text())
    binding = digest({'requirements': req['requirements'], 'sources': sources,
                      'intake': json.loads(intake_path.read_text()) if intake_path.is_file() else None,
                      'impact': impact_snapshot(root, impact)['digest'],
                      'claims': claims})
    return {'feature_id': folder.name, 'input_digest': binding, 'code_revision': head,
            'source_hashes': sources, 'claims': claims}


def validate(root, folder):
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
        errors = []
        current_rows = {r['id']: r for r in current['claims']}
        for item in rows:
            name = item['id']
            allowed = ('supported', 'approved_waiver') if current_rows[name]['result_status'] == 'waived' else ('supported',)
            if item.get('verdict') not in allowed:
                errors.append('claim-to-evidence review unresolved: ' + name)
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
    parser.add_argument('action', choices=('capture', 'check'))
    parser.add_argument('root', type=Path)
    parser.add_argument('feature_id')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.feature_id):
        parser.error('invalid feature ID')
    root = args.root.resolve()
    folder = root / '.agent-workflow/features' / args.feature_id
    try:
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
