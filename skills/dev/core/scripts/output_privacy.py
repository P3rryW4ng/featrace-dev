#!/usr/bin/env python3
"""Read-only, explicit output privacy checks; no redaction or safety certification."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

MAX_BYTES = 16 * 1024 * 1024  # Maximum logical line; not maximum file size.
MAX_STREAM_BYTES = 256 * 1024 * 1024
SCAN_BLOCK_CHARS = 256 * 1024
MAX_FINDINGS = 100
KINDS = {'account_identifier', 'credential', 'device_identifier', 'contact'}
LABEL = re.compile(r'''(?i)\b(?P<key>user[_-]?id|uid|account[_-]?id|device[_-]?(?:id|serial)|serial[_-]?(?:number|no)|access[_-]?token|refresh[_-]?token|api[_-]?key|client[_-]?secret|authorization|email|phone)[\\"'` \t]*[:=：][\\"'` \t]*(?P<value>[^\s,;\]}"'`\\]+)''')
PATTERNS = [
    ('bearer_candidate', re.compile(r'(?i)\bbearer[ \t]+(?P<value>[A-Za-z0-9][A-Za-z0-9._~+/=-]{7,})')),
    ('credential_candidate', re.compile(r'\b(?:sk-|gh[pousr]_|github_pat_)[A-Za-z0-9_-]{20,}\b')),
    ('jwt_candidate', re.compile(r'\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b')),
    ('private_key_candidate', re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
]


class ScanError(ValueError):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ScanError('invalid_arguments')  # Never echo a secret-bearing argument.


def git(root, *args, required=True):
    options = [] if args and args[0] == 'check-ignore' else ['--literal-pathspecs']
    p = subprocess.run(['git', *options, '-C', str(root), *args], capture_output=True,
                       env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})
    if required and p.returncode:
        raise ScanError('git_input_unavailable')
    return p


def path_at(root, name):
    p = Path(name)
    if not name or p.is_absolute() or any(x in {'.', '..'} for x in p.parts):
        raise ScanError('unsafe_path')
    target = root
    for part in p.parts:
        target = target / part
        if target.is_symlink():
            raise ScanError('unsafe_path')
    if not target.resolve().is_relative_to(root):
        raise ScanError('unsafe_path')
    return target


def raw_file(path, limit=MAX_BYTES):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(fd, 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ScanError('not_regular_file')
            data = stream.read(limit + 1)
    except OSError:
        raise ScanError('file_unavailable') from None
    if len(data) > limit:
        raise ScanError('input_too_large')
    return data


def text(data):
    if b'\x00' in data:
        raise ScanError('binary_or_encoding_unavailable')
    try:
        return data.decode('utf-8-sig')
    except UnicodeError:
        raise ScanError('binary_or_encoding_unavailable') from None


def known_values(root, name):
    if name is None:
        return [], None
    path = path_at(root, name)
    repo = git(root, 'rev-parse', '--show-toplevel', required=False)
    if repo.returncode == 0 and git(root, 'check-ignore', '--', str(path), required=False).returncode:
        raise ScanError('known_values_must_be_ignored')
    data = raw_file(path, 64 * 1024)
    try:
        d = json.loads(text(data))
        if not isinstance(d, dict) or set(d) != {'values'} or not isinstance(d['values'], list) or len(d['values']) > 128:
            raise ScanError('invalid_known_values')
        rows = []
        for row in d['values']:
            if (not isinstance(row, dict) or set(row) != {'kind', 'value'} or row['kind'] not in KINDS
                    or not isinstance(row['value'], str) or not row['value'] or len(row['value']) > 4096):
                raise ScanError('invalid_known_values')
            rows.append((row['kind'], row['value']))
        return rows, data
    except (ValueError, TypeError, KeyError):
        raise ScanError('invalid_known_values') from None


def stream_lines(stream, state, key, *, line_limit=MAX_BYTES):
    """Validate all UTF-8 bytes; bound a logical line and each input stream."""
    sha = hashlib.sha256(); size = 0; first = True
    while True:
        data = stream.readline(line_limit + 1)
        if not data:
            break
        size += len(data)
        if len(data) > line_limit or size > MAX_STREAM_BYTES:
            raise ScanError('input_too_large')
        sha.update(data)
        if b'\x00' in data:
            raise ScanError('binary_or_encoding_unavailable')
        try:
            value = data.decode('utf-8-sig' if first else 'utf-8')
        except UnicodeError:
            raise ScanError('binary_or_encoding_unavailable') from None
        first = False
        yield value
    state[key] = {'sha256': sha.hexdigest(), 'bytes': size}


def git_lines(root, state, key, *args, line_limit=MAX_BYTES):
    """Never retain full Git output, launch diff drivers, or echo stderr."""
    try:
        proc = subprocess.Popen(['git', '--literal-pathspecs', '-C', str(root), *args],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})
    except OSError:
        raise ScanError('git_input_unavailable') from None
    try:
        yield from stream_lines(proc.stdout, state, key, line_limit=line_limit)
        if proc.wait(timeout=5):
            raise ScanError('git_input_unavailable')
    except (subprocess.TimeoutExpired, OSError):
        raise ScanError('git_input_unavailable') from None
    finally:
        proc.stdout.close()
        if proc.poll() is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            proc.wait()


def collect(root, name, staged):
    path = path_at(root, name)
    state = {}
    if not staged:
        def file_parts():
            try:
                fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, 'O_NOFOLLOW', 0))
            except OSError:
                raise ScanError('file_unavailable') from None
            with os.fdopen(fd, 'rb') as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise ScanError('not_regular_file')
                try:
                    for number, value in enumerate(stream_lines(stream, state, 'file'), 1):
                        yield number, value
                except OSError:
                    raise ScanError('file_unavailable') from None
        return state, file_parts(), 'file_text'
    actual = git(root, 'rev-parse', '--show-toplevel').stdout.decode().strip()
    if Path(actual).resolve() != root:
        raise ScanError('staged_requires_git_root')
    entry = git(root, 'ls-files', '--stage', '-z', '--', name).stdout
    head = git(root, 'rev-parse', '--verify', 'HEAD', required=False)
    old = git(root, 'rev-parse', '--verify', 'HEAD:' + name, required=False)
    state.update(index=hashlib.sha256(entry).hexdigest(), head=head.stdout.hex(), old=old.stdout.hex())
    if not entry:
        if old.returncode == 0:
            return state, iter(()), 'staged_deletion'
        raise ScanError('target_not_staged')
    rows = [x.split(b'\t', 1)[0].split() for x in entry.split(b'\x00') if x]
    if len(rows) != 1 or len(rows[0]) != 3 or rows[0][2] != b'0' or rows[0][0] not in {b'100644', b'100755'}:
        raise ScanError('unsafe_or_unmerged_index')
    new_oid = rows[0][1].decode(); old_oid = old.stdout.decode().strip() if old.returncode == 0 else None
    def staged_parts():
        for _ in git_lines(root, state, 'new_blob', 'cat-file', 'blob', new_oid):
            pass
        if old_oid:
            for _ in git_lines(root, state, 'old_blob', 'cat-file', 'blob', old_oid):
                pass
        cursor = None; pending = None; had_hunk = False
        for line in git_lines(root, state, 'diff', 'diff', '--cached', '--no-ext-diff', '--no-textconv',
                              '--no-color', '--no-renames', '--text', '--inter-hunk-context=0', '--unified=0',
                              '--', name, line_limit=MAX_BYTES + 65536):
            # Delay one addition to remove Git's synthetic LF on a non-LF final line.
            if line.startswith('\\ No newline at end of file'):
                if pending:
                    yield pending[0], pending[1][:-1] if pending[1].endswith('\n') else pending[1]
                    pending = None
                continue
            if pending:
                yield pending
                pending = None
            hunk = re.match(r'^@@ -[0-9]+(?:,[0-9]+)? \+([0-9]+)(?:,[0-9]+)? @@', line)
            if hunk:
                cursor = int(hunk[1]); had_hunk = True
            elif cursor is not None and line.startswith('+'):
                pending = (cursor, line[1:]); cursor += 1
            elif cursor is not None and line.startswith(' '):
                cursor += 1
        if pending:
            yield pending
        old_hash = state.get('old_blob', {}).get('sha256', hashlib.sha256(b'').hexdigest())
        if state['new_blob']['sha256'] != old_hash and not had_hunk:
            raise ScanError('staged_diff_unavailable')
    return state, staged_parts(), 'staged_additions'


def blocks(parts):
    """Group complete contiguous lines: regex tokens never split at a block edge."""
    values = []; size = 0; first = None; next_line = None
    for number, value in parts:
        if values and (number != next_line or size + len(value) > SCAN_BLOCK_CHARS):
            yield first, ''.join(values)
            values = []; size = 0
        if not values:
            first = number
        values.append(value); size += len(value); next_line = number + value.count('\n')
    if values:
        yield first, ''.join(values)


def position(value, offset, first, column=1):
    last = value.rfind('\n', 0, offset)
    return first + value.count('\n', 0, offset), offset - last if last >= 0 else column + offset


def placeholder(value):
    v = value.strip().lower()
    return (v in {'null', 'none', 'undefined', 'true', 'false', 'redacted', 'masked', 'bearer', '[', '{'}
            or v.startswith(('<', '[redacted', '{{')) or bool(re.fullmatch(r'[*x•]+', v)))


def matches(value, known):
    for kind, secret in known:
        variants = {secret, json.dumps(secret, ensure_ascii=True)[1:-1], json.dumps(secret, ensure_ascii=False)[1:-1]}
        for variant in sorted(variants):
            for m in re.finditer(re.escape(variant), value):
                yield m.start(), 'known_' + kind, 'known_value'
    for m in LABEL.finditer(value):
        if placeholder(m['value']):
            continue
        key = m['key'].lower().replace('_', '').replace('-', '')
        kind = 'credential_candidate' if key in {'accesstoken', 'refreshtoken', 'apikey', 'clientsecret', 'authorization'} else 'identifier_candidate'
        yield m.start('value'), kind, 'candidate'
    for kind, pattern in PATTERNS:
        for m in pattern.finditer(value):
            if 'value' in m.groupdict() and placeholder(m['value']):
                continue
            yield m.start('value') if 'value' in m.groupdict() else m.start(), kind, 'candidate'


def scan(root, files, *, staged=False, known_name=None):
    root = Path(root).resolve(strict=True)
    if not root.is_dir() or not files or len(files) > 64 or len(files) != len(set(files)):
        raise ScanError('invalid_targets')
    known, known_bytes = known_values(root, known_name)
    variants = [(kind, variant) for kind, secret in known for variant in sorted({
        secret, json.dumps(secret, ensure_ascii=True)[1:-1], json.dumps(secret, ensure_ascii=False)[1:-1]})]
    overlap = max([len(v) for _, v in variants] or [0])
    results, findings, snapshots = [], [], []
    for number, name in enumerate(files, 1):
        parts = None
        try:
            source, parts, scope = collect(root, name, staged)
            seen = set(); truncated = False; tail = ''; tail_line = 1; tail_column = 1; next_line = None
            for first_line, value in blocks(parts):
                if truncated:
                    continue  # Still consume/hash/validate every input byte.
                if first_line != next_line:
                    tail = ''; tail_line = first_line; tail_column = 1
                combined = tail + value
                def candidates():
                    for kind, variant in variants:
                        for match in re.finditer(re.escape(variant), combined):
                            if match.end() > len(tail):
                                yield (position(combined, match.start(), tail_line, tail_column),
                                       'known_' + kind, 'known_value')
                    for offset, kind, confidence in matches(value, []):
                        yield position(value, offset, first_line), kind, confidence
                # Keep candidate iteration lazy even on a dense, very long line.
                for (line, column), kind, confidence in candidates():
                    item = (line, column, kind)
                    if item in seen:
                        continue
                    if len(seen) >= MAX_FINDINGS:
                        truncated = True; break
                    seen.add(item)
                    findings.append({'target': number, 'line': line, 'column': column, 'kind': kind, 'confidence': confidence})
                if overlap:
                    cut = max(0, len(combined) - overlap)
                    tail_line, tail_column = position(combined, cut, tail_line, tail_column)
                    tail = combined[cut:]
                else:
                    tail = ''; tail_line = first_line + value.count('\n'); tail_column = 1
                next_line = first_line + value.count('\n')
            snapshots.append((name, source))
            results.append({'target': number, 'status': 'scanned', 'scope': scope, 'findings': len(seen), 'positions_truncated': truncated})
        except ScanError as exc:
            results.append({'target': number, 'status': 'unavailable', 'reason': str(exc)})
        finally:
            if hasattr(parts, 'close'):
                parts.close()
    # Re-read exact sources/index/HEAD, comparing summaries rather than retaining raw copies.
    for name, before in snapshots:
        parts = None
        try:
            after, parts, _ = collect(root, name, staged)
            for _ in parts:
                pass
            if after != before:
                raise ScanError('input_changed')
        except ScanError:
            return {'status': 'unavailable', 'reason': 'input_changed', 'targets': results, 'findings': findings}, 2
        finally:
            if hasattr(parts, 'close'):
                parts.close()
    if known_name is not None and raw_file(path_at(root, known_name), 64 * 1024) != known_bytes:
        raise ScanError('known_values_changed')
    unavailable = any(x['status'] == 'unavailable' for x in results)
    status = 'unavailable' if unavailable else ('review_needed' if findings else 'no_matches')
    report = {'status': status, 'targets': results, 'findings': findings,
              'note': 'Target numbers follow --file order. Positions only; values, paths and context are omitted. No matches is not privacy approval; patterns/known values are bounded. No files were redacted or rewritten.'}
    return report, 2 if unavailable else (1 if findings else 0)


def main():
    try:
        p = Parser(description=__doc__); p.add_argument('root', type=Path)
        p.add_argument('--file', action='append', required=True); p.add_argument('--staged', action='store_true')
        p.add_argument('--known-values')
        a = p.parse_args()
        result, code = scan(a.root, a.file, staged=a.staged, known_name=a.known_values)
    except ScanError as exc:
        result, code = {'status': 'unavailable', 'reason': str(exc), 'findings': []}, 2
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        result, code = {'status': 'unavailable', 'reason': 'invalid_or_unreadable_input', 'findings': []}, 2
    print(json.dumps(result, ensure_ascii=False, indent=2)); return code


if __name__ == '__main__': sys.exit(main())
