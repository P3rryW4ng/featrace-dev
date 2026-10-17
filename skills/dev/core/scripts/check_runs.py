#!/usr/bin/env python3
"""Explicit feature selections and immutable check attempts; never infer coverage."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import uuid


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def safe(root, path):
    original_root = Path(root).absolute(); root = original_root.resolve()
    path = Path(path)
    if path.is_absolute() and path.is_relative_to(original_root): path = root / path.relative_to(original_root)
    if not path.is_absolute(): path = root / path
    if not path.is_relative_to(root): raise ValueError('check record outside workspace')
    cursor = root
    for part in path.relative_to(root).parts:
        if part in ('.', '..'): raise ValueError('unsafe check record')
        cursor /= part
        if cursor.is_symlink(): raise ValueError('symlink check record')
    return path


def read(root, path):
    return json.loads(safe(root, path).read_text())


def save(root, path, value, *, create=False):
    path = safe(root, path); path.parent.mkdir(parents=True, exist_ok=True)
    if create and path.exists(): raise ValueError('immutable check record already exists')
    with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False) as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n'); name = f.name
        f.flush(); os.fsync(f.fileno())
    try:
        if create:
            os.link(name, path)  # No replace of an existing immutable fact.
            os.unlink(name)
        else: os.replace(name, path)
    finally:
        if Path(name).exists(): Path(name).unlink()


def folder(root, feature):
    if not isinstance(feature, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', feature):
        raise ValueError('explicit feature ID required')
    f = safe(root, '.agent-workflow/features/' + feature)
    req = read(root, f / 'spec/requirements.json')
    if req.get('feature', {}).get('id') != feature: raise ValueError('check feature mismatch')
    return f


def enabled(root):
    base = Path(root) / '.agent-workflow/project-baseline'
    config_path = safe(root, base / 'quality-gates.json')
    if not config_path.exists() and not (base / 'check-contract-v2-origin.json').exists(): return False
    config = read(root, config_path)
    marker = config.get('execution_contract')
    if marker is not None and (type(marker) is not int or marker != 2):
        raise ValueError('unsupported check execution contract')
    if (base / 'check-contract-v2-origin.json').exists() and marker != 2:
        raise ValueError('explicit check contract removed; no fallback to legacy results')
    return marker == 2


@contextmanager
def execution_lock(root):
    if os.name != 'posix': raise ValueError('isolated check process lifecycle currently requires POSIX')
    import fcntl
    p = safe(root, '.agent-workflow/scratch/check-execution.lock'); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('a') as stream:
        try: fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError: raise ValueError('workspace checks busy; no command started') from None
        try: yield
        finally: fcntl.flock(stream, fcntl.LOCK_UN)


def selection(root, feature):
    root = Path(root).resolve()
    from project import validate_gates
    f = folder(root, feature)
    catalog = read(root, Path(root) / '.agent-workflow/project-baseline/quality-gates.json')
    validate_gates(root, catalog)
    if not enabled(root): return catalog
    chosen = read(root, f / 'check-selection.json')
    if (set(chosen) != {'schema_version', 'feature_id', 'gates', 'reason'} or chosen['schema_version'] != 1
            or chosen['feature_id'] != feature or not isinstance(chosen['reason'], str) or not chosen['reason'].strip()
            or not isinstance(chosen['gates'], list) or not chosen['gates']):
        raise ValueError('invalid feature check selection')
    by_name = {g['name']: g for g in catalog['gates']}; gates = []; seen = set()
    for item in chosen['gates']:
        if (not isinstance(item, dict) or set(item) != {'name', 'test_ids'} or item['name'] in seen
                or item['name'] not in by_name): raise ValueError('missing or duplicate selected check definition')
        seen.add(item['name']); gate = dict(by_name[item['name']]); gate['test_ids'] = item['test_ids']; gates.append(gate)
    resolved = {'selection_feature_id': feature, 'gates': gates, 'selection_reason': chosen['reason']}
    validate_gates(root, resolved)
    return resolved


def prepare(root, feature, selected, reason):
    """Explicit opt-in only. Input is [{name,test_ids}], referring to catalog gates."""
    root = Path(root).resolve()
    from project import validate_gates
    if not isinstance(reason, str) or not reason.strip(): raise ValueError('selection reason required')
    f = folder(root, feature); base = Path(root) / '.agent-workflow/project-baseline'
    with execution_lock(root):
        no_unfinished(root)
        config = read(root, base / 'quality-gates.json'); validate_gates(root, config)
        trial = {'schema_version': 1, 'feature_id': feature, 'gates': selected, 'reason': reason}
        if not isinstance(selected, list) or not selected: raise ValueError('explicit nonempty gate selection required')
        by_name = {g['name']: g for g in config['gates']}; seen = set(); resolved = []
        for item in selected:
            if (not isinstance(item, dict) or set(item) != {'name', 'test_ids'} or item['name'] not in by_name or item['name'] in seen):
                raise ValueError('invalid selected definition')
            seen.add(item['name']); g = dict(by_name[item['name']]); g['test_ids'] = item['test_ids']; resolved.append(g)
        validate_gates(root, {'selection_feature_id': feature, 'gates': resolved})
        # Record the legacy source before the explicit project-wide switch.
        origin = base / 'check-contract-v2-origin.json'
        if config.get('execution_contract') != 2:
            if origin.exists():
                saved = read(root, origin)
                if saved.get('config') != config or saved.get('digest') != digest(config):
                    raise ValueError('interrupted contract preparation differs; inspect before retry')
            else: save(root, origin, {'schema_version': 1, 'config': config, 'digest': digest(config), 'at': now()}, create=True)
        save(root, f / 'check-selection.json', trial)
        config['execution_contract'] = 2; save(root, base / 'quality-gates.json', config)
    return trial


def locate(root, feature):
    f = folder(root, feature); head = read(root, f / 'check-head.json')
    if set(head) != {'schema_version', 'feature_id', 'attempt_id'} or head['schema_version'] != 1 or head['feature_id'] != feature:
        raise ValueError('invalid latest check pointer')
    ident = head['attempt_id']
    if not isinstance(ident, str) or not re.fullmatch('[0-9a-f]{32}', ident): raise ValueError('invalid check attempt ID')
    return f / 'check-runs' / ident, head


def terminal(root, feature):
    d, head = locate(root, feature)
    start = read(root, d / 'start.json'); result = read(root, d / 'result.json')
    for value, field in [(start, 'digest'), (result, 'digest')]:
        if not isinstance(value, dict) or value.get(field) != digest({k: v for k, v in value.items() if k != field}):
            raise ValueError('check fact hash mismatch')
    if (start.get('schema_version') != 1 or result.get('schema_version') != 1
            or start.get('feature_id') != feature or start.get('attempt_id') != head['attempt_id']
            or result.get('start_digest') != start['digest'] or result.get('attempt_id') != head['attempt_id']
            or result.get('status') not in ('passed', 'failed', 'unavailable', 'interrupted')):
        raise ValueError('incomplete or cross-feature check fact')
    expected = start['selection']['gates']; values = result.get('results')
    if not isinstance(values, list) or [v.get('name') for v in values] != [g['name'] for g in expected]:
        raise ValueError('incomplete check result set')
    for value, gate in zip(values, expected):
        if value.get('test_ids') != gate['test_ids'] or value.get('command') != gate['command']:
            raise ValueError('check result does not match frozen command/tests')
    if result['status'] == 'passed' and (result.get('comparison', {}).get('state') != 'same'
            or result.get('lifecycle_safe') is not True
            or any(v.get('status') != 'passed' or v.get('returncode') != 0 for v in values)):
        raise ValueError('check success lacks complete stable execution')
    return start, result


def _current(root, feature):
    from project import quality_snapshot, quality_comparison, quality_selection
    if not enabled(root): raise ValueError('feature attempts not enabled')
    start, result = terminal(root, feature)
    if result['status'] != 'passed': raise ValueError('latest check attempt is ' + result['status'])
    config = selection(root, feature)
    if quality_selection(config) != start['selection_identity']: raise ValueError('check selection changed')
    latest = quality_snapshot(root, config)
    if quality_comparison(root, start['project_snapshot'], latest)['state'] != 'same': raise ValueError('check inputs changed or unknown')
    if terminal(root, feature) != (start, result): raise ValueError('check head changed during read')
    return {'tested_at': result['ended_at'], 'project_snapshot': start['project_snapshot'],
            'quality_selection': start['selection_identity'], 'results': result['results'],
            'input_comparison': result['comparison'], 'attempt_id': start['attempt_id'],
            'attempt_digest': result['digest'], 'execution_contract': 2}


def current(root, feature):
    # A live/orphaned command in another feature can still mutate this workspace.
    # Inspect only while no runner owns the workspace lock and all groups resolved.
    with execution_lock(root):
        no_unfinished(root)
        return _current(root, feature)


def view(root, feature):
    try:
        report = current(root, feature)
        return {'state': 'current', 'attempt_id': report['attempt_id'], 'digest': report['attempt_digest'],
                'report_ref': '.agent-workflow/features/' + feature + '/check-runs/' + report['attempt_id'] + '/result.json', 'report': report}
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return {'state': 'unavailable', 'reason': str(exc)}


def records(root, feature):
    start, result = terminal(root, feature)
    return ['.agent-workflow/project-baseline/quality-gates.json',
            '.agent-workflow/project-baseline/check-contract-v2-origin.json',
            '.agent-workflow/features/' + feature + '/check-selection.json',
            '.agent-workflow/features/' + feature + '/check-head.json',
            '.agent-workflow/features/' + feature + '/check-runs/' + start['attempt_id'] + '/start.json',
            '.agent-workflow/features/' + feature + '/check-runs/' + start['attempt_id'] + '/result.json']


def report(root, feature):
    if enabled(root): return current(root, feature)
    return read(root, Path(root) / '.agent-workflow/project-baseline/quality-report.json')


def no_unfinished(root):
    features = safe(root, '.agent-workflow/features')
    for f in features.iterdir():
        if f.is_symlink(): raise ValueError('unsafe feature check directory')
        runs = safe(root, f / 'check-runs')
        if not runs.exists(): continue
        for d in runs.iterdir():
            safe(root, d)
            if not d.is_dir(): raise ValueError('unsafe attempt directory')
            if not (d / 'start.json').is_file() or not (d / 'result.json').is_file():
                raise ValueError('unfinished check execution; inspect process state before another run')
            result = read(root, d / 'result.json'); start = read(root, d / 'start.json')
            if (result.get('digest') != digest({k:v for k,v in result.items() if k != 'digest'})
                    or start.get('digest') != digest({k:v for k,v in start.items() if k != 'digest'})
                    or result.get('start_digest') != start.get('digest')):
                raise ValueError('prior check facts corrupt; inspect before another run')
            if result.get('lifecycle_safe') is not True: raise ValueError('check process lifecycle unresolved; inspect before another run')


def run_gate(gate, cmd, cwd, timeout):
    started = now(); proc = None; safe_end = True; status = 'unavailable'; code = None; stdout = stderr = ''; error = None
    try:
        proc = subprocess.Popen(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        stdout, stderr = proc.communicate(timeout=timeout); code = proc.returncode; status = 'passed' if code == 0 else 'failed'
    except BaseException as exc:
        if not isinstance(exc, (OSError, subprocess.TimeoutExpired, KeyboardInterrupt)): raise
        error = type(exc).__name__; status = 'interrupted' if isinstance(exc, KeyboardInterrupt) else 'unavailable'
        if proc is not None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                try: stdout, stderr = proc.communicate(timeout=0.5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL); stdout, stderr = proc.communicate(timeout=2)
            except (OSError, subprocess.TimeoutExpired): safe_end = False
    # A successful parent can leave a child alive. Never silently permit a retry.
    if proc is not None:
        try: os.killpg(proc.pid, 0); safe_end = False
        except ProcessLookupError: pass
        except OSError: safe_end = False
    value = {'name': gate['name'], 'command': cmd, 'test_ids': gate.get('test_ids', []), 'status': status,
             'returncode': code, 'stdout': stdout[-12000:], 'stderr': stderr[-12000:], 'started_at': started, 'ended_at': now()}
    if error: value['error'] = error
    return value, safe_end


def run(root, feature):
    from project import quality_selection, quality_snapshot, quality_comparison, validate_gates
    root = Path(root).resolve(); f = folder(root, feature)
    if not enabled(root): raise ValueError('explicit prepare required before feature attempts')
    with execution_lock(root):
        no_unfinished(root)
        config = selection(root, feature); prepared = validate_gates(root, config)
        if not prepared: raise ValueError('no selected checks')
        before = quality_snapshot(root, config)
        if before['check_inputs'].get('state') != 'identified': raise ValueError('check inputs unknown before execution')
        ident = uuid.uuid4().hex; d = f / 'check-runs' / ident
        start = {'schema_version': 1, 'feature_id': feature, 'attempt_id': ident, 'started_at': now(),
                 'selection': config, 'selection_identity': quality_selection(config), 'project_snapshot': before}
        start['digest'] = digest(start); save(root, d / 'start.json', start, create=True)
        head = {'schema_version': 1, 'feature_id': feature, 'attempt_id': ident}; save(root, f / 'check-head.json', head)
        results = []; lifecycle = True; interrupted = False
        for gate, cmd, cwd, timeout in prepared:
            if interrupted:
                result = {'name': gate['name'], 'command': cmd, 'test_ids': gate.get('test_ids', []), 'status': 'unavailable', 'returncode': None, 'error': 'not executed after interruption'}
            else:
                result, ended = run_gate(gate, cmd, cwd, timeout); lifecycle &= ended
                interrupted = result['status'] == 'interrupted' or not ended
            results.append(result)
        try:
            after = quality_snapshot(root, selection(root, feature)); comparison = quality_comparison(root, before, after)
        except (OSError, ValueError, TypeError, KeyError): comparison = {'state': 'unknown'}
        status = 'interrupted' if interrupted else ('passed' if lifecycle and comparison['state'] == 'same' and all(v['status'] == 'passed' for v in results) else 'failed' if any(v['status'] == 'failed' for v in results) else 'unavailable')
        result = {'schema_version': 1, 'attempt_id': ident, 'start_digest': start['digest'], 'ended_at': now(),
                  'status': status, 'comparison': comparison, 'lifecycle_safe': lifecycle, 'results': results}
        result['digest'] = digest(result)
        if read(root, f / 'check-head.json') != head: raise ValueError('check head changed; execution remains unfinished')
        save(root, d / 'result.json', result, create=True)
        print('CHECK_ATTEMPT: ' + ident + ' ' + status)
        return 0 if status == 'passed' else 2


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('action', choices=['prepare', 'status'])
    p.add_argument('root', type=Path); p.add_argument('feature'); p.add_argument('--selection', type=Path); p.add_argument('--reason')
    a = p.parse_args(); root = a.root.resolve()
    if a.action == 'prepare':
        if not a.selection or not a.reason: p.error('prepare requires --selection and --reason')
        prepare(root, a.feature, json.loads(a.selection.read_text()), a.reason); print('CHECK_CONTRACT_PREPARED: no command executed')
    else: print(json.dumps(view(root, a.feature), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try: main()
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print('CHECK_RUN_ERROR: ' + str(exc), file=sys.stderr); sys.exit(2)
