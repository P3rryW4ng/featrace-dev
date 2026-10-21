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
    parser.add_argument('--verification-policy', action='store_true', help='Explicit scoped/schema7 route (alias)')
    parser.add_argument('--verification-route', choices=('legacy', 'scoped'),
                        help='Choose acceptance independently of parent traceability; required for a linked increment')
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

    route = args.verification_route
    if args.verification_policy:
        if route == 'legacy': raise ValueError('conflicting verification routes')
        route = 'scoped'
    if args.parent and route is None:
        raise ValueError('linked work requires an explicit --verification-route legacy|scoped; inspect readiness before choosing')
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
    if route is not None:
        # 1 retains the existing scoped contract; 2 is guarded legacy planning.
        # Old policy readers reject 2 rather than skipping the causal obligations.
        feature['verification_policy'] = 1 if route == 'scoped' else 2
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
    from verification_policy import delivery_readiness
    print('DELIVERY_READINESS: ' + json.dumps(delivery_readiness(root, args.feature_id), ensure_ascii=False))
    print('NEXT: inspect the actual route and prerequisites before Build/check execution; intake is not preparation or acceptance')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, UnicodeError, ValueError, subprocess.CalledProcessError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(2)
