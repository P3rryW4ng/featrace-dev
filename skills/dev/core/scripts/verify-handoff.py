#!/usr/bin/env python3
"""Bind an optional read-only reviewer to inputs; never approve delivery or write records."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                     separators=(',', ':')).encode()).hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE,
                                   env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})


def relative(value):
    p = Path(value)
    if not value or p.is_absolute() or '..' in p.parts or '.git' in p.parts or p.as_posix() == '.':
        raise ValueError('unsafe project path: ' + str(value))
    return p.as_posix()


def file_state(root, name):
    name = relative(name)
    p = root
    for part in Path(name).parts:
        p = p / part
        if p.is_symlink():
            return {'state': 'unavailable', 'reason': 'symlink'}
    if not p.exists():
        return {'state': 'missing'}
    if not p.is_file():
        return {'state': 'unavailable', 'reason': 'not a regular file'}
    h = hashlib.sha256()
    with p.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return {'state': 'file', 'sha256': h.hexdigest(), 'size': p.stat().st_size}


def tree_paths(root, name):
    # Do not follow even in-project symlinks; they are an explicit reading gap.
    name = relative(name)
    p = root
    for part in Path(name).parts:
        p /= part
        if p.is_symlink():
            return [name]
    if not p.is_dir():
        return [name]
    result = []
    for folder, dirs, files in os.walk(p, followlinks=False):
        for directory in list(dirs):
            target = Path(folder) / directory
            if target.is_symlink():
                result.append(target.relative_to(root).as_posix())
                dirs.remove(directory)
        result.extend((Path(folder) / f).relative_to(root).as_posix() for f in files)
    return result


def names(data):
    return sorted({p.decode('utf-8', 'surrogateescape') for p in data.split(b'\0') if p})


def collect(root, feature_id, base, extra):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', feature_id):
        raise ValueError('invalid feature ID')
    if Path(git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != root:
        raise ValueError('project must be the Git root')
    base = git(root, 'rev-parse', '--verify', '--end-of-options', base + '^{commit}').decode().strip()
    git(root, 'merge-base', '--is-ancestor', base, 'HEAD')
    if b'160000 ' in git(root, 'ls-files', '--stage'):
        raise ValueError('submodules require a separate frozen review; unsupported in this pilot')
    folder = '.agent-workflow/features/' + feature_id
    required = folder + '/spec/requirements.json'
    if file_state(root, required)['state'] != 'file':
        raise ValueError('requirements missing or unsafe')
    if json.loads((root / required).read_text()).get('feature', {}).get('id') != feature_id:
        raise ValueError('feature ID mismatch')
    tracked = names(git(root, 'ls-files', '-z'))
    untracked = names(git(root, 'ls-files', '--others', '--exclude-standard', '-z'))
    extra = sorted({relative(p) for p in extra})
    bound = set(untracked + extra)
    for path in (folder, '.agent-workflow/project-baseline', '.agent-workflow/modules'):
        bound.update(tree_paths(root, path))
    bound.update(['.agent-workflow/config.yaml', '.agent-workflow/quality-gates.json'])
    skill = Path(__file__).resolve().parents[2]
    skill_files = {p.relative_to(skill).as_posix(): file_state(skill, p.relative_to(skill).as_posix())
                   for p in skill.rglob('*') if (p.is_file() or p.is_symlink())
                   and '__pycache__' not in p.parts and p.suffix != '.pyc'
                   and p.name != '.feature-delivery-install.json'}
    return {'schema_version': 1, 'project': str(root), 'feature_id': feature_id,
            'base_revision': base, 'extra_paths': extra,
            'git_head': git(root, 'rev-parse', 'HEAD').decode().strip(),
            'tracked_paths': tracked,
            'base_paths': sorted(row.split(b'\t', 1)[1].decode('utf-8', 'surrogateescape')
                                 for row in git(root, 'ls-tree', '-r', '-z', base).split(b'\0')
                                 if row.startswith((b'100644 ', b'100755 '))),
            'changed_paths': names(git(root, 'diff', '--no-ext-diff', '--name-only', '-z', base)),
            'worktree_diff_sha256': hashlib.sha256(git(root, 'diff', '--no-ext-diff', '--no-textconv',
                                                     '--binary', 'HEAD', '--')).hexdigest(),
            'index_sha256': hashlib.sha256(git(root, 'ls-files', '--stage', '-z')).hexdigest(),
            'files': {p: file_state(root, p) for p in sorted(bound)},
            'skill_sha256': digest(skill_files)}


def capture(root, feature_id, base, extra):
    first = collect(root, feature_id, base, extra)
    second = collect(root, feature_id, first['base_revision'], extra)
    if first != second:
        raise ValueError('inputs changed during capture; pause writers and retry')
    return {'input_digest': digest(first), 'inputs': first}


def text(value):
    return isinstance(value, str) and bool(value.strip())


def validate_result(result, snapshot):
    if not isinstance(result, dict) or result.get('input_digest') != snapshot['input_digest']:
        raise ValueError('review result missing or bound to another input digest')
    if result.get('status') not in ('reviewed', 'blocked', 'failed') or not text(result.get('summary')):
        raise ValueError('review status/summary invalid; passed and complete are not review statuses')
    for key in ('read_paths', 'findings', 'gaps', 'checks_not_run'):
        if not isinstance(result.get(key), list):
            raise ValueError('review requires list: ' + key)
    bound = snapshot['inputs']
    permitted = set(bound['tracked_paths']) | {p for p, state in bound['files'].items()
                                              if state['state'] == 'file'}
    for path in result['read_paths']:
        if text(path) and path.startswith('base:'):
            if relative(path[5:]) not in bound['base_paths']:
                raise ValueError('review read an unbound baseline path: ' + path)
        elif (not text(path) or relative(path) not in permitted
              or file_state(Path(bound['project']), path)['state'] != 'file'):
            raise ValueError('review read an unbound path; add --path and redispatch: ' + str(path))
    for key in ('gaps', 'checks_not_run'):
        if any(not text(v) for v in result[key]):
            raise ValueError('empty review gap/check')
    if result['status'] in ('blocked', 'failed') and not result['gaps']:
        raise ValueError('blocked/failed review must explain its gap')
    for finding in result['findings']:
        if not isinstance(finding, dict) or not text(finding.get('claim')):
            raise ValueError('finding claim required')
        refs = finding.get('evidence')
        if not isinstance(refs, list) or not refs:
            raise ValueError('finding requires file evidence; uncertainty belongs in gaps')
        for ref in refs:
            if (not isinstance(ref, dict) or ref.get('path') not in result['read_paths']
                    or not text(ref.get('locator')) or not text(ref.get('observation'))):
                raise ValueError('finding evidence needs a read path, locator and observation')


def check(root, feature_id, snapshot, result):
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get('inputs'), dict):
        raise ValueError('invalid snapshot')
    old = snapshot['inputs']
    if snapshot.get('input_digest') != digest(old):
        raise ValueError('snapshot digest mismatch')
    if old.get('schema_version') != 1 or old.get('project') != str(root) or old.get('feature_id') != feature_id:
        raise ValueError('snapshot project/feature/schema mismatch')
    current = capture(root, feature_id, old['base_revision'], old['extra_paths'])
    if current != snapshot:
        raise ValueError('review inputs stale; preserve result and redispatch with current inputs')
    if result is not None:
        validate_result(result, snapshot)
    return {'status': 'VERIFY_REVIEW_RETURN_CURRENT' if result is not None else 'VERIFY_HANDOFF_CURRENT',
            'input_digest': snapshot['input_digest'],
            'review_status': result['status'] if result is not None else None,
            'note': 'Input/return contract only; router must validate findings and existing delivery gates.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('capture', 'check'):
        p = sub.add_parser(name)
        p.add_argument('project', type=Path)
        p.add_argument('feature_id')
        if name == 'capture':
            p.add_argument('--base', required=True, help='Reviewed pre-change Git revision')
            p.add_argument('--path', action='append', default=[], help='Additional ignored evidence file')
        else:
            p.add_argument('--snapshot', type=Path, required=True)
            p.add_argument('--result', type=Path)
    args = parser.parse_args()
    try:
        root = args.project.resolve()
        if args.command == 'capture':
            output = capture(root, args.feature_id, args.base, args.path)
        else:
            output = check(root, args.feature_id, json.loads(args.snapshot.read_text()),
                           json.loads(args.result.read_text()) if args.result else None)
        print(json.dumps(output, ensure_ascii=True, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError, AttributeError, subprocess.CalledProcessError) as exc:
        print('VERIFY_HANDOFF_ERROR: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
