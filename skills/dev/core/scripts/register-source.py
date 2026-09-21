#!/usr/bin/env python3
"""Register one immutable local evidence file and synchronize source indexes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from prd_intake import source_path

KINDS = ('document', 'html', 'design', 'api')


def read(path):
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(path.name + ' must contain an object')
    return value


def replace(path, content):
    with tempfile.NamedTemporaryFile('wb', dir=path.parent, delete=False) as f:
        f.write(content)
        temp = Path(f.name)
    os.replace(temp, path)


def register(root, feature_id, supplied, kind):
    root = root.resolve(); supplied = supplied.resolve()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', feature_id):
        raise ValueError('invalid feature ID')
    if not supplied.is_file() or supplied.is_symlink():
        raise ValueError('source must be an existing regular file')
    folder = root / '.agent-workflow/features' / feature_id
    if not folder.is_dir() or folder.is_symlink() or not folder.resolve().is_relative_to(root):
        raise ValueError('feature workspace does not exist')
    intake_path = folder / 'spec/prd-intake.json'
    req_path = folder / 'spec/requirements.json'
    intake, req = read(intake_path), read(req_path)
    if intake.get('feature_id') != feature_id or req.get('feature', {}).get('id') != feature_id:
        raise ValueError('feature identity mismatch')
    sources = intake.get('sources')
    if not isinstance(sources, list):
        raise ValueError('intake sources must be an array')
    source_dir = folder / 'sources'
    if source_dir.is_symlink() or not source_dir.is_dir() or source_dir.resolve() != (folder.resolve() / 'sources'):
        raise ValueError('feature source directory is invalid')
    data = supplied.read_bytes(); supplied_digest = hashlib.sha256(data).hexdigest()
    for row in sources:
        if not isinstance(row, dict) or not isinstance(row.get('path'), str):
            raise ValueError('invalid registered source')
        existing = source_path(folder, row['path'])
        if existing.is_file() and hashlib.sha256(existing.read_bytes()).hexdigest() == supplied_digest:
            if row.get('kind') != kind:
                raise ValueError('identical source is already registered with kind ' + str(row.get('kind')))
            return {'status': 'already_registered', 'source': row}
    ids = []
    for row in sources:
        match = re.fullmatch(r'SRC-([0-9]+)', str(row.get('id', '')))
        if not match:
            raise ValueError('registered source ID must use SRC-NN form')
        ids.append(int(match.group(1)))
    number = max(ids, default=0) + 1
    prefix = {'document': 'prd-part', 'html': 'prd-part', 'design': 'design-part', 'api': 'api-part'}[kind]
    suffix = supplied.suffix
    destination = source_dir / (prefix + '-%02d' % number + suffix)
    if destination.exists() or destination.is_symlink():
        raise ValueError('source destination already exists')
    row = {'id': 'SRC-%02d' % number, 'path': 'sources/' + destination.name, 'kind': kind}
    updated_intake = json.loads(json.dumps(intake)); updated_intake['sources'].append(row)
    updated_req = json.loads(json.dumps(req)); feature = updated_req['feature']
    paths = feature.get('prd_paths')
    if not isinstance(paths, list) or any(not isinstance(x, str) or not x for x in paths):
        raise ValueError('feature.prd_paths must be a non-empty string array')
    if row['path'] not in paths:
        paths.append(row['path'])
    if kind == 'design':
        feature.setdefault('source_status', {})['figma'] = 'present'
    elif kind == 'api':
        feature.setdefault('source_status', {})['api'] = 'present'
    intake_before, req_before = intake_path.read_bytes(), req_path.read_bytes()
    try:
        shutil.copyfile(supplied, destination)
        replace(intake_path, (json.dumps(updated_intake, ensure_ascii=False, indent=2) + '\n').encode())
        replace(req_path, (json.dumps(updated_req, ensure_ascii=False, indent=2) + '\n').encode())
    except Exception:
        replace(intake_path, intake_before); replace(req_path, req_before)
        if destination.exists() and not destination.is_symlink():
            destination.unlink()
        raise
    return {'status': 'registered', 'source': row}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('feature_id')
    parser.add_argument('source', type=Path)
    parser.add_argument('--kind', choices=KINDS, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(register(args.root, args.feature_id, args.source, args.kind), ensure_ascii=False))
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(1, 'ERROR: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
