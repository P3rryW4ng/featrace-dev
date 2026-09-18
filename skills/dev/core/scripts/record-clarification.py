#!/usr/bin/env python3
"""Register an unanswered clarification without changing product meaning or code."""
from feature_lifecycle import require_active
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from clarifications import render_decisions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('feature_id')
    parser.add_argument('question')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.feature_id) or not args.question.strip():
        raise ValueError('valid feature ID and non-empty question required')
    folder = args.root.resolve() / '.agent-workflow/features' / args.feature_id
    req = json.loads((folder / 'spec/requirements.json').read_text())
    doc = json.loads((folder / 'decisions.json').read_text())
    if not isinstance(req, dict) or not isinstance(req.get('feature'), dict) or req['feature'].get('id') != args.feature_id:
        raise ValueError('feature record does not match requested ID')
    if not isinstance(doc, dict) or doc.get('feature_id') != args.feature_id or not isinstance(doc.get('decisions'), list):
        raise ValueError('invalid decisions.json; preserve it for manual repair')
    require_active(req['feature'])
    decisions = doc['decisions']
    ids = [d.get('id') for d in decisions if isinstance(d, dict)]
    if len(ids) != len(decisions) or any(not isinstance(i, str) or not i.strip() for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('invalid or duplicate decision IDs; preserve records for manual repair')
    for d in decisions:
        c = d.get('clarification', {})
        if isinstance(c, dict) and c.get('question') == args.question and d.get('status') in ('pending', 'blocked'):
            print('CLARIFICATION_ALREADY_RECORDED: ' + d['id'])
            return 0
    numbers = [int(i[2:]) for i in ids if re.fullmatch(r'D-\d+', i)]
    did = 'D-%03d' % (max(numbers, default=0) + 1)
    decisions.append({'id': did, 'title': args.question, 'status': 'pending',
                      'sources': [], 'options': [], 'chosen': '', 'impact': [],
                      'clarification': {'question': args.question,
                          'recorded_at': datetime.now(timezone.utc).isoformat(),
                          'evidence': [], 'impact_review': '',
                          'resolution_kind': 'unclassified', 'confirmation_ref': '',
                          'application': {'status': 'pending', 'evidence': []}}})
    (folder / 'decisions.json').write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n')
    if req['feature'].get('status') == 'complete':
        req['feature']['status'] = 'provisional'
        (folder / 'spec/requirements.json').write_text(json.dumps(req, ensure_ascii=False, indent=2) + '\n')
    render_decisions(folder, decisions)
    print('CLARIFICATION_RECORDED: ' + did)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(2)
