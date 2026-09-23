#!/usr/bin/env python3
"""Small cross-platform manifest inventory and explicit quality-command runner."""
import argparse
import hashlib
import json
import os
import math
import re
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

SKIP = {'.git', '.agent-workflow', '.agents', '.claude', 'node_modules', 'build', '.gradle', '.venv', 'venv', 'vendor', 'Pods', 'DerivedData', '__pycache__'}
NAMES = {'settings.gradle', 'settings.gradle.kts', 'build.gradle', 'build.gradle.kts', 'libs.versions.toml', 'gradle.lockfile', 'gradle-wrapper.properties', 'Package.swift', 'project.pbxproj', 'package.json', 'package-lock.json', 'pnpm-lock.yaml', 'yarn.lock', 'go.mod', 'go.sum', 'pyproject.toml', 'requirements.txt', 'pom.xml', 'Cargo.toml', 'Cargo.lock', 'Makefile', 'CMakeLists.txt'}


def workflow_path(path):
    return path == '.agent-workflow' or path.startswith('.agent-workflow/')


def git_paths(root, *args):
    run = subprocess.run(['git', '-C', str(root), *args], capture_output=True)
    if run.returncode != 0:
        return None
    return sorted(set(path.decode('utf-8', 'surrogateescape') for path in run.stdout.split(b'\0') if path))


def committed_paths(root, old_head, new_head):
    if not old_head or not new_head or old_head == new_head:
        return []
    return git_paths(root, 'diff', '--name-only', '-z', old_head, new_head, '--')


def worktree_paths(root):
    groups = [
        git_paths(root, 'diff', '--name-only', '-z', '--'),
        git_paths(root, 'diff', '--cached', '--name-only', '-z', '--'),
        git_paths(root, 'ls-files', '--others', '--exclude-standard', '-z', '--'),
    ]
    if any(group is None for group in groups):
        return []
    return sorted(set(path for group in groups for path in group if not workflow_path(path)))


def changed_keys(before, after):
    before = before if isinstance(before, dict) else {}
    after = after if isinstance(after, dict) else {}
    return sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))


def print_paths(label, paths, limit=50):
    if paths is None:
        print(label + ': unavailable')
        return
    shown = paths[:limit]
    print(label + ': ' + (', '.join(shown) or 'none'))
    if len(paths) > limit:
        print(label + '_MORE: ' + str(len(paths) - limit))


def baseline_diagnostics(root, recorded, current):
    reasons = []
    if not isinstance(recorded, dict) or not isinstance(current, dict):
        return ['invalid_fingerprint'], None, [], [], []
    if set(recorded) != set(current):
        reasons.append('fingerprint_shape')
    if recorded.get('version') != current.get('version'):
        reasons.append('fingerprint_version')
    if recorded.get('profile') != current.get('profile'):
        reasons.append('profile')
    manifest_paths = changed_keys(recorded.get('files'), current.get('files'))
    if manifest_paths:
        reasons.append('manifests')
    evidence_paths = changed_keys(recorded.get('evidence'), current.get('evidence'))
    if evidence_paths:
        reasons.append('evidence')
    old_head, new_head = recorded.get('git_head', ''), current.get('git_head', '')
    head_paths = []
    if old_head != new_head:
        reasons.append('git_head')
        head_paths = committed_paths(root, old_head, new_head)
    return reasons, head_paths, manifest_paths, evidence_paths, worktree_paths(root)


def verify_baseline(root, recorded, current):
    reasons, head_paths, manifest_paths, evidence_paths, dirty_paths = baseline_diagnostics(root, recorded, current)
    if reasons == ['git_head'] and head_paths and all(workflow_path(path) for path in head_paths) and not dirty_paths:
        print('BASELINE_VALID: manifests and registered evidence only')
        print_paths('BASELINE_HEAD_ADVANCED_WORKFLOW_ONLY', head_paths)
        return 0
    if reasons:
        print('BASELINE_STALE: review changed project files before refreshing the baseline')
        print('BASELINE_STALE_REASONS: ' + ', '.join(reasons))
        if 'git_head' in reasons:
            print_paths('HEAD_CHANGED_PATHS', head_paths)
        if manifest_paths:
            print_paths('MANIFEST_CHANGED_PATHS', manifest_paths)
        if evidence_paths:
            print_paths('EVIDENCE_CHANGED_PATHS', evidence_paths)
        if dirty_paths:
            print_paths('WORKTREE_CHANGED_PATHS', dirty_paths)
        return 3
    if dirty_paths:
        print('BASELINE_WORKTREE_REVIEW_REQUIRED: uncommitted project paths are outside the baseline fingerprint')
        print_paths('WORKTREE_CHANGED_PATHS', dirty_paths)
        return 3
    print('BASELINE_VALID: manifests and registered evidence only')
    return 0

def snapshot(root, baseline=None):
    files = {}
    android = False
    for parent, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not Path(parent, d).is_symlink())
        for name in sorted(names):
            path = Path(parent, name)
            if name not in NAMES or path.is_symlink():
                continue
            data = path.read_bytes()
            files[str(path.relative_to(root))] = hashlib.sha256(data).hexdigest()
            if name in {'build.gradle', 'build.gradle.kts', 'libs.versions.toml'}:
                android |= any(x in data for x in (b'com.android.application', b'com.android.library'))
    git = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    evidence = {}
    registry = (baseline or root / '.agent-workflow/project-baseline') / 'evidence-files.json'
    registered = []
    if registry.exists():
        record = json.loads(registry.read_text())
        if not isinstance(record, dict) or not isinstance(record.get('files'), list) or not all(isinstance(p, str) and p for p in record['files']):
            raise ValueError('evidence-files.json requires a files array of relative paths')
        registered = record['files']
    for rel in sorted(set(registered + ['AGENTS.md', 'CLAUDE.md'])):
        path = root / rel
        if Path(rel).is_absolute():
            raise ValueError('evidence path must be relative')
        path.resolve().relative_to(root)
        if path.is_symlink() or path.is_dir():
            raise ValueError('evidence must be a regular project file: ' + rel)
        evidence[rel] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    return {'version': 2, 'evidence': evidence, 'profile': 'android' if android else 'generic', 'git_head': git.stdout.strip() if git.returncode == 0 else '', 'files': files}

def quality_snapshot_matches(root, recorded, current):
    """Accept a later HEAD only when tracked changes are workflow records alone."""
    if recorded == current:
        return True
    if not isinstance(recorded, dict) or not isinstance(current, dict):
        return False
    recorded_without_head = dict(recorded)
    current_without_head = dict(current)
    old_head = recorded_without_head.pop('git_head', '')
    new_head = current_without_head.pop('git_head', '')
    if recorded_without_head != current_without_head or not old_head or not new_head:
        return False
    changed = subprocess.run(
        ['git', '-C', str(root), 'diff', '--name-only', '-z', old_head, new_head, '--'],
        capture_output=True, text=True)
    if changed.returncode != 0:
        return False
    paths = [path for path in changed.stdout.split('\0') if path]
    return all(path == '.agent-workflow' or path.startswith('.agent-workflow/') for path in paths)

def validate_gates(root, config):
    """Validate all selected commands before executing any; never interpret prose conditions."""
    if not isinstance(config, dict) or not isinstance(config.get('gates'), list):
        raise ValueError('quality-gates.json requires a gates array')
    if set(config) - {'gates', 'notes', 'selection_reason', 'known_gaps'}:
        raise ValueError('unsupported quality configuration field; keep candidates separately')
    prepared, names = [], set()
    for gate in config['gates']:
        if not isinstance(gate, dict):
            raise ValueError('gate must be an object')
        if set(gate) - {'name', 'command', 'cwd', 'timeout_seconds', 'purpose', 'source', 'selection_reason', 'test_ids'}:
            raise ValueError('unsupported gate field: conditions/templates belong in quality-candidates.json')
        name, cmd = gate.get('name'), gate.get('command')
        if not isinstance(name, str) or not name.strip() or name in names:
            raise ValueError('each selected gate needs a unique non-empty name')
        names.add(name)
        test_ids = gate.get('test_ids', [])
        if (not isinstance(test_ids, list) or
                any(not isinstance(value, str) or not value.strip() for value in test_ids) or
                len(set(test_ids)) != len(test_ids)):
            raise ValueError('gate test_ids must be unique non-empty text IDs')
        if not isinstance(cmd, list) or not cmd or not all(isinstance(x, str) and x.strip() for x in cmd):
            raise ValueError('gate command must be a non-empty argument array')
        if any(re.search(r'<[^<>]+>|\{\{.*?\}\}|\$\{[^}]+\}', arg) for arg in cmd):
            raise ValueError('unresolved placeholder in selected command')
        rel = gate.get('cwd', '.')
        if not isinstance(rel, str) or Path(rel).is_absolute():
            raise ValueError('gate cwd must be project-relative')
        cwd = (root / rel).resolve()
        cwd.relative_to(root)
        if not cwd.is_dir():
            raise ValueError('gate cwd does not exist')
        timeout = gate.get('timeout_seconds', 600)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 86400:
            raise ValueError('invalid gate timeout')
        prepared.append((gate, cmd, cwd, timeout))
    return prepared


def inventory(root, base):
    data = snapshot(root, base)
    base.mkdir(parents=True, exist_ok=True)
    (base / 'fingerprint.json').write_text(json.dumps(data, indent=2) + '\n')
    files = '\n'.join('- ' + p for p in sorted(data['files']))
    (base / 'inventory.md').write_text('# Manifest inventory\n\nProfile: ' + data['profile'] + '\n\n' + files + '\n')
    for name, title in [('architecture', 'Architecture'), ('conventions', 'Conventions'), ('examples', 'Reuse examples')]:
        path = base / (name + '.md')
        if not path.exists():
            path.write_text('# ' + title + '\n\nAgent review required. Cite actual project files.\n')
    if not (base / 'quality-gates.json').exists():
        (base / 'quality-gates.json').write_text('{"gates": []}\n')
    if not (base / 'coverage.md').exists():
        (base / 'coverage.md').write_text('# Analysis coverage\n\nList actual modules, evidence, scope and status: reviewed / inventory_only / pending.\nNo architecture review has been recorded yet.\n')
    if not (base / 'evidence-files.json').exists():
        (base / 'evidence-files.json').write_text('{"files": []}\n')



def tree_bytes(path):
    if path.is_symlink():
        raise ValueError('baseline paths must not be symlinks')
    result = {}
    if path.exists():
        for p in sorted(path.rglob('*')):
            if p.is_symlink():
                raise ValueError('baseline must not contain symlinks')
            if p.is_file():
                result[str(p.relative_to(path))] = p.read_bytes()
    return result


def tree_digest(path):
    return hashlib.sha256(json.dumps({k: hashlib.sha256(v).hexdigest()
        for k, v in tree_bytes(path).items()}, sort_keys=True).encode()).hexdigest()


def fingerprint_head_only_change(current_bytes, candidate_bytes):
    try:
        current = json.loads(current_bytes)
        candidate = json.loads(candidate_bytes)
    except (json.JSONDecodeError, TypeError):
        return False
    if not isinstance(current, dict) or not isinstance(candidate, dict):
        return False
    old_head, new_head = current.pop('git_head', None), candidate.pop('git_head', None)
    return bool(old_head and new_head and old_head != new_head and current == candidate)


@contextmanager
def baseline_lock(root):
    # OS locks release on process death; no stale lock-file deletion race.
    work = root / '.agent-workflow'
    if work.is_symlink():
        raise ValueError('workflow directory must not be a symlink')
    work.mkdir(exist_ok=True)
    lock = work / '.baseline.lock'
    if lock.is_symlink():
        raise ValueError('lock must not be a symlink')
    with lock.open('a') as stream:
        if os.name == 'nt':
            import msvcrt
            stream.seek(0); stream.write('0'); stream.flush(); stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX)
        base, previous = work / 'project-baseline', work / '.baseline-previous'
        if previous.exists():
            tree_bytes(previous)
            if not base.exists():
                previous.rename(base)
            else:
                shutil.rmtree(previous)
        yield


def promote(root, candidate, keep):
    work = root / '.agent-workflow'
    base = work / 'project-baseline'
    current_tree, candidate_tree = tree_bytes(base), tree_bytes(candidate)
    if current_tree == candidate_tree:
        print('BASELINE_UNCHANGED: no backup created')
        return
    current_content = {key: value for key, value in current_tree.items() if key != 'fingerprint.json'}
    candidate_content = {key: value for key, value in candidate_tree.items() if key != 'fingerprint.json'}
    if (base.exists() and current_content == candidate_content
            and fingerprint_head_only_change(current_tree.get('fingerprint.json'), candidate_tree.get('fingerprint.json'))):
        source = candidate / 'fingerprint.json'
        if not source.is_file():
            raise ValueError('candidate fingerprint missing')
        os.replace(source, base / 'fingerprint.json')
        shutil.rmtree(candidate)
        print('BASELINE_FINGERPRINT_REFRESHED: baseline content unchanged; no backup created')
        return
    history = work / 'baseline-backups' / 'managed-v1'
    if history.is_symlink() or history.parent.is_symlink():
        raise ValueError('backup directory must not be a symlink')
    history.mkdir(parents=True, exist_ok=True)
    backup = None
    if base.exists():
        backup = history / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup.mkdir()
        try:
            shutil.copytree(base, backup / 'baseline')
            (backup / 'managed.json').write_text('{"version": 1}\n')
        except BaseException:
            shutil.rmtree(backup)
            raise
    previous = work / '.baseline-previous'
    if base.exists():
        base.rename(previous)
    try:
        candidate.rename(base)
    except BaseException:
        if previous.exists():
            previous.rename(base)
        if backup:
            shutil.rmtree(backup)
        raise
    if previous.exists():
        shutil.rmtree(previous)
    # Only our completed snapshots; legacy/manual/pinned backups are untouched.
    eligible = []
    for entry in sorted(history.iterdir(), reverse=True):
        if entry.is_symlink() or not entry.is_dir() or (entry / 'PINNED').exists():
            continue
        marker = entry / 'managed.json'
        if marker.is_file() and not marker.is_symlink() and marker.read_text().strip() == '{"version": 1}':
            eligible.append(entry)
    for entry in eligible[keep:]:
        tree_bytes(entry)
        shutil.rmtree(entry)
    print('BASELINE_UPDATED: retained up to %d unpinned managed backups' % keep)


def scan_baseline(root, keep, action):
    if not 1 <= keep <= 100:
        raise ValueError('--keep must be between 1 and 100')
    work = root / '.agent-workflow'
    base, draft = work / 'project-baseline', work / 'baseline-draft'
    tree_bytes(base)
    tree_bytes(draft)
    if action == 'scan-discard':
        if draft.exists():
            shutil.rmtree(draft)
        print('BASELINE_DRAFT_DISCARDED')
        return
    if action == 'scan-publish':
        state = json.loads((draft / 'state.json').read_text())
        if state['base_digest'] != tree_digest(base) or state['project'] != snapshot(root):
            raise ValueError('project or baseline changed during review; discard and prepare again')
        candidate = draft / 'baseline'
        tree_bytes(candidate)
        for name in ('architecture.md', 'conventions.md', 'examples.md', 'coverage.md', 'evidence-files.json', 'quality-gates.json'):
            if not (candidate / name).is_file() or not (candidate / name).read_text().strip():
                raise ValueError('draft missing required file: ' + name)
        inventory(root, candidate)
        validate_gates(root, json.loads((candidate / 'quality-gates.json').read_text()))
        candidate_snapshot = snapshot(root, candidate)
        if candidate_snapshot['profile'] == 'android':
            from module_context import discover_gradle_candidates
            discovered = discover_gradle_candidates(root)
            print('MODULE_CANDIDATES_RENDERED: modules=%d edges=%d gaps=%d' %
                  (len(discovered['modules']), len(discovered['edges']), len(discovered['gaps'])))
        module_index = root / '.agent-workflow/modules/index.json'
        if module_index.is_file():
            from module_context import render_graph
            graph = render_graph(root)
            print('MODULE_GRAPH_RENDERED: nodes=%d edges=%d' % (len(graph['nodes']), len(graph['edges'])))
        promote(root, candidate, keep)
        shutil.rmtree(draft)
        return
    if draft.exists():
        raise ValueError('unfinished baseline-draft exists; publish or explicitly scan-discard first')
    with tempfile.TemporaryDirectory(prefix='.baseline-stage-', dir=work) as tmp:
        stage = Path(tmp)
        candidate = stage / 'baseline'
        if base.exists():
            shutil.copytree(base, candidate)
        inventory(root, candidate)
        validate_gates(root, json.loads((candidate / 'quality-gates.json').read_text()))
        if action == 'scan-prepare':
            (stage / 'state.json').write_text(json.dumps({'base_digest': tree_digest(base), 'project': snapshot(root)}))
            stage.rename(draft)
            print('BASELINE_DRAFT_READY: ' + str(draft / 'baseline'))
            if snapshot(root, draft / 'baseline')['profile'] == 'android':
                from module_context import discover_gradle_candidates
                discovered = discover_gradle_candidates(root)
                print('MODULE_CANDIDATES_RENDERED: modules=%d edges=%d gaps=%d' %
                      (len(discovered['modules']), len(discovered['edges']), len(discovered['gaps'])))
        else:
            if snapshot(root, candidate)['profile'] == 'android':
                from module_context import discover_gradle_candidates
                discovered = discover_gradle_candidates(root)
                print('MODULE_CANDIDATES_RENDERED: modules=%d edges=%d gaps=%d' %
                      (len(discovered['modules']), len(discovered['edges']), len(discovered['gaps'])))
            module_index = root / '.agent-workflow/modules/index.json'
            if module_index.is_file():
                from module_context import render_graph
                graph = render_graph(root)
                print('MODULE_GRAPH_RENDERED: nodes=%d edges=%d' % (len(graph['nodes']), len(graph['edges'])))
            promote(root, candidate, keep)
            print('BASELINE_INVENTORIED: agent review required')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['scan', 'scan-prepare', 'scan-publish', 'scan-discard', 'verify', 'validate-gates', 'check'])
    parser.add_argument('root', type=Path)
    parser.add_argument('--feature', help='bind executed checks to one requirement baseline')
    parser.add_argument('--keep', type=int, default=3, help='recent managed backups to retain (1..100)')
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        raise ValueError('project directory not found')
    base = root / '.agent-workflow/project-baseline'
    fingerprint = base / 'fingerprint.json'
    if args.action in {'scan', 'scan-prepare', 'scan-publish', 'scan-discard'}:
        with baseline_lock(root):
            scan_baseline(root, args.keep, args.action)
        return 0
    if args.action == 'verify':
        if not fingerprint.exists():
            print('BASELINE_MISSING'); return 2
        return verify_baseline(root, json.loads(fingerprint.read_text()), snapshot(root))
    config = base / 'quality-gates.json'
    if not config.exists():
        print('QUALITY_UNAVAILABLE: no configuration'); return 2
    prepared = validate_gates(root, json.loads(config.read_text()))
    if args.action == 'validate-gates':
        print('QUALITY_CONFIG_VALID: %d selected gates; commands not executed' % len(prepared))
        if not prepared:
            print('SELECTION_REQUIRED: empty selection is not a passed quality check')
        return 0
    if not prepared:
        print('QUALITY_UNAVAILABLE: no selected gates'); return 2
    if args.feature:
        from revisions import binding
    before_baseline = binding(root, args.feature) if args.feature else None
    before_check = snapshot(root)
    results = []
    for gate, cmd, cwd, timeout in prepared:
        try:
            run = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout)
            result = {'name': gate.get('name', cmd[0]), 'command': cmd, 'test_ids': gate.get('test_ids', []), 'returncode': run.returncode, 'status': 'passed' if run.returncode == 0 else 'failed', 'stdout': run.stdout[-12000:], 'stderr': run.stderr[-12000:]}
        except (OSError, subprocess.TimeoutExpired) as exc:
            result = {'name': gate.get('name', cmd[0]), 'command': cmd, 'test_ids': gate.get('test_ids', []), 'status': 'unavailable', 'error': str(exc)}
        results.append(result)
        print(result['name'] + ': ' + result['status'])
    after_check = snapshot(root)
    after_baseline = binding(root, args.feature) if args.feature else None
    if after_check != before_check or after_baseline != before_baseline:
        print('PROJECT_CHANGED_DURING_CHECK: results do not certify the final project snapshot')
    report = {'tested_at': datetime.now(timezone.utc).isoformat(), 'project_snapshot': before_check, 'results': results, 'feature_baseline': before_baseline}
    (base / 'quality-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0 if after_check == before_check and after_baseline == before_baseline and all(x['status'] == 'passed' for x in results) else 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(2)
