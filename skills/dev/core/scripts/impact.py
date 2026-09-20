#!/usr/bin/env python3
"""Inspect declared local change scope; never infer business correctness."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

MECHANISMS = ('entry_points', 'callers', 'shared_state', 'navigation', 'lifecycle', 'legacy_behavior')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def git(root, *args):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True)
    if result.returncode:
        raise ValueError('cannot inspect Git scope: ' + result.stderr.decode(errors='replace').strip())
    return result.stdout


def path_name(value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('impact paths must be explicit relative file paths')
    p = Path(value)
    if p.is_absolute() or '..' in p.parts or p.as_posix() != value or value == '.':
        raise ValueError('invalid impact path: ' + value)
    if p.parts[0] in ('.git', '.agent-workflow'):
        raise ValueError('impact scope must reference project files, not workflow records')
    return value


def snapshot(root, record):
    root = root.resolve()
    if Path(git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != root:
        raise ValueError('impact requires the Git project root')
    base = record.get('base_revision', '')
    if not isinstance(base, str) or len(base) not in (40, 64) or any(c not in '0123456789abcdef' for c in base):
        raise ValueError('base_revision must be a full immutable commit hash')
    git(root, 'rev-parse', '--verify', base + '^{commit}')
    git(root, 'merge-base', '--is-ancestor', base, 'HEAD')
    changed = set(git(root, 'diff', '--name-only', '--no-renames', '-z', base, '--').decode().split('\0'))
    changed.update(git(root, 'ls-files', '--others', '--exclude-standard', '-z').decode().split('\0'))
    changed = sorted(p for p in changed if p and not p.startswith('.agent-workflow/'))
    paths = sorted(set(changed) | set(record['inspected_paths']))
    files = {}
    for name in paths:
        path_name(name)
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('symlink/outside path needs manual handling: ' + name)
        if path.exists() and not path.is_file():
            raise ValueError('directory/submodule needs manual handling: ' + name)
        files[name] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'executable': bool(path.stat().st_mode & 0o111)} if path.exists() else None
    # Include the declared contract, excluding results; edits to boundaries invalidate evidence.
    contract = {k: v for k, v in record.items() if k != 'behaviors'}
    contract['behaviors'] = [{k: v for k, v in b.items() if k != 'verification'} for b in record['behaviors']]
    return {'changed_paths': changed, 'digest': digest({'base': base, 'files': files, 'contract': contract})}


def validate_impact(root, folder, req, stage):
    errors, warnings = [], []
    path = folder / 'impact.json'
    required = req.get('feature', {}).get('impact_required', False)
    if not isinstance(required, bool):
        return ['feature.impact_required must be boolean'], []
    if not path.exists():
        message = 'impact checklist missing; register it before new business-code edits'
        (errors if required and stage != 'draft' else warnings).append(message)
        return errors, warnings
    try:
        doc = json.loads(path.read_text())
        def need(condition, message):
            if not condition:
                raise ValueError(message)
        def text(value):
            return isinstance(value, str) and bool(value.strip())
        need(isinstance(doc, dict) and doc.get('schema_version') == 1 and doc.get('feature_id') == folder.name, 'impact identity/schema mismatch')
        for field in ('allowed_paths', 'inspected_paths'):
            values = doc.get(field)
            need(isinstance(values, list) and values and all(isinstance(p, str) for p in values), field + ' must contain explicit files')
            need(len(values) == len(set(values)), field + ' has duplicates')
            for p in values:
                path_name(p)
        excluded = doc.get('excluded_changes', {})
        need(isinstance(excluded, dict), 'excluded_changes must map unrelated paths to reasons')
        for p, reason in excluded.items():
            path_name(p); need(text(reason), 'excluded change needs a reason')
        need(not set(excluded) & set(doc['allowed_paths']), 'excluded and allowed scope overlap')
        mechanisms = doc.get('mechanisms', {})
        need(isinstance(mechanisms, dict), 'mechanisms must be an object')
        for key in MECHANISMS:
            item = mechanisms.get(key, {})
            need(isinstance(item, dict) and item.get('status') in ('reviewed', 'not_applicable', 'unknown') and text(item.get('evidence')), key + ' needs status and evidence/reason')
            if item['status'] == 'unknown' and stage != 'draft':
                errors.append('unresolved impact mechanism: ' + key)
        behaviors = doc.get('behaviors')
        need(isinstance(behaviors, list) and behaviors, 'impact behaviors must not be empty')
        known = {r['id'] for r in req.get('requirements', [])}
        ids = set()
        for b in behaviors:
            need(isinstance(b, dict) and text(b.get('id')) and b['id'] not in ids, 'invalid/duplicate behavior id')
            ids.add(b['id'])
            need(b.get('kind') in ('change', 'preserve', 'unknown') and text(b.get('statement')) and text(b.get('basis')), 'behavior needs kind, statement and basis')
            refs = b.get('requirement_ids')
            need(isinstance(refs, list) and refs and all(isinstance(r, str) and r in known for r in refs), 'behavior requires known requirement_ids')
            if b['kind'] == 'unknown' and stage != 'draft':
                errors.append('unresolved impact behavior: ' + b['id'])
        current = snapshot(root, doc)
        if stage == 'check':
            outside = set(current['changed_paths']) - set(doc['allowed_paths']) - set(excluded)
            if outside:
                errors.append('unreviewed scope expansion: ' + ', '.join(sorted(outside)))
            for b in behaviors:
                result = b.get('verification', {})
                if not isinstance(result, dict) or result.get('status') not in ('passed', 'waived') or not text(result.get('evidence')) or not text(result.get('method')):
                    errors.append('behavior needs actual regression evidence or explicit waiver: ' + b['id'])
                elif result.get('digest') != current['digest']:
                    errors.append('stale impact regression: ' + b['id'])
        return errors, warnings
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return ['invalid impact checklist: ' + str(exc)], warnings


def render_impact(folder):
    path = folder / 'impact.json'
    if path.exists():
        doc = json.loads(path.read_text())
        (folder / 'impact.md').write_text('# Change impact\n\nDeclared investigation and evidence; not automatic impact discovery.\n\n```json\n' + json.dumps(doc, ensure_ascii=False, indent=2) + '\n```\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('feature_id')
    args = parser.parse_args()
    import re
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.feature_id):
        parser.error('invalid feature ID')
    folder = args.root.resolve() / '.agent-workflow/features' / args.feature_id
    try:
        req = json.loads((folder / 'spec/requirements.json').read_text())
        errors, _ = validate_impact(args.root, folder, req, 'develop')
        if errors:
            raise ValueError('; '.join(errors))
        print(json.dumps(snapshot(args.root, json.loads((folder / 'impact.json').read_text())), indent=2))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, 'ERROR: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
