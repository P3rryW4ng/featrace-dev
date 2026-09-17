#!/usr/bin/env python3
"""Register a reported mismatch in an existing feature; classification follows investigation."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from fixes import read_fixes, render_fixes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('feature_id')
    parser.add_argument('description')
    parser.add_argument('--expected', default='')
    parser.add_argument('--actual', default='')
    parser.add_argument('--reproduction', default='')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.feature_id) or not args.description.strip():
        raise ValueError('valid feature ID and non-empty problem description required')
    folder = args.root.resolve() / '.agent-workflow/features' / args.feature_id
    requirements = json.loads((folder / 'spec/requirements.json').read_text())
    if requirements.get('feature', {}).get('id') != args.feature_id:
        raise ValueError('feature record does not match requested ID')
    doc = read_fixes(folder, args.feature_id)
    if not isinstance(doc, dict) or doc.get('feature_id') != args.feature_id or not isinstance(doc.get('fixes'), list):
        raise ValueError('invalid fixes.json; preserve it for manual repair')
    for fix in doc['fixes']:
        if isinstance(fix, dict) and fix.get('description') == args.description and fix.get('status') != 'verified':
            print('FIX_ALREADY_RECORDED: ' + str(fix.get('id'))); return 0
    numbers = [int(fix['id'][4:]) for fix in doc['fixes'] if isinstance(fix, dict) and
               isinstance(fix.get('id'), str) and re.fullmatch(r'FIX-\d+', fix['id'])]
    fid = 'FIX-%03d' % (max(numbers, default=0) + 1)
    previous_status = requirements['feature'].get('status')
    doc['fixes'].append({'id': fid, 'description': args.description,
                         'status': 'reported', 'kind': 'unclassified',
                         'expected': args.expected, 'actual': args.actual,
                         'reproduction': args.reproduction,
                         'requirement_ids': [], 'task_ids': [], 'decision_ids': [],
                         'evidence': [], 'verification': [], 'contributing_kinds': [],
                         'task_changes': [], 'regression_test_ids': [],
                         'reported_at': datetime.now(timezone.utc).isoformat(),
                         'previous_feature_status': previous_status})
    (folder / 'fixes.json').write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n')
    if previous_status == 'complete':
        requirements['feature']['status'] = 'provisional'
        (folder / 'spec/requirements.json').write_text(json.dumps(requirements, ensure_ascii=False, indent=2) + '\n')
    render_fixes(folder, args.feature_id)
    print('FIX_RECORDED: ' + fid)
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(2)
