#!/usr/bin/env python3
"""Discover related verified fixes and validate the current feature's regression review."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def text(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value):
    return isinstance(value, list) and all(text(item) for item in value)


def history_ids(history):
    if not isinstance(history, list):
        raise ValueError('history must be an array')
    identifiers = set()
    for entry in history:
        archived_disposition = entry.get('disposition') if isinstance(entry, dict) else None
        identity_payload = copy.deepcopy(entry) if isinstance(entry, dict) else {}
        recorded_id = identity_payload.pop('history_id', None)
        if (not isinstance(entry, dict) or not text(entry.get('history_id'))
                or entry['history_id'] in identifiers
                or recorded_id != digest(identity_payload)
                or entry.get('superseded_reason') not in ('candidate_changed', 'candidate_removed')
                or not text(entry.get('candidate_id'))
                or not text(entry.get('candidate_digest'))
                or not isinstance(entry.get('candidate'), dict)
                or not isinstance(archived_disposition, dict)
                or archived_disposition.get('candidate_id') != entry.get('candidate_id')
                or archived_disposition.get('candidate_digest') != entry.get('candidate_digest')
                or not text(entry.get('superseded_by_review_digest'))):
            raise ValueError('invalid or duplicate history entry')
        identifiers.add(entry['history_id'])
    return identifiers


def read(path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def clean_path(value):
    if not text(value):
        return None
    value = re.sub(r'#L\d+(?:-L\d+)?$', '', value.strip())
    value = re.sub(r':\d+(?::\d+)?$', '', value)
    path = Path(value)
    if (path.is_absolute() or value == '.' or '..' in path.parts or '\\' in value
            or path.parts[0] in ('.git', '.agent-workflow')):
        return None
    return path.as_posix()


def feature_scope(folder, requirements):
    feature = requirements.get('feature', {}) if isinstance(requirements, dict) else {}
    modules = feature.get('modules', [])
    modules = sorted(set(modules)) if strings(modules) else []
    trace = read(folder / 'traceability.json', {})
    paths = []
    if isinstance(trace, dict) and isinstance(trace.get('links'), list):
        paths += [p for link in trace['links'] if isinstance(link, dict)
                  for p in link.get('code', []) if isinstance(p, str)]
    impact = read(folder / 'impact.json', {})
    if isinstance(impact, dict):
        for field in ('allowed_paths', 'inspected_paths'):
            if isinstance(impact.get(field), list):
                paths += impact[field]
    return {'modules': modules, 'paths': sorted(set(p for p in map(clean_path, paths) if p))}


def overlaps(left, right):
    matches = set()
    for a in left:
        for b in right:
            if a == b or a.startswith(b.rstrip('/') + '/') or b.startswith(a.rstrip('/') + '/'):
                matches.add(a if len(a) >= len(b) else b)
    return sorted(matches)


def fix_paths(folder, fix):
    paths = [p for p in fix.get('code_refs', []) if isinstance(p, str)]
    requirements = set(fix.get('requirement_ids', [])) if strings(fix.get('requirement_ids', [])) else set()
    trace = read(folder / 'traceability.json', {})
    if isinstance(trace, dict) and isinstance(trace.get('links'), list):
        paths += [p for link in trace['links'] if isinstance(link, dict) and link.get('requirement_id') in requirements
                  for p in link.get('code', []) if isinstance(p, str)]
    return sorted(set(p for p in map(clean_path, paths) if p))


def discover(root, feature_id):
    root = Path(root).resolve()
    current = root / '.agent-workflow/features' / feature_id
    requirements = read(current / 'spec/requirements.json')
    if not isinstance(requirements, dict) or not isinstance(requirements.get('feature'), dict):
        raise ValueError('current requirements record is invalid')
    scope = feature_scope(current, requirements)
    candidates, warnings = [], []
    parent = current.parent
    if not parent.is_dir():
        raise ValueError('feature workspace does not exist')
    for folder in sorted((p for p in parent.iterdir() if p.is_dir()), key=lambda p: p.name):
        try:
            historical_req = read(folder / 'spec/requirements.json', {})
            historical_fixes = read(folder / 'fixes.json', {'fixes': []})
            historical_scope = feature_scope(folder, historical_req)
            fixes = historical_fixes.get('fixes', []) if isinstance(historical_fixes, dict) else []
            if not isinstance(fixes, list):
                raise ValueError('fixes is not an array')
        except (OSError, ValueError, TypeError, KeyError) as exc:
            warnings.append(folder.name + ': skipped invalid historical records: ' + str(exc))
            continue
        shared_modules = sorted(set(scope['modules']) & set(historical_scope['modules']))
        for fix in fixes:
            if not isinstance(fix, dict) or fix.get('status') != 'verified' or not text(fix.get('id')):
                continue
            paths = fix_paths(folder, fix)
            shared_paths = overlaps(scope['paths'], paths)
            if not shared_modules and not shared_paths:
                continue
            candidate = {
                'id': folder.name + ':' + fix['id'],
                'feature_id': folder.name,
                'fix_id': fix['id'],
                'description': fix.get('description', ''),
                'kind': fix.get('kind', ''),
                'matched_modules': shared_modules,
                'matched_paths': shared_paths,
                'historical_regression_test_ids': fix.get('regression_test_ids', []),
                'historical_tested_revision': fix.get('tested_revision', ''),
            }
            candidate['candidate_digest'] = digest(candidate)
            candidates.append(candidate)
    candidates.sort(key=lambda row: row['id'])
    payload = {'scope': scope, 'candidates': candidates}
    return scope, candidates, digest(payload), warnings


def validate_review(root, folder, requirements, stage):
    errors, warnings = [], []
    required = requirements.get('feature', {}).get('history_regression_required', False)
    if not isinstance(required, bool):
        return ['feature.history_regression_required must be boolean'], []
    path = folder / 'regression-review.json'
    if not path.exists():
        message = 'historical regression review missing; sync it before new business-code edits'
        (errors if required and stage != 'draft' else warnings).append(message)
        return errors, warnings
    try:
        doc = read(path)
        if (not isinstance(doc, dict) or doc.get('schema_version') not in (1, 2)
                or doc.get('feature_id') != folder.name):
            raise ValueError('identity/schema mismatch')
        history_ids(doc.get('history', []))
        scope, candidates, review_digest, discovery_warnings = discover(root, folder.name)
        warnings.extend(discovery_warnings)
        if doc.get('scope') != scope or doc.get('candidates') != candidates or doc.get('review_digest') != review_digest:
            errors.append('historical regression review is stale; run sync and review changed candidates')
            return errors, warnings
        dispositions = doc.get('dispositions')
        if not isinstance(dispositions, list):
            raise ValueError('dispositions must be an array')
        by_id = {}
        for item in dispositions:
            if not isinstance(item, dict) or not text(item.get('candidate_id')) or item['candidate_id'] in by_id:
                raise ValueError('invalid or duplicate disposition')
            by_id[item['candidate_id']] = item
        known = {candidate['id']: candidate for candidate in candidates}
        if any(candidate_id not in known for candidate_id in by_id):
            errors.append('historical regression review contains obsolete dispositions; run sync')
        for candidate_id, candidate in known.items():
            item = by_id.get(candidate_id)
            if not item:
                if stage != 'draft':
                    errors.append('historical fix needs disposition: ' + candidate_id)
                continue
            if item.get('candidate_digest') != candidate['candidate_digest']:
                errors.append('historical fix disposition is stale: ' + candidate_id)
            action = item.get('action')
            if action not in ('retest', 'not_applicable') or not text(item.get('reason')):
                errors.append('historical fix needs retest/not_applicable action and reason: ' + candidate_id)
                continue
            if action == 'retest':
                if not strings(item.get('planned_checks')) or not item.get('planned_checks'):
                    errors.append('historical fix retest needs planned_checks: ' + candidate_id)
                if stage == 'check':
                    result = item.get('result')
                    if not isinstance(result, dict) or result.get('status') not in ('passed', 'waived'):
                        errors.append('historical fix retest needs passed/waived result: ' + candidate_id)
                    else:
                        for field in ('method', 'evidence', 'tested_revision'):
                            if not text(result.get(field)):
                                errors.append('historical fix retest result needs ' + field + ': ' + candidate_id)
                        if result.get('review_digest') != review_digest:
                            errors.append('historical fix retest evidence is stale: ' + candidate_id)
                        if result.get('status') == 'waived' and not all(text(result.get(field)) for field in ('residual_risk', 'approval_ref')):
                            errors.append('historical fix waiver needs residual_risk and approval_ref: ' + candidate_id)
        return errors, warnings
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return ['invalid historical regression review: ' + str(exc)], warnings


def render(folder):
    path = folder / 'regression-review.json'
    if not path.exists():
        return
    doc = read(path)
    dispositions = {row.get('candidate_id'): row for row in doc.get('dispositions', []) if isinstance(row, dict)}
    lines = ['# Historical regression review', '', 'Generated view; edit regression-review.json.', '',
             '- Modules: ' + (', '.join(doc.get('scope', {}).get('modules', [])) or 'none'),
             '- Paths: ' + (', '.join(doc.get('scope', {}).get('paths', [])) or 'none'),
             '- Review digest: ' + doc.get('review_digest', ''), '']
    for candidate in doc.get('candidates', []):
        item = dispositions.get(candidate.get('id'), {})
        result = item.get('result', {}) if isinstance(item.get('result'), dict) else {}
        lines += ['## ' + candidate.get('id', '?') + ' — ' + candidate.get('description', ''), '',
                  '- Match modules: ' + ', '.join(candidate.get('matched_modules', [])),
                  '- Match paths: ' + ', '.join(candidate.get('matched_paths', [])),
                  '- Historical tests: ' + ', '.join(candidate.get('historical_regression_test_ids', [])),
                  '- Action: ' + item.get('action', 'pending'),
                  '- Reason: ' + item.get('reason', ''),
                  '- Planned checks: ' + ', '.join(item.get('planned_checks', [])),
                  '- Result: ' + result.get('status', ''),
                  '- Evidence: ' + result.get('evidence', ''), '']
    if not doc.get('candidates'):
        lines += ['No related verified fixes were found from registered modules and code paths.', '']
    history = doc.get('history', [])
    if history:
        lines += ['# Superseded history', '',
                  'Preserved for audit only; these entries do not satisfy the current review.', '']
        for entry in history:
            item = entry.get('disposition', {})
            result = item.get('result', {}) if isinstance(item.get('result'), dict) else {}
            lines += ['## ' + entry.get('candidate_id', '?'), '',
                      '- Superseded reason: ' + entry.get('superseded_reason', ''),
                      '- Prior action: ' + item.get('action', ''),
                      '- Prior result: ' + result.get('status', ''),
                      '- Prior candidate digest: ' + entry.get('candidate_digest', ''),
                      '- Replacement candidate digest: ' + entry.get('superseded_by_candidate_digest', ''),
                      '- Replacement review digest: ' + entry.get('superseded_by_review_digest', ''), '']
    (folder / 'regression-review.md').write_text('\n'.join(lines))


def write_atomic(path, value):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def sync(root, feature_id):
    root = Path(root).resolve()
    folder = root / '.agent-workflow/features' / feature_id
    req_path = folder / 'spec/requirements.json'
    original_requirements = req_path.read_bytes()
    requirements = json.loads(original_requirements)
    if not isinstance(requirements, dict) or not isinstance(requirements.get('feature'), dict):
        raise ValueError('current requirements record is invalid')
    scope, candidates, review_digest, warnings = discover(root, feature_id)
    old = read(folder / 'regression-review.json', {})
    if not isinstance(old, dict):
        raise ValueError('existing regression review must be an object')
    old_dispositions = old.get('dispositions', [])
    old_history = old.get('history', [])
    old_candidates = old.get('candidates', [])
    if not isinstance(old_dispositions, list) or not isinstance(old_history, list) or not isinstance(old_candidates, list):
        raise ValueError('existing regression review arrays are invalid')
    old_by_id = {}
    for row in old_dispositions:
        if (not isinstance(row, dict) or not text(row.get('candidate_id'))
                or not text(row.get('candidate_digest')) or row['candidate_id'] in old_by_id):
            raise ValueError('existing regression review has invalid or duplicate dispositions')
        old_by_id[row['candidate_id']] = row
    old_candidate_by_id = {row.get('id'): row for row in old_candidates
                           if isinstance(row, dict) and text(row.get('id'))}
    history = copy.deepcopy(old_history)
    try:
        known_history_ids = history_ids(history)
    except ValueError as exc:
        raise ValueError('existing regression review has ' + str(exc)) from exc
    dispositions = []
    current_by_id = {candidate['id']: candidate for candidate in candidates}
    for candidate in candidates:
        item = old_by_id.get(candidate['id'])
        if isinstance(item, dict) and item.get('candidate_digest') == candidate['candidate_digest']:
            dispositions.append(copy.deepcopy(item))
    for candidate_id, item in old_by_id.items():
        current = current_by_id.get(candidate_id)
        if current and item.get('candidate_digest') == current['candidate_digest']:
            continue
        reason = 'candidate_changed' if current else 'candidate_removed'
        archived = {
            'candidate_id': candidate_id,
            'candidate_digest': item.get('candidate_digest', ''),
            'review_digest': old.get('review_digest', ''),
            'candidate': copy.deepcopy(old_candidate_by_id.get(candidate_id, {})),
            'disposition': copy.deepcopy(item),
            'superseded_reason': reason,
            'superseded_by_candidate_digest': current.get('candidate_digest', '') if current else '',
            'superseded_by_review_digest': review_digest,
        }
        archived['history_id'] = digest(archived)
        if archived['history_id'] not in known_history_ids:
            history.append(archived)
            known_history_ids.add(archived['history_id'])
    record = {'schema_version': 2, 'feature_id': feature_id, 'scope': scope, 'candidates': candidates,
              'review_digest': review_digest, 'dispositions': dispositions, 'history': history}
    requirements['feature']['history_regression_required'] = True
    if req_path.read_bytes() != original_requirements:
        raise ValueError('requirements changed during regression review sync; retry')
    write_atomic(req_path, requirements)
    write_atomic(folder / 'regression-review.json', record)
    render(folder)
    return record, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('sync', 'show'))
    parser.add_argument('project', type=Path)
    parser.add_argument('feature_id')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.feature_id):
        parser.error('invalid feature ID')
    try:
        if args.action == 'sync':
            record, warnings = sync(args.project, args.feature_id)
            for warning in warnings:
                print('WARNING: ' + warning)
            print('REGRESSION_REVIEW_SYNCED: candidates=%d pending=%d digest=%s' %
                  (len(record['candidates']), len(record['candidates']) - len(record['dispositions']), record['review_digest']))
        else:
            folder = args.project.resolve() / '.agent-workflow/features' / args.feature_id
            print(json.dumps(read(folder / 'regression-review.json', {}), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print('REGRESSION_REVIEW_ERROR: ' + str(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
