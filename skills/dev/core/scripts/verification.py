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
import hashlib

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
        if 'dependencies' in item:
            from impact import path_name
            paths = item['dependencies']
            if not isinstance(paths, list) or not paths or len(paths) != len(set(paths)):
                raise ValueError('scoped evidence requires distinct dependency paths')
            for name in paths:
                path_name(name)
            if not isinstance(item.get('scope_reason'), str) or not item['scope_reason'].strip():
                raise ValueError('scoped dependencies require investigation rationale')
        for index, result in enumerate(item['history']):
            if not isinstance(result, dict) or result.get('status') not in ('passed', 'failed', 'unavailable', 'waived', 'retained'):
                raise ValueError('invalid verification result')
            if any(not isinstance(result.get(k), str) or not result[k].strip() for k in ('digest', 'tested_revision', 'actual', 'evidence', 'at', 'method')):
                raise ValueError('verification result lacks evidence or tested identity')
            if result['status'] == 'retained' and (not isinstance(result.get('scope_files'), dict) or not isinstance(result.get('changed_paths'), list)
                                                   or not result['changed_paths'] or not all(isinstance(result.get(k), str) and result[k].strip() for k in ('reviewed_revision', 'reason', 'source_result_digest', 'semantic_digest'))):
                raise ValueError('retained evidence lacks reviewed scope and prior identity')
            if result['status'] == 'retained':
                previous = item['history'][index - 1] if index else None
                if previous is None or previous['status'] not in ('passed', 'retained') or result['source_result_digest'] != previous['digest'] or result['tested_revision'] != previous['tested_revision']:
                    raise ValueError('retained evidence lacks a matching prior pass')
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


def semantic_stamp(root, folder, row):
    """Meaning and execution contract, excluding mutable project file contents."""
    req, config, impact = sources(root, folder)
    contract = {k: v for k, v in row.items() if k not in ('history', 'retention')}
    impact_contract = {k: v for k, v in impact.items() if k != 'behaviors'}
    impact_contract['behaviors'] = [{k: v for k, v in b.items() if k != 'verification'} for b in impact['behaviors']]
    return digest({'requirements': req['requirements'], 'decisions': read(folder / 'decisions.json'),
                   'config': config, 'impact_contract': impact_contract, 'item': contract})


def scope_files(root, folder):
    """Fingerprint every registered changed/inspected project file."""
    root = root.resolve()
    impact = read(folder / 'impact.json')
    snap = impact_snapshot(root, impact)
    names = set(snap['changed_paths']) | set(impact['inspected_paths'])
    files = {}
    for name in sorted(names):
        from impact import path_name
        path_name(name)
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('unsafe scoped evidence path: ' + name)
        files[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    return files


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
            for key in ('dependencies', 'scope_reason'):
                if key in previous[row['id']]:
                    row[key] = previous[row['id']][key]
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


def result(status, stamp, head, actual, evidence, method, *, semantic=None, files=None):
    row = {'status': status, 'digest': stamp, 'tested_revision': head,
            'actual': actual, 'evidence': evidence, 'method': method,
            'at': datetime.now(timezone.utc).isoformat()}
    if semantic is not None:
        row['semantic_digest'] = semantic
        row['scope_files'] = files
    return row


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
    scoped = row['source'].startswith('impact:') and bool(row.get('dependencies'))
    row['history'].append(result(status, stamp, tested, actual, evidence, 'manual',
                                 semantic=semantic_stamp(root, folder, row) if scoped else None,
                                 files=scope_files(root, folder) if scoped else None))
    save(folder / 'verification.json', doc)
    render(folder)


def retain(root, folder, item_id, stamp, changed, reason, evidence):
    """Carry a prior pass only after a scoped, current-input relevance review."""
    doc = load_plan(folder)
    current, head = context(root, folder, doc)
    from feature_lifecycle import require_active
    require_active(read(folder / 'spec/requirements.json')['feature'])
    if stamp != current:
        raise ValueError('scope review digest is stale')
    row = next((r for r in doc['items'] if r['id'] == item_id), None)
    if row is None or row['mode'] != 'manual' or not row['history']:
        raise ValueError('only a previously observed manual item may retain evidence')
    if row['source'][:7] != 'impact:' or not row.get('dependencies'):
        raise ValueError('retention requires a scoped preserved impact behavior; otherwise retest')
    impact = read(folder / 'impact.json')
    behavior = next((b for b in impact['behaviors'] if b['id'] == row['source'][7:]), None)
    if behavior is None or behavior['kind'] != 'preserve':
        raise ValueError('only preserved behavior may retain prior evidence')
    previous = row['history'][-1]
    if previous['status'] not in ('passed', 'retained') or previous['digest'] == current:
        raise ValueError('only a stale prior pass can be retained; failures and waivers need fresh disposition')
    if not isinstance(previous.get('scope_files'), dict) or previous.get('semantic_digest') != semantic_stamp(root, folder, row):
        raise ValueError('prior evidence lacks matching semantic and file provenance; retest')
    now = scope_files(root, folder)
    before = previous['scope_files']
    delta = sorted(p for p in before.keys() | now.keys() if before.get(p) != now.get(p))
    if not delta or sorted(set(changed)) != delta or len(changed) != len(delta):
        raise ValueError('review every changed registered path exactly once: ' + ', '.join(delta))
    if set(row['dependencies']) & set(delta):
        raise ValueError('registered behavior dependency changed; rerun the affected check')
    if not set(row['dependencies']) <= set(now):
        raise ValueError('registered behavior dependency is outside observed scope')
    if not reason.strip() or not evidence.strip():
        raise ValueError('scope reasoning and inspected evidence are required')
    carried = result('retained', current, previous['tested_revision'],
                     'Prior passed observation in history at ' + previous['tested_revision'],
                     'Scope review at ' + head + ': ' + evidence + '; prior result digest: ' + previous['digest'],
                     'prior observation retained after scoped review; not re-executed',
                     semantic=previous['semantic_digest'], files=now)
    carried['reviewed_revision'] = head
    carried['changed_paths'] = delta
    carried['reason'] = reason
    carried['source_result_digest'] = previous['digest']
    row['history'].append(carried)
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
        return ['verification incomplete: ' + r['id'] + ' (' + state(r, stamp) + ')' for r in doc['items'] if state(r, stamp) not in ('passed', 'waived', 'retained')]
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return ['invalid verification: ' + str(exc)]


def impact_results(root, folder):
    """Read current checklist evidence without duplicating editable acceptance records."""
    doc = load_plan(folder)
    stamp, _ = context(root, folder, doc)
    impact_stamp = impact_snapshot(root, read(folder / 'impact.json'))['digest']
    results = {}
    for row in doc['items']:
        if row['source'].startswith('impact:') and state(row, stamp) in ('passed', 'waived', 'retained'):
            last = row['history'][-1]
            results[row['source'][7:]] = {'status': 'passed' if last['status'] == 'retained' else last['status'], 'method': last['method'],
                                       'evidence': last['actual'] + '\n' + last['evidence'], 'digest': impact_stamp}
    return results


def summary(root, folder):
    doc = load_plan(folder)
    stamp, head = context(root, folder, doc)
    items = []
    for row in doc['items']:
        item = {'id': row['id'], 'mode': row['mode'], 'status': state(row, stamp), 'expected': row['expected']}
        if row.get('dependencies'):
            item['dependencies'] = row['dependencies']
            item['scope_reason'] = row['scope_reason']
        if item['status'] == 'retained':
            last = row['history'][-1]
            item.update(tested_revision=last['tested_revision'], reviewed_revision=last['reviewed_revision'],
                        changed_paths=last['changed_paths'], reason=last['reason'])
        items.append(item)
    print(json.dumps({'digest': stamp, 'tested_revision': head, 'items': items}, ensure_ascii=False, indent=2))
    return 0 if all(r['status'] in ('passed', 'waived', 'retained') for r in items) else 2


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
        if row.get('dependencies'):
            lines += ['Dependencies: ' + ', '.join(row['dependencies']), 'Scope rationale: ' + row['scope_reason'], '']
        if row['history']:
            lines += ['Latest recorded evidence (not necessarily current):', '```json', json.dumps(row['history'][-1], ensure_ascii=False, indent=2), '```', '']
    (folder / 'verification.md').write_text('\n'.join(lines))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['sync', 'run', 'status', 'record', 'retain'])
    p.add_argument('root', type=Path)
    p.add_argument('feature_id')
    p.add_argument('--item'); p.add_argument('--status', choices=['passed', 'failed', 'unavailable', 'waived'])
    p.add_argument('--digest'); p.add_argument('--tested-revision'); p.add_argument('--actual'); p.add_argument('--evidence')
    p.add_argument('--changed-path', action='append', default=[]); p.add_argument('--reason')
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
        if args.action == 'retain':
            if not all([args.item, args.digest, args.reason, args.evidence]):
                raise ValueError('retain requires item, digest, changed-path, reason and evidence')
            retain(root, folder, args.item, args.digest, args.changed_path, args.reason, args.evidence)
            return 0
        return summary(root, folder)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        p.exit(1, 'ERROR: ' + str(exc) + '\n')


if __name__ == '__main__':
    sys.exit(main())
