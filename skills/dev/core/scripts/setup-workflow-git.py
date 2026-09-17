#!/usr/bin/env python3
"""Install scoped ignore defaults; never stage, untrack, commit or push files."""
import argparse
from pathlib import Path
import subprocess
import sys

START = '# BEGIN feature-delivery-skill local state'
END = '# END feature-delivery-skill local state'


def setup(root):
    if not root.is_dir():
        raise ValueError('project directory not found')
    work = root / '.agent-workflow'
    target = work / '.gitignore'
    if work.is_symlink() or target.is_symlink():
        raise ValueError('workflow and ignore file must not be symlinks')
    template = (Path(__file__).resolve().parents[1] / 'assets/workflow.gitignore').read_bytes()
    old = target.read_bytes() if target.exists() else b''
    # Keep existing rules byte-for-byte. Changed managed blocks need review.
    if START.encode() in old or END.encode() in old:
        if old.count(START.encode()) != 1 or old.count(END.encode()) != 1 or template.rstrip(b'\n') not in old:
            raise ValueError('existing managed ignore block differs; reconcile manually')
        print('IGNORE_UNCHANGED')
    else:
        work.mkdir(exist_ok=True)
        target.write_bytes(old + (b'\n' if old and not old.endswith(b'\n') else b'') + template)
        print('IGNORE_CONFIGURED: .agent-workflow/.gitignore')
    # Git ignores cannot untrack existing files or override excluded parent dirs.
    probe = subprocess.run(['git', '-C', str(root), 'check-ignore', '--no-index', '-q', '.agent-workflow/project-baseline/architecture.md'], capture_output=True)
    if probe.returncode == 0:
        print('REVIEW_REQUIRED: parent/existing rules hide shareable baseline; do not remove them without checking project policy')
    tracked = subprocess.run(['git', '-C', str(root), 'ls-files', '-z', '--', '.agent-workflow'], capture_output=True)
    if tracked.returncode == 0 and tracked.stdout:
        ignored = subprocess.run(['git', '-C', str(root), 'check-ignore', '--no-index', '--stdin', '-z'], input=tracked.stdout, capture_output=True)
        if ignored.stdout:
            print('REVIEW_REQUIRED: %d already tracked paths match ignore rules; index unchanged' % len(ignored.stdout.rstrip(b'\0').split(b'\0')))
    print('REVIEW_BEFORE_COMMIT: specs and summaries may also contain confidential source content')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    try:
        setup(args.root.resolve())
    except (OSError, ValueError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(2)
