"""Read-only Git disposition for shareable feature/module records."""
import json
import re
import subprocess


def report(root, feature_id, modules):
    def git(*args):
        return subprocess.run(['git', '-C', str(root), *args], capture_output=True)
    top = git('rev-parse', '--show-toplevel')
    from pathlib import Path
    if top.returncode or Path(top.stdout.decode().strip()).resolve() != root.resolve():
        return {'state': 'unavailable', 'reason': 'project root is not a Git root; archive is local only'}
    prefix = '.agent-workflow/features/' + feature_id + '/'
    names = ['spec/requirements.json', 'spec/prd-intake.json', 'spec/spec.md', 'tasks.json', 'tasks.md',
             'decisions.json', 'decisions.md', 'traceability.json', 'traceability.md', 'fixes.json', 'fixes.md',
             'impact.json', 'impact.md', 'verification.json', 'verification.md', 'regression-review.json',
             'regression-review.md', 'revisions', 'revisions.md', 'delivery-report.md']
    paths = [prefix + n for n in names]
    paths += ['.agent-workflow/modules/index.json', '.agent-workflow/modules/index.md']
    for name in modules:
        if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', name):
            paths += ['.agent-workflow/modules/' + name + ext for ext in ('.json', '.md')]
    status = git('status', '--porcelain=v1', '-z', '--untracked-files=all', '--ignored=matching', '--', *[':(literal)' + p for p in paths])
    if status.returncode:
        return {'state': 'unavailable', 'reason': 'Git status failed; no saved-state claim'}
    entries = status.stdout.decode().split('\0'); files = []; i = 0
    while i < len(entries):
        item = entries[i]; i += 1
        if not item:
            continue
        code, path = item[:2], item[3:]
        entry = {'path': path, 'git_status': code,
                 'state': 'untracked' if code == '??' else ('ignored_by_policy' if code == '!!' else 'uncommitted')}
        if 'R' in code or 'C' in code:
            entry['previous_path'] = entries[i]; i += 1
        files.append(entry)
    branch = git('symbolic-ref', '--quiet', '--short', 'HEAD')
    upstream = git('rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{upstream}')
    counts = git('rev-list', '--left-right', '--count', 'HEAD...@{upstream}')
    remote = {'state': 'unknown_no_upstream', 'network_checked': False}
    if not counts.returncode and not upstream.returncode:
        ahead, behind = map(int, counts.stdout.split())
        remote = {'upstream': upstream.stdout.decode().strip(), 'ahead': ahead, 'behind': behind, 'network_checked': False}
    return {'state': 'needs_git_review' if files else 'tracked_scope_clean',
            'branch': branch.stdout.decode().strip() or 'detached_or_unborn', 'files': files,
            'remote_tracking': remote, 'note': 'Archive is not commit/push. Review sensitivity before staging; remote counts are local tracking data only.'}


def show(root, feature_id, modules):
    print('GIT_RECORD_STATUS: ' + json.dumps(report(root, feature_id, modules), ensure_ascii=False))
