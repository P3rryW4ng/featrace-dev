#!/usr/bin/env python3
"""Opt-in two-task Build workspaces and an external integration candidate; never write feature records."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

CORE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('build_snapshot', CORE / 'verify-handoff.py')
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)


def load(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    with Path(path).open('x') as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def seal(value):
    return {**value, 'record_digest': handoff.digest(value)}


def unseal(value):
    if not isinstance(value, dict):
        raise ValueError('scratch record must be an object')
    body = {k: v for k, v in value.items() if k != 'record_digest'}
    if value.get('record_digest') != handoff.digest(body):
        raise ValueError('scratch record changed; preserve it and start a new attempt')
    return body


def git(root, *args, env=None):
    return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(root), *args], stderr=subprocess.PIPE,
                                   env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0', **(env or {})})


def text(value):
    return isinstance(value, str) and bool(value.strip())


def commands(value):
    if not isinstance(value, list) or not value:
        raise ValueError('nonempty approved check commands required')
    if any(not isinstance(cmd, list) or not cmd or any(not text(arg) or '\0' in arg for arg in cmd)
           for cmd in value):
        raise ValueError('checks must be argv arrays, not shell strings')
    return value


def path(value):
    if not isinstance(value, str):
        raise ValueError('path must be a string')
    result = handoff.relative(value)
    if result == '.agent-workflow' or result.startswith('.agent-workflow/'):
        raise ValueError('workers cannot own shared workflow records')
    if any(char in result for char in '*?['):
        raise ValueError('use exact file paths, not globs')
    return result


def overlap(left, right):
    return left == right or left.startswith(right + '/') or right.startswith(left + '/')


def workflow_state(root):
    return {name: handoff.file_state(root, name)
            for name in handoff.tree_paths(root, '.agent-workflow')}


def prepare(project, feature_id, plan, out):
    project = Path(project).resolve()
    out = Path(out).resolve()
    if out.exists() or out == project or project in out.parents:
        raise ValueError('use a new attempt directory outside the project')
    if not isinstance(plan, dict) or plan.get('schema_version') != 1:
        raise ValueError('plan schema_version must be 1')
    selection = plan.get('tasks')
    if not isinstance(selection, list) or len(selection) != 2:
        raise ValueError('pilot requires exactly two task slices')
    independence = plan.get('independence', {})
    if (not isinstance(independence, dict) or not text(independence.get('reason'))
            or any(not isinstance(independence.get(k), list) or not independence[k]
                   or any(not text(x) for x in independence[k]) for k in ('evidence', 'interfaces', 'preserve'))):
        raise ValueError('review dependency evidence, interfaces and preserved behavior first')
    commands(plan.get('integration_checks'))
    timeout = plan.get('timeout_seconds', 120)
    if type(timeout) is not int or not 1 <= timeout <= 300:
        raise ValueError('timeout_seconds must be 1..300')
    folder = project / '.agent-workflow/features' / feature_id
    # Capture checks identity, ancestry, unsafe evidence, and unsupported submodules.
    base = git(project, 'rev-parse', 'HEAD').decode().strip()
    snapshot = handoff.capture(project, feature_id, base, [])
    changed = handoff.names(git(project, 'diff', '--name-only', '-z', 'HEAD'))
    changed += handoff.names(git(project, 'ls-files', '--others', '--exclude-standard', '-z'))
    if any(not (p == '.agent-workflow' or p.startswith('.agent-workflow/')) for p in changed):
        raise ValueError('uncommitted business paths: preserve work and use serial Build')
    valid = subprocess.run([sys.executable, str(CORE / 'validate-feature.py'), '--stage', 'develop',
                            str(project), feature_id], capture_output=True, text=True)
    if valid.returncode:
        raise ValueError('develop prerequisites failed:\n' + valid.stdout + valid.stderr)
    req = load(folder / 'spec/requirements.json')
    requirements = {r['id']: r for r in req['requirements']}
    tasks = {t['id']: t for t in load(folder / 'tasks.json')['tasks']}
    impact = load(folder / 'impact.json')
    allowed_impact = set(impact.get('allowed_paths', []))
    chosen = set()
    for item in selection:
        if not isinstance(item, dict):
            raise ValueError('task slice must be an object')
        tid = item.get('task_id')
        if not isinstance(tid, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', tid):
            raise ValueError('invalid task ID')
        if tid in chosen or tid not in tasks or tasks[tid]['status'] not in {'planned', 'in_progress'}:
            raise ValueError('select two distinct eligible existing tasks')
        chosen.add(tid)
        if item.get('depends_on') != [] or tasks[tid].get('depends_on', []):
            raise ValueError('dependent task slices use serial Build in this pilot')
        if any(requirements[r]['status'] != 'confirmed' for r in tasks[tid]['requirement_ids']):
            raise ValueError('selected task requirements must be confirmed')
        owned = item.get('allowed_paths')
        if not isinstance(owned, list) or not owned or len(set(owned)) != len(owned):
            raise ValueError('task requires unique exact allowed_paths')
        for name in owned:
            if path(name) != name:
                raise ValueError('use canonical ownership paths: ' + name)
            if name not in allowed_impact:
                raise ValueError('task path outside the reviewed impact boundary: ' + name)
            ignored = subprocess.run(['git', '-C', str(project), 'check-ignore', '--no-index', name], capture_output=True)
            if ignored.returncode not in {0, 1}:
                raise ValueError('cannot establish ignore status: ' + name)
            if ignored.returncode == 0:
                raise ValueError('ignored business path unsupported in this pilot: ' + name)
        commands(item.get('checks'))
    if any(overlap(a, b) for a in selection[0]['allowed_paths'] for b in selection[1]['allowed_paths']):
        raise ValueError('task ownership conflict; use serial Build')
    # Freeze canonical evidence. Workers read this copy, never update the primary records.
    out.mkdir(parents=True)
    write(out / 'snapshot.json', snapshot)
    frozen = {}
    for name, state in snapshot['inputs']['files'].items():
        if name.startswith('.agent-workflow/') and state['state'] == 'file':
            dest = out / 'inputs' / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((project / name).read_bytes())
            frozen[name] = state
    workspaces = {}
    try:
        for item in selection:
            worker = out / 'workers' / item['task_id']
            worker.parent.mkdir(exist_ok=True)
            git(project, 'worktree', 'add', '--detach', str(worker), base)
            workspaces[item['task_id']] = {'path': str(worker), 'workflow_state': workflow_state(worker)}
        handoff.check(project, feature_id, snapshot, None)
        doc = seal({'schema_version': 1, 'project': str(project), 'feature_id': feature_id,
                    'base_revision': base, 'plan': plan, 'workspaces': workspaces,
                    'snapshot': snapshot, 'frozen_files': frozen,
                    'develop_output': valid.stdout + valid.stderr})
        write(out / 'run.json', doc)
        return {'status': 'PARALLEL_BUILD_PREPARED', 'run': str(out), 'run_digest': doc['record_digest']}
    except Exception as exc:
        (out / 'prepare-error.txt').write_text(str(exc) + '\nWorkspaces retained; do not force-delete dirty work.\n')
        raise


def preflight(run):
    run = Path(run).resolve()
    doc = unseal(load(run / 'run.json'))
    handoff.check(Path(doc['project']), doc['feature_id'], doc['snapshot'], None)
    actual = {name: handoff.file_state(run / 'inputs', name)
              for name in handoff.tree_paths(run / 'inputs', '.agent-workflow')}
    if actual != doc['frozen_files']:
        raise ValueError('frozen authority changed')
    return doc


def proposal(run, doc, task_id):
    item = next((t for t in doc['plan']['tasks'] if t['task_id'] == task_id), None)
    if item is None:
        raise ValueError('task not in this attempt')
    worker = Path(doc['workspaces'][task_id]['path'])
    if git(worker, 'rev-parse', 'HEAD').decode().strip() != doc['base_revision']:
        raise ValueError('worker HEAD changed; leave edits uncommitted in this pilot')
    if workflow_state(worker) != doc['workspaces'][task_id]['workflow_state']:
        raise ValueError('worker modified shared workflow records')
    # A private index includes untracked code without mutating the worker's real index.
    with tempfile.TemporaryDirectory(dir=run, prefix='export-') as scratch:
        env = {'GIT_INDEX_FILE': str(Path(scratch) / 'index')}
        git(worker, 'read-tree', doc['base_revision'], env=env)
        git(worker, 'add', '-A', '--', '.', env=env)
        changed = handoff.names(git(worker, 'diff', '--cached', '--no-renames', '--name-only', '-z',
                                    doc['base_revision'], env=env))
        if not changed:
            raise ValueError('no implementation changes returned')
        if any(path(name) not in item['allowed_paths'] for name in changed):
            raise ValueError('worker scope expansion: ' + ', '.join(changed))
        raw = git(worker, 'diff', '--cached', '--no-renames', '--raw', doc['base_revision'], env=env)
        for row in raw.decode().splitlines():
            modes = row.split()[:2]
            if any(mode.lstrip(':') not in {'000000', '100644', '100755'} for mode in modes):
                raise ValueError('changed symlinks/submodules unsupported')
        patch = git(worker, 'diff', '--cached', '--no-ext-diff', '--no-textconv', '--binary',
                    '--no-renames', doc['base_revision'], '--', env=env)
    return worker, item, changed, patch


def candidate_state(root):
    visible = handoff.names(git(root, 'ls-files', '-z')) + handoff.names(git(root, 'ls-files', '--others', '--exclude-standard', '-z'))
    return {'files': {name: handoff.file_state(root, name) for name in visible},
            'workflow': workflow_state(root),
            'index': hashlib.sha256(git(root, 'ls-files', '--stage', '-z')).hexdigest()}


def checks(cwd, selected, directory, timeout):
    results = []
    for index, command in enumerate(selected):
        log = directory / ('check-%d.log' % index)
        with log.open('xb') as stream:
            try:
                proc = subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
                rc, state = proc.returncode, 'passed' if proc.returncode == 0 else 'failed'
            except subprocess.TimeoutExpired:
                rc, state = None, 'timeout'
            except OSError as exc:
                stream.write(str(exc).encode()); rc, state = None, 'unavailable'
        results.append({'command': command, 'status': state, 'returncode': rc, 'log': log.name,
                        'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest()})
    return results


def finish(run, task_id, status, summary):
    run = Path(run).resolve()
    doc = preflight(run)
    if status not in {'ready', 'blocked', 'failed'} or not text(summary):
        raise ValueError('return ready/blocked/failed and an honest summary')
    if task_id not in doc['workspaces']:
        raise ValueError('unknown task')
    directory = run / 'returns' / task_id
    directory.mkdir(parents=True, exist_ok=False)
    result = {'run_digest': handoff.digest(doc), 'task_id': task_id, 'status': status,
              'summary': summary, 'checks': []}
    try:
        if status == 'ready':
            worker, item, changed, patch = proposal(run, doc, task_id)
            result['worker_state'] = candidate_state(worker)
            result['changed_paths'] = changed
            result['patch_sha256'] = hashlib.sha256(patch).hexdigest()
            (directory / 'patch.diff').write_bytes(patch)
            result['checks'] = checks(worker, item['checks'], directory, doc['plan'].get('timeout_seconds', 120))
            if any(c['status'] != 'passed' for c in result['checks']):
                result['status'] = 'failed'
            if proposal(run, doc, task_id)[3] != patch or candidate_state(worker) != result['worker_state']:
                raise ValueError('checks changed the implementation; evidence cannot be reused')
            preflight(run)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        result.update(status='failed', error=str(exc))
    write(directory / 'result.json', seal(result))
    return result


def integrate(run):
    run = Path(run).resolve()
    doc = preflight(run)
    patches = []
    for item in doc['plan']['tasks']:
        tid = item['task_id']; directory = run / 'returns' / tid
        result = unseal(load(directory / 'result.json'))
        if (result.get('run_digest') != handoff.digest(doc) or result.get('task_id') != tid
                or result.get('status') != 'ready'):
            raise ValueError('task failed/blocked or result does not match the attempt: ' + tid)
        worker, item, changed, patch = proposal(run, doc, tid)
        if (result.get('worker_state') != candidate_state(worker) or result.get('changed_paths') != changed or result.get('patch_sha256') != hashlib.sha256(patch).hexdigest()
                or (directory / 'patch.diff').read_bytes() != patch):
            raise ValueError('worker changed after tests: ' + tid)
        results = result.get('checks', [])
        if len(results) != len(item['checks']):
            raise ValueError('required task checks missing: ' + tid)
        for index, check in enumerate(results):
            log = directory / ('check-%d.log' % index)
            if (check.get('command') != item['checks'][index] or check.get('status') != 'passed'
                    or check.get('returncode') != 0
                    or check.get('log_sha256') != hashlib.sha256(log.read_bytes()).hexdigest()):
                raise ValueError('task evidence changed or incomplete: ' + tid)
        patches.append(directory / 'patch.diff')
    candidate = run / 'integration'
    if candidate.exists() or (run / 'integration-report.json').exists():
        raise ValueError('integration attempt already exists; preserve it, do not auto-retry')
    git(doc['project'], 'worktree', 'add', '--detach', str(candidate), doc['base_revision'])
    result = {'run_digest': handoff.digest(doc), 'candidate': str(candidate), 'status': 'blocked',
              'base_revision': doc['base_revision'], 'checks': [], 'note': 'Candidate only; no primary writes or delivery approval.'}
    try:
        for patch in patches:
            try:
                git(candidate, 'apply', '--index', str(patch))
            except subprocess.CalledProcessError as exc:
                result.update(status='merge_conflict', error=exc.stderr.decode(errors='replace'))
                write(run / 'integration-report.json', seal(result))
                return result
        tree = git(candidate, 'write-tree').decode().strip()
        result['candidate_tree'] = tree
        before = candidate_state(candidate)
        result['checks'] = checks(candidate, doc['plan']['integration_checks'], run,
                                  doc['plan'].get('timeout_seconds', 120))
        result['status'] = 'candidate_checks_passed' if all(c['status'] == 'passed' for c in result['checks']) else 'checks_failed'
        if before != candidate_state(candidate) or git(candidate, 'write-tree').decode().strip() != tree:
            raise ValueError('integration checks changed candidate inputs')
        preflight(run)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        result.update(status='blocked', error=str(exc))
    write(run / 'integration-report.json', seal(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='action', required=True)
    p = subs.add_parser('prepare'); p.add_argument('project'); p.add_argument('feature_id'); p.add_argument('--plan', required=True); p.add_argument('--out', required=True)
    p = subs.add_parser('preflight'); p.add_argument('run')
    p = subs.add_parser('finish'); p.add_argument('run'); p.add_argument('task_id'); p.add_argument('--status', required=True, choices=['ready', 'blocked', 'failed']); p.add_argument('--summary', required=True)
    p = subs.add_parser('integrate'); p.add_argument('run')
    args = parser.parse_args()
    try:
        if args.action == 'prepare': result = prepare(args.project, args.feature_id, load(args.plan), args.out)
        elif args.action == 'preflight':
            doc = preflight(args.run); result = {'status': 'PARALLEL_BUILD_INPUTS_CURRENT', 'run_digest': handoff.digest(doc)}
        elif args.action == 'finish': result = finish(args.run, args.task_id, args.status, args.summary)
        else: result = integrate(args.run)
        print(json.dumps(result, indent=2))
        return 0 if result['status'] in {'PARALLEL_BUILD_PREPARED', 'PARALLEL_BUILD_INPUTS_CURRENT', 'ready', 'candidate_checks_passed'} else 1
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print('PARALLEL_BUILD_ERROR: ' + str(exc), file=sys.stderr); return 1


if __name__ == '__main__':
    sys.exit(main())
