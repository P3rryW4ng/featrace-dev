"""Read-only identity of local automatic-check inputs, not semantic coverage."""
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess


SCOPE = 'git-business-worktree-and-declared-inputs'


def workflow(name):
    return name == '.agent-workflow' or name.startswith('.agent-workflow/')


def git(root, *args):
    run = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                         env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})
    if run.returncode:
        raise ValueError('Git input identity unavailable')
    return run.stdout


def path_state(root, name):
    rel = Path(name)
    if not name or rel.is_absolute() or '..' in rel.parts or '.git' in rel.parts or rel.as_posix() != name:
        raise ValueError('unsafe declared check input')
    path = root
    for part in rel.parts:
        path /= part
        if path.is_symlink():
            raise ValueError('symlink check input: ' + name)
    if not path.exists():
        return {'state': 'missing'}
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError('non-regular check input: ' + name)
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_mode) != (
            after.st_ino, after.st_size, after.st_mtime_ns, after.st_mode):
        raise ValueError('check input moved during reading: ' + name)
    return {'state': 'file', 'sha256': h.hexdigest(), 'executable': bool(after.st_mode & 0o111)}


def collect(root, required, optional):
    root = Path(root).resolve()
    if Path(os.fsdecode(git(root, 'rev-parse', '--show-toplevel')).strip()).resolve() != root:
        raise ValueError('check identity requires the Git root')
    head = git(root, 'rev-parse', '--verify', 'HEAD^{commit}').decode().strip()
    committed, index = {}, {}
    for row in git(root, 'ls-tree', '-r', '-z', head).split(b'\0'):
        if not row:
            continue
        meta, raw = row.split(b'\t', 1)
        mode, kind, oid = meta.decode().split()
        name = os.fsdecode(raw)
        if workflow(name):
            continue
        if mode not in ('100644', '100755', '120000') or kind != 'blob':
            raise ValueError('unsupported committed input: ' + name)
        committed[name] = {'mode': mode, 'oid': oid}
    for row in git(root, 'ls-files', '--stage', '-z').split(b'\0'):
        if not row:
            continue
        meta, raw = row.split(b'\t', 1)
        mode, oid, stage = meta.decode().split()
        name = os.fsdecode(raw)
        if workflow(name):
            continue
        if stage != '0' or mode not in ('100644', '100755', '120000'):
            raise ValueError('unmerged/unsupported index input: ' + name)
        index[name] = {'mode': mode, 'oid': oid}
    untracked = {os.fsdecode(n) for n in git(root, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0')
                 if n and not workflow(os.fsdecode(n))}
    # Read actual bytes even for assume-unchanged entries. Git's clean flags are
    # not evidence that a compiler saw the committed contents.
    from managed_links import inspect
    links, member_files = inspect(root, committed, index)
    files = {}
    for name in sorted(set(committed) | set(index) | untracked):
        files[name] = links[name] if name in links else member_files[name] if name in member_files else path_state(root, name)
    declared = {}
    for name in sorted(set(required) | set(optional)):
        declared[name] = path_state(root, name)
        if name in required and declared[name]['state'] != 'file':
            raise ValueError('required check input missing: ' + name)
    return {'schema_version': 2 if links else 1, 'scope': SCOPE, 'state': 'identified', 'project': str(root),
            'head': head, 'committed': committed, 'index': index, 'files': files, 'declared': declared}


def capture(root, required=(), optional=()):
    """Unknown is explicit; failed Git/filesystem reads never mean unchanged."""
    try:
        first = collect(root, required, optional)
        if first != collect(root, required, optional):
            raise ValueError('check inputs changed during capture')
        return first
    except (OSError, ValueError, TypeError) as exc:
        return {'schema_version': 1, 'scope': SCOPE, 'state': 'unknown', 'reason': str(exc)}


def valid(value):
    keys = {'schema_version', 'scope', 'state', 'project', 'head', 'committed', 'index', 'files', 'declared'}
    shape = (isinstance(value, dict) and set(value) == keys and type(value['schema_version']) is int and value['schema_version'] in (1, 2)
            and value['scope'] == SCOPE and value['state'] == 'identified'
            and isinstance(value['project'], str) and bool(value['project'])
            and isinstance(value['head'], str) and re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}', value['head'])
            and all(isinstance(value[k], dict) for k in ('committed', 'index', 'files', 'declared')))
    if not shape:
        return False
    for key in ('committed', 'index', 'files', 'declared'):
        for name, entry in value[key].items():
            if not isinstance(name, str) or not name or not isinstance(entry, dict):
                return False
            path = Path(name)
            if path.is_absolute() or '..' in path.parts or '.git' in path.parts or path.as_posix() != name:
                return False
            if key in ('committed', 'index'):
                if (set(entry) != {'mode', 'oid'} or entry['mode'] not in (('100644', '100755', '120000') if value['schema_version'] == 2 else ('100644', '100755'))
                        or not isinstance(entry['oid'], str) or not re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}', entry['oid'])):
                    return False
            elif key == 'files' and entry.get('state') == 'managed_directory_link':
                if not valid_link(value, name, entry): return False
            elif entry != {'state': 'missing'}:
                if (set(entry) != {'state', 'sha256', 'executable'} or entry['state'] != 'file'
                        or type(entry['executable']) is not bool or not isinstance(entry['sha256'], str)
                        or not re.fullmatch('[0-9a-f]{64}', entry['sha256'])):
                    return False
    links = {n for n, e in value['files'].items() if e.get('state') == 'managed_directory_link'}
    tracked_links = {n for k in ('committed', 'index') for n, e in value[k].items() if e['mode'] == '120000'}
    if links != tracked_links or (value['schema_version'] == 2 and not links): return False
    return True


def valid_link(value, name, entry):
    from managed_links import target_path, blob_id
    if (value['schema_version'] != 2 or set(entry) != {'state', 'sha256', 'target', 'target_path', 'members'}
            or not isinstance(entry['target'], str) or not isinstance(entry['sha256'], str)
            or not isinstance(entry['target_path'], str) or not isinstance(entry['members'], list)
            or not entry['members'] or not all(isinstance(n, str) for n in entry['members'])
            or entry['members'] != sorted(set(entry['members']))):
        return False
    tracked = value['committed'].get(name)
    if not tracked or tracked.get('mode') != '120000' or tracked != value['index'].get(name): return False
    try:
        raw = os.fsencode(entry['target'])
        if (target_path(name, entry['target']) != entry['target_path']
                or hashlib.sha256(raw).hexdigest() != entry['sha256']
                or blob_id(raw, tracked['oid']) != tracked['oid']): return False
    except (ValueError, TypeError, UnicodeError): return False
    prefix = entry['target_path'] + '/'
    expected = {n for n in value['committed'] if n.startswith(prefix)}
    if set(entry['members']) != expected or expected != {n for n in value['index'] if n.startswith(prefix)}: return False
    for member in expected:
        if (value['committed'][member].get('mode') not in ('100644', '100755')
                or value['index'][member].get('mode') not in ('100644', '100755')
                or not isinstance(value['files'].get(member), dict)
                or value['files'][member].get('state') != 'file'): return False
    return True


def compare(before, after):
    if not valid(before) or not valid(after):
        return {'state': 'unknown', 'scope': SCOPE,
                'reason': 'missing, unsupported or unavailable check identity', 'changes': {}}
    changes = {}
    if before['project'] != after['project']:
        changes['project'] = ['workspace root differs']
    for key in ('committed', 'index', 'files', 'declared'):
        names = sorted(n for n in set(before[key]) | set(after[key]) if before[key].get(n) != after[key].get(n))
        if names:
            changes[key] = names
    # HEAD is provenance, not a substitute for content: workflow-only commits
    # may advance it without changing these local execution inputs.
    return {'state': 'changed' if changes else 'same', 'scope': SCOPE, 'changes': changes}
