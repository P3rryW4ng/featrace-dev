#!/usr/bin/env python3
"""Read-only structural routing signal after an authorized feature mutation.

This is a trigger aid, not semantic acceptance or a second feature status.
"""
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
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.feature_id):
        parser.error('invalid feature ID')
    root = args.root.resolve()
    folder = root / '.agent-workflow/features' / args.feature_id
    try:
        req = json.loads((folder / 'spec/requirements.json').read_text())
        tasks = json.loads((folder / 'tasks.json').read_text())['tasks']
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('CLOSURE_ROUTE_BLOCKED: cannot read feature records: ' + str(exc))
        return 1
    feature = req.get('feature', {})
    if not isinstance(feature, dict) or feature.get('id') != args.feature_id or not isinstance(tasks, list):
        print('CLOSURE_ROUTE_BLOCKED: feature identity or tasks invalid')
        return 1
    if feature.get('status') == 'complete':
        print('CLOSURE_ROUTE_COMPLETE: delivery already recorded; archive and push are separate')
        return 0
    archive = feature.get('archive')
    if isinstance(archive, dict) and archive.get('archived'):
        print('CLOSURE_ROUTE_BLOCKED: archived feature requires restore')
        return 0
    if not tasks or any(not isinstance(task, dict) or task.get('status') != 'done' for task in tasks):
        print('CLOSURE_ROUTE_TASKS_PENDING: finish or resolve active tasks before Verify')
        return 0
    script_dir = Path(__file__).resolve().parent
    checks = (
        [sys.executable, str(script_dir / 'validate-feature.py'), '--stage', 'check', str(root), args.feature_id],
        [sys.executable, str(script_dir / 'audit-delivery.py'), str(root), args.feature_id],
    )
    results = [subprocess.run(command, capture_output=True, text=True) for command in checks]
    if any(run.returncode for run in results):
        print('CLOSURE_ROUTE_VERIFY_REQUIRED: current check or audit is incomplete')
        for label, run in zip(('check', 'audit'), results):
            if run.returncode:
                for line in run.stdout.splitlines():
                    if line.startswith(('ERROR:', 'WARNING:')):
                        print(label + ': ' + line)
                if not run.stdout.strip() and run.stderr.strip():
                    print(label + ': ' + run.stderr.strip())
        return 0
    print('CLOSURE_ROUTE_DELIVER_ELIGIBLE: structural checks current; review full claim-to-evidence meaning before Deliver')
    return 0


if __name__ == '__main__':
    sys.exit(main())
