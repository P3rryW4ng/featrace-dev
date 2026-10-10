#!/usr/bin/env python3
"""Read-only changed-path inventory for an already completed feature."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


def git(root, *args):
    run = subprocess.run(['git', '-C', str(root), *args], capture_output=True)
    if run.returncode:
        raise ValueError('cannot inspect Git revision or changes: ' + run.stderr.decode(errors='replace').strip())
    return run.stdout


def paths(data):
    return {part.decode('utf-8', 'surrogateescape') for part in data.split(b'\0') if part}


def workflow(path):
    return path == '.agent-workflow' or path.startswith('.agent-workflow/')


def inspect(root, feature_id, base):
    if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', base):
        raise ValueError('base must be the full delivered commit SHA from the accepted report')
    if Path(git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != root:
        raise ValueError('project path must be the Git root')
    folder = root / '.agent-workflow' / 'features' / feature_id
    record = json.loads((folder / 'spec/requirements.json').read_text())
    if record.get('feature', {}).get('id') != feature_id or record['feature'].get('status') != 'complete':
        raise ValueError('post-merge review requires an already complete feature')
    report = folder / 'delivery-report.md'
    if not report.is_file() or not report.read_text().strip():
        raise ValueError('accepted delivery report missing; establish the delivered revision first')
    git(root, 'rev-parse', '--verify', base + '^{commit}')
    git(root, 'merge-base', '--is-ancestor', base, 'HEAD')
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    if head == base:
        raise ValueError('HEAD has not advanced beyond the delivered revision')
    committed = paths(git(root, 'diff', '--name-only', '--no-renames', '-z', base, 'HEAD', '--'))
    dirty = set()
    for args in [('diff', '--name-only', '-z', '--'),
                 ('diff', '--cached', '--name-only', '-z', '--'),
                 ('ls-files', '--others', '--exclude-standard', '-z', '--')]:
        dirty.update(paths(git(root, *args)))
    project = sorted(path for path in committed | dirty if not workflow(path))
    return {'feature_id': feature_id, 'delivered_revision': base, 'current_revision': head,
            'committed_changed_paths': sorted(committed), 'worktree_changed_paths': sorted(dirty),
            'project_changed_paths': project,
            'state': 'NO_PROJECT_CHANGE' if not project else 'REVIEW_REQUIRED',
            'meaning': ('No tracked or non-ignored project path changed; historical delivery remains tied to its original revision.'
                        if not project else 'Review every changed project path and its callers/dependencies; no old check or manual observation has been promoted to the current revision.')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('feature_id')
    parser.add_argument('--base', required=True, help='full delivered commit SHA confirmed from the accepted report')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.feature_id):
        parser.error('invalid feature ID')
    try:
        result = inspect(args.root.resolve(), args.feature_id, args.base)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print('POST_MERGE_REVIEW_ERROR: ' + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
