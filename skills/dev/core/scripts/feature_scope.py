#!/usr/bin/env python3
"""Record and validate a feature capability with evidence-backed module roles."""
import argparse
import json
import os
from pathlib import Path
import re
import tempfile

from feature_lifecycle import read_record
from module_context import catalog, render_graph


ROLES = {'owner', 'host', 'provider', 'consumer', 'shared'}
CAPABILITY_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*')


def _text(value, label):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(label + ' must be non-empty trimmed text')
    return value


def validate_scope(root, feature, stage='draft'):
    """Return validation errors; workflow v1/v2 records remain compatible."""
    version = feature.get('workflow_version', 1)
    if not isinstance(version, int) or isinstance(version, bool):
        return ['workflow_version must be a positive integer']
    scope = feature.get('module_scope')
    if version < 3 and scope is None:
        return []
    try:
        if not isinstance(scope, dict):
            raise ValueError('feature.module_scope must be an object')
        status = scope.get('status')
        if status not in {'pending', 'confirmed', 'not_applicable'}:
            raise ValueError('module_scope.status must be pending, confirmed or not_applicable')
        if status == 'pending':
            if stage != 'draft':
                raise ValueError('feature capability and module roles need confirmation before development')
            return []
        if status == 'not_applicable':
            _text(scope.get('note'), 'module_scope.note')
            if scope.get('assignments') not in (None, []):
                raise ValueError('not_applicable module scope cannot contain assignments')
            if feature.get('modules', []) or feature.get('module_context_required') is not False:
                raise ValueError('not_applicable module scope requires empty modules and module_context_required=false')
            return []
        capability = scope.get('capability')
        if not isinstance(capability, dict):
            raise ValueError('confirmed module scope requires capability')
        cid = _text(capability.get('id'), 'capability.id')
        if not CAPABILITY_ID.fullmatch(cid):
            raise ValueError('capability.id must use letters, digits, underscore or hyphen')
        _text(capability.get('name'), 'capability.name')
        assignments = scope.get('assignments')
        if not isinstance(assignments, list) or not assignments:
            raise ValueError('confirmed module scope requires assignments')
        index = catalog(root)
        known = {row['id'] for row in index['modules']}
        seen = set()
        for row in assignments:
            if not isinstance(row, dict):
                raise ValueError('module assignment must be an object')
            mid = _text(row.get('module_id'), 'module assignment module_id')
            if mid not in known:
                raise ValueError('unknown assigned module: ' + mid)
            if mid in seen:
                raise ValueError('duplicate module assignment: ' + mid)
            seen.add(mid)
            if row.get('role') not in ROLES:
                raise ValueError('invalid module role for ' + mid)
            _text(row.get('responsibility'), 'module responsibility')
            refs = row.get('evidence_refs')
            if (not isinstance(refs, list) or not refs or
                    any(not isinstance(ref, str) or not ref.strip() for ref in refs) or
                    len(set(refs)) != len(refs)):
                raise ValueError('module assignment evidence_refs must be unique non-empty text')
        if feature.get('modules') != [row['module_id'] for row in assignments]:
            raise ValueError('feature.modules must match module_scope assignments in order')
        if feature.get('module_context_required') is not True:
            raise ValueError('confirmed module scope requires module_context_required=true')
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        return [str(exc)]
    return []


def replace(path, original, doc):
    temp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            temp = Path(stream.name)
            json.dump(doc, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        if path.read_bytes() != original:
            raise ValueError('feature changed during scope update; retry after reviewing current records')
        os.replace(temp, path)
    finally:
        if temp and temp.exists():
            temp.unlink()


def set_scope(root, feature_id, supplied):
    path, original, doc = read_record(root, feature_id)
    feature = doc['feature']
    feature['workflow_version'] = max(feature.get('workflow_version', 1), 3)
    scope = {'status': 'confirmed', 'capability': supplied.get('capability'),
             'assignments': supplied.get('assignments'), 'note': supplied.get('note', '')}
    feature['module_scope'] = scope
    feature['modules'] = [row.get('module_id') for row in scope['assignments']] if isinstance(scope['assignments'], list) else []
    feature['module_context_required'] = True
    feature.pop('module_context_note', None)
    errors = validate_scope(root, feature, 'develop')
    if errors:
        raise ValueError('; '.join(errors))
    replace(path, original, doc)
    render_graph(root)
    return scope


def not_applicable(root, feature_id, reason):
    path, original, doc = read_record(root, feature_id)
    feature = doc['feature']
    feature['workflow_version'] = max(feature.get('workflow_version', 1), 3)
    note = _text(reason, 'reason')
    feature['module_scope'] = {'status': 'not_applicable', 'capability': None, 'assignments': [], 'note': note}
    feature['modules'] = []
    feature['module_context_required'] = False
    feature['module_context_note'] = note
    errors = validate_scope(root, feature, 'develop')
    if errors:
        raise ValueError('; '.join(errors))
    replace(path, original, doc)
    if (root / '.agent-workflow/modules/index.json').exists():
        render_graph(root)
    return feature['module_scope']


def clear(root, feature_id):
    path, original, doc = read_record(root, feature_id)
    feature = doc['feature']
    feature['workflow_version'] = max(feature.get('workflow_version', 1), 3)
    feature['module_scope'] = {'status': 'pending', 'capability': None, 'assignments': [], 'note': ''}
    feature['modules'] = []
    feature.pop('module_context_required', None)
    feature.pop('module_context_note', None)
    replace(path, original, doc)
    if (root / '.agent-workflow/modules/index.json').exists():
        render_graph(root)
    return feature['module_scope']


def suggest(root, feature_id):
    _, _, doc = read_record(root, feature_id)
    index = catalog(root)
    trace_path = root / '.agent-workflow/features' / feature_id / 'traceability.json'
    trace = json.loads(trace_path.read_text()) if trace_path.exists() else {'links': []}
    code = sorted({path for link in trace.get('links', []) if isinstance(link, dict)
                   for path in link.get('code', []) if isinstance(path, str)})
    rows = []
    for module in index['modules']:
        matched = sorted(path for path in code if any(path == base or path.startswith(base.rstrip('/') + '/') for base in module['roots']))
        rows.append({'module_id': module['id'], 'summary': module['summary'], 'matched_code_paths': matched,
                     'depends_on': module['depends_on']})
    return {'feature_id': feature_id, 'candidates': rows,
            'note': 'Path matches are candidates only; Agent must inspect behavior and ask the user to confirm ambiguous business ownership.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('suggest', 'set', 'not-applicable', 'clear'))
    parser.add_argument('project', type=Path)
    parser.add_argument('feature_id')
    parser.add_argument('--input', type=Path)
    parser.add_argument('--reason', default='')
    args = parser.parse_args()
    root = args.project.resolve()
    try:
        if args.action == 'suggest':
            result = suggest(root, args.feature_id)
        elif args.action == 'set':
            if not args.input:
                raise ValueError('set requires --input')
            result = set_scope(root, args.feature_id, json.loads(args.input.read_text()))
        elif args.action == 'not-applicable':
            result = not_applicable(root, args.feature_id, args.reason)
        else:
            result = clear(root, args.feature_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(1, 'FEATURE_SCOPE_ERROR: ' + str(exc) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
