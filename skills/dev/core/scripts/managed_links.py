"""Narrow identity for committed relative links to managed in-repository directories.

No directory exclusions, external traversal, link chains or dependency inference.
Descriptor-relative no-follow reads keep a replaced path from redirecting reads.
"""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import stat

REGULAR = ('100644', '100755')


def signature(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def target_path(name, target):
    """Accept leading ../ only; no intermediate traversal/link normalization."""
    if not isinstance(target, str) or not target or os.path.isabs(target):
        raise ValueError('absolute/empty symlink target unsupported: ' + name)
    parts = list(Path(name).parts[:-1])
    descended = False
    for component in target.split('/'):
        if component == '..' and not descended:
            if not parts: raise ValueError('symlink target escapes project: ' + name)
            parts.pop()
        elif component in ('', '.', '..'):
            raise ValueError('complex symlink target unsupported: ' + name)
        else:
            descended = True
            parts.append(component)
    if not parts or any(p in ('.git', '.agent-workflow') for p in parts):
        raise ValueError('symlink control/root target unsupported: ' + name)
    return '/'.join(parts)


def blob_id(data, oid):
    if len(oid) not in (40, 64): raise ValueError('unsupported Git object identity')
    h = hashlib.new('sha1' if len(oid) == 40 else 'sha256')
    h.update(('blob ' + str(len(data)) + '\0').encode()); h.update(data)
    return h.hexdigest()


@contextmanager
def directory(parent, components):
    """Open each component without following links, retain all guards until exit."""
    opened = []
    try:
        fd = parent
        for component in components:
            fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            opened.append((fd, signature(os.fstat(fd))))
        yield fd
        for fd, before in opened:
            if signature(os.fstat(fd)) != before:
                raise ValueError('managed directory changed during capture')
    finally:
        for fd, _ in reversed(opened): os.close(fd)


def read_member(parent, leaf, info, expected, clean):
    fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or signature(before) != signature(info):
            raise ValueError('managed member changed before reading')
        h = hashlib.sha256()
        algorithm = 'sha1' if len(expected['oid']) == 40 else 'sha256'
        git_hash = hashlib.new(algorithm)
        git_hash.update(('blob ' + str(before.st_size) + '\0').encode())
        length = 0
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block: break
            h.update(block); git_hash.update(block); length += len(block)
        after = os.fstat(fd)
        current = os.stat(leaf, dir_fd=parent, follow_symlinks=False)
        if length != before.st_size or signature(before) != signature(after) or signature(after) != signature(current):
            raise ValueError('managed member moved during reading')
        mode = '100755' if after.st_mode & 0o111 else '100644'
        if clean and (mode != expected['mode'] or git_hash.hexdigest() != expected['oid']):
            raise ValueError('actual input differs from committed continuity target')
        return {'state': 'file', 'sha256': h.hexdigest(), 'executable': mode == '100755'}
    finally:
        os.close(fd)


def members(parent, prefix, expected, clean):
    before = signature(os.fstat(parent))
    found = {}
    for leaf in sorted(os.listdir(parent)):
        name = prefix + '/' + leaf
        info = os.stat(leaf, dir_fd=parent, follow_symlinks=False)
        if stat.S_ISLNK(info.st_mode):
            raise ValueError('nested symlink target unsupported: ' + name)
        if stat.S_ISDIR(info.st_mode):
            if not any(p.startswith(name + '/') for p in expected):
                raise ValueError('unmanaged directory in symlink target: ' + name)
            with directory(parent, [leaf]) as child:
                found.update(members(child, name, expected, clean))
        elif stat.S_ISREG(info.st_mode) and name in expected:
            found[name] = read_member(parent, leaf, info, expected[name], clean)
        else:
            raise ValueError('unmanaged/nonregular symlink target member: ' + name)
    if signature(os.fstat(parent)) != before:
        raise ValueError('managed directory membership moved during capture')
    return found


def inspect(root, committed, index, clean=False):
    """Return link identities and already-read member files; both scopes stay bound.

    Link definitions must already agree in HEAD, index and actual filesystem.
    Ordinary target files may be dirty for check identity; continuity requires clean.
    """
    names = sorted(n for n in set(committed) | set(index)
                   if committed.get(n, {}).get('mode') == '120000' or index.get(n, {}).get('mode') == '120000')
    if not names: return {}, {}
    if not hasattr(os, 'O_NOFOLLOW') or not hasattr(os, 'O_DIRECTORY'):
        raise ValueError('managed symlink capture requires no-follow directory reads')
    root_fd = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    links, files = {}, {}
    try:
        for name in names:
            entry = committed.get(name)
            if not entry or entry['mode'] != '120000' or entry != index.get(name):
                raise ValueError('symlink must be committed and unchanged in index: ' + name)
            with directory(root_fd, Path(name).parts[:-1]) as parent:
                leaf = Path(name).name
                before = os.stat(leaf, dir_fd=parent, follow_symlinks=False)
                if not stat.S_ISLNK(before.st_mode):
                    raise ValueError('committed symlink missing/replaced: ' + name)
                target = os.readlink(leaf, dir_fd=parent)
                raw = os.fsencode(target)
                if blob_id(raw, entry['oid']) != entry['oid']:
                    raise ValueError('symlink target differs from committed input: ' + name)
                resolved = target_path(name, target)
                prefix = resolved + '/'
                expected = {n: v for n, v in committed.items() if n.startswith(prefix)}
                indexed = {n: v for n, v in index.items() if n.startswith(prefix)}
                if (not expected or set(expected) != set(indexed)
                        or any(v['mode'] not in REGULAR or indexed[n]['mode'] not in REGULAR
                               for n, v in expected.items())):
                    raise ValueError('symlink input requires a committed managed directory without links/submodules: ' + name)
                with directory(root_fd, Path(resolved).parts) as folder:
                    found = members(folder, resolved, expected, clean)
                if set(found) != set(expected):
                    raise ValueError('managed symlink target members missing: ' + name)
                if (signature(os.stat(leaf, dir_fd=parent, follow_symlinks=False)) != signature(before)
                        or os.readlink(leaf, dir_fd=parent) != target):
                    raise ValueError('symlink moved during capture: ' + name)
                for member, state in found.items():
                    if member in files and files[member] != state:
                        raise ValueError('shared symlink target changed during capture')
                    files[member] = state
                links[name] = {'state': 'managed_directory_link', 'sha256': hashlib.sha256(raw).hexdigest(),
                               'target': target, 'target_path': resolved, 'members': sorted(found)}
        return links, files
    finally:
        os.close(root_fd)
