#!/usr/bin/env python3
"""Record an already performed PRD review; this command does not perform it."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from prd_intake import validate_intake, review_digest, render_intake


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('feature_id')
    parser.add_argument('--stage', choices=('draft', 'develop'), default='develop',
                        help='draft records partial reading with warnings; develop requires all reading gaps resolved')
    parser.add_argument('--reviewer', required=True)
    parser.add_argument('--notes', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.feature_id) or not args.reviewer.strip() or not args.notes.strip():
        raise ValueError('valid feature ID, reviewer and notes required')
    folder = args.root.resolve() / '.agent-workflow/features' / args.feature_id
    req = json.loads((folder / 'spec/requirements.json').read_text())
    if not isinstance(req, dict) or req.get('feature', {}).get('id') != args.feature_id or not isinstance(req.get('requirements'), list):
        raise ValueError('requirements feature/records do not match the requested workspace')
    errors, warnings = validate_intake(folder, req, args.stage, require_review=False)
    if errors:
        print('\n'.join('ERROR: ' + e for e in errors)); return 1
    path = folder / 'spec/prd-intake.json'
    doc = json.loads(path.read_text())
    doc['review'] = {'stage': args.stage, 'reviewer': args.reviewer, 'notes': args.notes,
                     'recorded_at': datetime.now(timezone.utc).isoformat(),
                     'digest': review_digest(folder, doc, req)}
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n')
    render_intake(folder)
    for warning in warnings:
        print('WARNING: ' + warning)
    label = 'PARTIAL_DRAFT_REVIEW_RECORDED' if args.stage == 'draft' else 'REVIEW_RECORDED'
    print(label + ': attributed review only; no automated semantic verification')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr); sys.exit(1)
