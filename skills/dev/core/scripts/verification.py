#!/usr/bin/env python3
"""Generate acceptance rows, run configured checks, and retain revision-bound results."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import os

from impact import digest, git, snapshot as impact_snapshot, validate_impact
from project import validate_gates


def read(path):
    return json.loads(path.read_text())


def save(path, doc):
    if path.is_symlink():
        raise ValueError('refusing symlink record')
    with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False) as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(f.name, path)


def sources(root, folder):
    req = read(folder / 'spec/requirements.json')
    config_path = root / '.agent-workflow/project-baseline/quality-gates.json'
    config = read(config_path) if config_path.exists() else {'gates': []}
    validate_gates(root.resolve(), config)
    impact = read(folder / 'impact.json')
    errors, _ = validate_impact(root, folder, req, 'develop')
    if errors:
        raise ValueError('; '.join(errors))
    return req, config, impact


def candidates(req, config, impact):
    rows = []
    def add(source, expected, mode, gates):
        rows.append({'id': source + ':' + digest(expected)[:12], 'source': source,
                     'expected': expected, 'mode': mode, 'gates': gates,
                     'coverage': 'configured command result only' if mode == 'automatic' else '',
                     'history': []})
    for r in req['requirements']:
        if r.get('status') != 'deprecated':
            for index, ac in enumerate(r.get('acceptance_criteria', [])):
                add('requirement:' + r['id'] + ':' + str(index + 1), ac, 'manual', [])
    for b in impact['behaviors']:
        add('impact:' + b['id'], b['statement'], 'manual', [])
    for gate in config['gates']:
        add('gate:' + gate['name'], gate.get('purpose') or ('Command succeeds: ' + gate['name']), 'automatic', [gate['name']])
    if not config['gates']:
        add('system:no-gates', 'Select applicable quality checks; no commands configured', 'manual', [])
    return rows


def load_plan(folder):
    doc = read(folder / 'verification.json')
    if not isinstance(doc, dict) or doc.get('schema_version') != 1 or doc.get('feature_id') != folder.name or not isinstance(doc.get('items'), list) or not isinstance(doc.get('retired'), list):
        raise ValueError('invalid verification identity/schema')
    ids = set()
    for item in doc['items']:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or item['id'] in ids:
            raise ValueError('invalid/duplicate verification ID')
        ids.add(item['id'])
        if item.get('mode') not in ('manual', 'automatic') or not isinstance(item.get('gates'), list) or not all(isinstance(g, str) and g for g in item['gates']) or not isinstance(item.get('history'), list):
            raise ValueError('invalid verification item')
        if item['mode'] == 'automatic' and (not item['gates'] or not isinstance(item.get('coverage'), str) or not item['coverage'].strip()):
            raise ValueError('automatic mapping requires gates and coverage rationale')
        if item['mode'] == 'manual' and item['gates']:
            raise ValueError('manual items cannot declare automatic gates')
        for result in item['history']:
            if not isinstance(result, dict) or result.get('status') not in ('passed', 'failed', 'unavailable', 'waived'):
                raise ValueError('invalid verification result')
            if any(not isinstance(result.get(k), str) or not result[k].strip() for k in ('digest', 'tested_revision', 'actual', 'evidence', 'at', 'method')):
                raise ValueError('verification result lacks evidence or tested identity')
    return doc


def context(root, folder, doc):
    req, config, impact = sources(root, folder)
    expected = {r['id']: r for r in candidates(req, config, impact)}
    actual = {r['id']: r for r in doc['items']}
    if actual.keys() != expected.keys() or any(actual[k].get('source') != v['source'] or actual[k].get('expected') != v['expected'] for k, v in expected.items()):
        raise ValueError('verification list is stale; run sync')
    names = {g['name'] for g in config['gates']}
    for row in doc['items']:
        if any(g not in names for g in row['gates']):
            raise ValueError('unknown mapped gate: ' + row['id'])
        if row['source'].startswith('gate:') and (row['mode'] != 'automatic' or row['gates'] != expected[row['id']]['gates']):
            raise ValueError('generated gate rows must retain their command mapping')
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    contract = [{k: v for k, v in row.items() if k != 'history'} for row in doc['items']]
    # Ignore requirement workflow status/task progress; retain semantic requirements and decisions.
    decisions_path = folder / 'decisions.json'
    stamp = digest({'requirements': req['requirements'], 'decisions': read(decisions_path),
                    'impact': impact_snapshot(root, impact)['digest'], 'config': config, 'items': contract})
    return stamp, head


def sync(root, folder):
    req, config, impact = sources(root, folder)
    from feature_lifecycle import require_active
    require_active(req['feature'])
    old = load_plan(folder) if (folder / 'verification.json').exists() else {'items': [], 'retired': []}
    previous = {r['id']: r for r in old['items']}
    rows = candidates(req, config, impact)
    for row in rows:
        if row['id'] in previous:
            row.update({k: previous[row['id']][k] for k in ('mode', 'gates', 'coverage', 'history')})
    active = {r['id'] for r in rows}
    doc = {'schema_version': 1, 'feature_id': folder.name, 'items': rows,
           'retired': old['retired'] + [r for r in old['items'] if r['id'] not in active]}
    save(folder / 'verification.json', doc)
    req['feature']['verification_required'] = True
    save(folder / 'spec/requirements.json', req)
    render(folder)
    return doc


def state(row, stamp):
    if not row['history']:
        return 'not_run'
    result = row['history'][-1]
    return result['status'] if result['digest'] == stamp else 'stale'


def result(status, stamp, head, actual, evidence, method):
    return {'status': status, 'digest': stamp, 'tested_revision': head,
            'actual': actual, 'evidence': evidence, 'method': method,
            'at': datetime.now(timezone.utc).isoformat()}


def run(root, folder):
    doc = load_plan(folder)
    stamp, head = context(root, folder, doc)
    from feature_lifecycle import require_active
    require_active(read(folder / 'spec/requirements.json')['feature'])
    preflight = subprocess.run([sys.executable, str(Path(__file__).with_name('validate-feature.py')), '--stage', 'develop', str(root), folder.name], capture_output=True, text=True)
    if preflight.returncode:
        raise ValueError('development eligibility failed before execution: ' + preflight.stdout + preflight.stderr)
    report_path = root / '.agent-workflow/project-baseline/quality-report.json'
    old_bytes = report_path.read_bytes() if report_path.exists() else None
    execution = subprocess.run([sys.executable, str(Path(__file__).with_name('project.py')), 'check', str(root), '--feature', folder.name], capture_output=True, text=True)
    # A missing/newly unproduced report is unavailable, never borrow an earlier green report.
    fresh = report_path.exists() and report_path.read_bytes() != old_bytes
    report = read(report_path) if fresh else {'results': []}
    results = {r['name']: r for r in report['results']}
    after, after_head = context(root, folder, doc)
    for row in doc['items']:
        if row['mode'] != 'automatic':
            continue
        selected = [results.get(name) for name in row['gates']]
        statuses = [r['status'] if r else 'unavailable' for r in selected]
        outcome = 'failed' if 'failed' in statuses else ('unavailable' if 'unavailable' in statuses else 'passed')
        if (after, after_head) != (stamp, head):
            outcome = 'unavailable'
        actual = json.dumps(selected, ensure_ascii=False) if fresh else (execution.stdout + execution.stderr).strip() or 'No new quality report'
        row['history'].append(result(outcome, stamp, head, actual, 'quality-report executed at ' + str(report.get('tested_at', 'unavailable')), 'automatic'))
    # Do not overwrite concurrent edits to the plan while checks were running.
    if load_plan(folder) != doc_without_new_results(doc):
        raise ValueError('verification plan changed during execution; results not applied')
    save(folder / 'verification.json', doc)
    render(folder)
    print(execution.stdout, end='')
    return summary(root, folder)


def doc_without_new_results(doc):
    import copy
    old = copy.deepcopy(doc)
    for row in old['items']:
        if row['mode'] == 'automatic':
            row['history'].pop()
    return old


def record(root, folder, item_id, status, stamp, tested, actual, evidence):
    doc = load_plan(folder)
    current, head = context(root, folder, doc)
    from feature_lifecycle import require_active
    require_active(read(folder / 'spec/requirements.json')['feature'])
    if current != stamp or tested != head:
        raise ValueError('manual result does not match current digest/full commit; keep old-build evidence in report history')
    if not actual or not actual.strip() or not evidence or not evidence.strip():
        raise ValueError('actual observation and evidence required')
    row = next((r for r in doc['items'] if r['id'] == item_id), None)
    if row is None or row['mode'] != 'manual' or row['source'] == 'system:no-gates':
        raise ValueError('select a manual acceptance item, not a gate or missing-configuration row')
    row['history'].append(result(status, stamp, tested, actual, evidence, 'manual'))
    save(folder / 'verification.json', doc)
    render(folder)


def validate_verification(root, folder, req, stage):
    path = folder / 'verification.json'
    required = req.get('feature', {}).get('verification_required', False)
    if not isinstance(required, bool):
        return ['verification_required must be boolean']
    if not path.exists():
        return ['verification list missing; run sync'] if required and stage == 'check' else []
    try:
        doc = load_plan(folder)
        if stage != 'check':
            return []
        stamp, _ = context(root, folder, doc)
        return ['verification incomplete: ' + r['id'] + ' (' + state(r, stamp) + ')' for r in doc['items'] if state(r, stamp) not in ('passed', 'waived')]
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return ['invalid verification: ' + str(exc)]


def impact_results(root, folder):
    """Read current checklist evidence without duplicating editable acceptance records."""
    doc = load_plan(folder)
    stamp, _ = context(root, folder, doc)
    impact_stamp = impact_snapshot(root, read(folder / 'impact.json'))['digest']
    results = {}
    for row in doc['items']:
        if row['source'].startswith('impact:') and state(row, stamp) in ('passed', 'waived'):
            last = row['history'][-1]
            results[row['source'][7:]] = {'status': last['status'], 'method': last['method'],
                                       'evidence': last['actual'] + '\n' + last['evidence'], 'digest': impact_stamp}
    return results


def summary(root, folder):
    doc = load_plan(folder)
    stamp, head = context(root, folder, doc)
    items = [{'id': r['id'], 'mode': r['mode'], 'status': state(r, stamp), 'expected': r['expected']} for r in doc['items']]
    print(json.dumps({'digest': stamp, 'tested_revision': head, 'items': items}, ensure_ascii=False, indent=2))
    return 0 if all(r['status'] in ('passed', 'waived') for r in items) else 2


def render(folder):
    if not (folder / 'verification.json').exists():
        return
    doc = load_plan(folder)
    root = folder.parents[2]
    try:
        stamp, _ = context(root, folder, doc)
    except (OSError, ValueError, TypeError, KeyError):
        stamp = None
    lines = ['# Verification checklist', '', 'Generated view; manual observation and automated checks are distinct.', '']
    for row in doc['items']:
        lines += ['## ' + row['id'], '', 'Mode: ' + row['mode'], 'Expected: ' + str(row['expected']),
                  'Status: ' + (state(row, stamp) if stamp else 'stale — synchronize sources'), '']
        if row['history']:
            lines += ['Latest recorded evidence (not necessarily current):', '```json', json.dumps(row['history'][-1], ensure_ascii=False, indent=2), '```', '']
    (folder / 'verification.md').write_text('\n'.join(lines))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['sync', 'run', 'status', 'record'])
    p.add_argument('root', type=Path)
    p.add_argument('feature_id')
    p.add_argument('--item'); p.add_argument('--status', choices=['passed', 'failed', 'unavailable', 'waived'])
    p.add_argument('--digest'); p.add_argument('--tested-revision'); p.add_argument('--actual'); p.add_argument('--evidence')
    args = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.feature_id):
        p.error('invalid feature ID')
    root = args.root.resolve(); folder = root / '.agent-workflow/features' / args.feature_id
    if not folder.resolve().is_relative_to(root) or folder.is_symlink():
        p.error('unsafe feature path')
    try:
        if args.action == 'sync':
            sync(root, folder); summary(root, folder); return 0
        if args.action == 'run':
            return run(root, folder)
        if args.action == 'record':
            if not all([args.item, args.status, args.digest, args.tested_revision, args.actual, args.evidence]):
                raise ValueError('record requires item, status, digest, tested-revision, actual and evidence')
            record(root, folder, args.item, args.status, args.digest, args.tested_revision, args.actual, args.evidence)
            return 0
        return summary(root, folder)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        p.exit(1, 'ERROR: ' + str(exc) + '\n')


if __name__ == '__main__':
    sys.exit(main())
