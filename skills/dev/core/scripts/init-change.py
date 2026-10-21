#!/usr/bin/env python3
"""Create a lightweight work item from a short, preserved user report."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('feature_id')
    parser.add_argument('--kind', choices=('change', 'defect', 'unclear'), required=True)
    parser.add_argument('--request-file', type=Path, required=True,
                        help='regular UTF-8 file containing the user report verbatim')
    parser.add_argument('--verification-policy', action='store_true')
    parser.add_argument('--parent', help='Complete historical feature; create a separate increment, never reopen it')
    parser.add_argument('--delivery-revision', help='Full original delivered code revision')
    parser.add_argument('--delivery-evidence', help='Existing source establishing that delivered revision')
    args = parser.parse_args()

    root = args.root.resolve()
    source = args.request_file.resolve()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.feature_id):
        raise ValueError('valid product work-item ID required')
    if not root.is_dir() or not args.request_file.is_file() or args.request_file.is_symlink():
        raise ValueError('project and regular request file required')
    if source.suffix.lower() not in ('.md', '.txt'):
        raise ValueError('request file must be Markdown or plain text')
    report = source.read_text(encoding='utf-8')
    if not report.strip():
        raise ValueError('request description must not be empty')
    folder = root / '.agent-workflow' / 'features' / args.feature_id
    if folder.exists():
        raise ValueError('work item already exists; use its existing feature or choose a distinct product ID')

    context = None
    if args.parent or args.delivery_revision or args.delivery_evidence:
        if not all((args.parent,args.delivery_revision,args.delivery_evidence)) or args.parent == args.feature_id:
            raise ValueError('distinct parent, delivered revision and evidence required')
        from verification_policy import followup_context
        context = followup_context(root,args.parent,args.delivery_revision,args.delivery_evidence)
    scripts = Path(__file__).resolve().parent
    subprocess.run([sys.executable, str(scripts / 'init-feature.py'), args.feature_id,
                    str(source), str(root)], check=True)
    requirements_path = folder / 'spec' / 'requirements.json'
    requirements = json.loads(requirements_path.read_text(encoding='utf-8'))
    feature = requirements['feature']
    feature['entry_kind'] = args.kind
    if args.verification_policy or context:
        feature['verification_policy'] = 1
    if context:
        feature['change_context'] = context
    feature['source_notes']['prd'] = (
        'Initial source is a user-reported change or observed problem, not an approved full PRD. '
        'Investigate the current contract and confirm any new expected behavior before development.'
    )
    requirements_path.write_text(json.dumps(requirements, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    subprocess.run([sys.executable, str(scripts / 'render-workspace.py'), str(root),
                    args.feature_id], check=True)

    if args.kind == 'defect':
        subprocess.run([sys.executable, str(scripts / 'record-fix.py'), str(root),
                        args.feature_id, report.strip()], check=True)
    print('LIGHTWEIGHT_WORK_ITEM_CREATED: ' + str(folder))
    print('NEXT: review the report, locate affected code and old behavior, then complete normal intake and Scope')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, UnicodeError, ValueError, subprocess.CalledProcessError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(2)
