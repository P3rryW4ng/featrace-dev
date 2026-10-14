#!/usr/bin/env python3
"""Read-only, explicit output privacy checks; no redaction or safety certification."""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

MAX_BYTES = 16 * 1024 * 1024
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
    p = subprocess.run(['git', *options, '-C', str(root), *args], capture_output=True)
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


def staged_text(root, name):
    actual = git(root, 'rev-parse', '--show-toplevel').stdout.decode().strip()
    if Path(actual).resolve() != root:
        raise ScanError('staged_requires_git_root')
    entry = git(root, 'ls-files', '--stage', '-z', '--', name).stdout
    if not entry:
        old = git(root, 'cat-file', '-e', 'HEAD:' + name, required=False)
        if old.returncode == 0:
            return b'', [], 'staged_deletion'
        raise ScanError('target_not_staged')
    rows = [x.split(b'\t', 1)[0].split() for x in entry.split(b'\x00') if x]
    if len(rows) != 1 or len(rows[0]) != 3 or rows[0][2] != b'0' or rows[0][0] not in {b'100644', b'100755'}:
        raise ScanError('unsafe_or_unmerged_index')
    new = git(root, 'cat-file', 'blob', rows[0][1].decode()).stdout
    if len(new) > MAX_BYTES:
        raise ScanError('input_too_large')
    new_text = text(new)
    old = git(root, 'show', 'HEAD:' + name, required=False)
    if old.returncode == 0:
        if len(old.stdout) > MAX_BYTES:
            raise ScanError('input_too_large')
        old_text = text(old.stdout)
    else:
        old_text = ''
    # Mirror the exact staged addition ranges; disable external diff/textconv drivers.
    diff = git(root, 'diff', '--cached', '--no-ext-diff', '--no-textconv', '--no-color',
               '--no-renames', '--text', '--inter-hunk-context=0', '--unified=0', '--', name).stdout
    parts = []; first = None; cursor = None; added = []
    # Git uses LF; Unicode separators are file content, not patch delimiters.
    for line in re.findall(r'[^\n]*\n|[^\n]+$', text(diff)):
        hunk = re.match(r'^@@ -[0-9]+(?:,[0-9]+)? \+([0-9]+)(?:,[0-9]+)? @@', line)
        if hunk:
            if added: parts.append((first, ''.join(added)))
            cursor = int(hunk[1]); first = None; added = []
        elif cursor is not None and line.startswith('+'):
            if first is None: first = cursor
            added.append(line[1:]); cursor += 1
        elif cursor is not None and line.startswith(' '):
            if added: parts.append((first, ''.join(added)))
            first = None; added = []; cursor += 1
    if added: parts.append((first, ''.join(added)))
    if new_text != old_text and not re.search(rb'^@@ ', diff, re.MULTILINE):
        raise ScanError('staged_diff_unavailable')
    return entry + b'\x00' + new + b'\x00' + old.stdout + b'\x00' + diff, parts, 'staged_additions'


def collect(root, name, staged):
    path = path_at(root, name)
    if staged:
        return staged_text(root, name)
    data = raw_file(path)
    return data, [(1, text(data))], 'file_text'


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
    results, findings, snapshots = [], [], []
    for number, name in enumerate(files, 1):
        try:
            source, parts, scope = collect(root, name, staged)
            snapshots.append((name, source))
            seen = set(); truncated = False
            for first_line, value in parts:
                for offset, kind, confidence in matches(value, known):
                    line = first_line + value.count('\n', 0, offset)
                    column = offset - value.rfind('\n', 0, offset)
                    item = (line, column, kind)
                    if item in seen:
                        continue
                    if len(seen) >= MAX_FINDINGS:
                        truncated = True; break
                    seen.add(item)
                    findings.append({'target': number, 'line': line, 'column': column, 'kind': kind, 'confidence': confidence})
                if truncated:
                    break
            results.append({'target': number, 'status': 'scanned', 'scope': scope, 'findings': len(seen), 'positions_truncated': truncated})
        except ScanError as exc:
            results.append({'target': number, 'status': 'unavailable', 'reason': str(exc)})
    # Recheck the exact examined artifacts/index/HEAD and local marker input, no writes.
    for name, before in snapshots:
        try:
            if collect(root, name, staged)[0] != before:
                raise ScanError('input_changed')
        except ScanError:
            return {'status': 'unavailable', 'reason': 'input_changed', 'targets': results, 'findings': findings}, 2
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
