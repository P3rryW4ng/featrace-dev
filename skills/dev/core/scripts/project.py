#!/usr/bin/env python3
"""Small cross-platform manifest inventory and explicit quality-command runner."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

SKIP = {'.git', '.agent-workflow', '.agents', '.claude', 'node_modules', 'build', '.gradle', '.venv', 'venv', 'vendor', 'Pods', 'DerivedData', '__pycache__'}
NAMES = {'settings.gradle', 'settings.gradle.kts', 'build.gradle', 'build.gradle.kts', 'libs.versions.toml', 'gradle.lockfile', 'gradle-wrapper.properties', 'Package.swift', 'project.pbxproj', 'package.json', 'package-lock.json', 'pnpm-lock.yaml', 'yarn.lock', 'go.mod', 'go.sum', 'pyproject.toml', 'requirements.txt', 'pom.xml', 'Cargo.toml', 'Cargo.lock', 'Makefile', 'CMakeLists.txt'}

def snapshot(root):
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
    return {'version': 1, 'profile': 'android' if android else 'generic', 'git_head': git.stdout.strip() if git.returncode == 0 else '', 'files': files}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['scan', 'verify', 'check'])
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        raise ValueError('project directory not found')
    base = root / '.agent-workflow/project-baseline'
    fingerprint = base / 'fingerprint.json'
    if args.action == 'scan':
        data = snapshot(root)
        base.mkdir(parents=True, exist_ok=True)
        fingerprint.write_text(json.dumps(data, indent=2) + '\n')
        files = '\n'.join('- ' + p for p in sorted(data['files']))
        (base / 'inventory.md').write_text('# Manifest inventory\n\nProfile: ' + data['profile'] + '\n\n' + files + '\n')
        for name, title in [('architecture', 'Architecture'), ('conventions', 'Conventions'), ('examples', 'Reuse examples')]:
            path = base / (name + '.md')
            if not path.exists():
                path.write_text('# ' + title + '\n\nAgent review required. Cite actual project files.\n')
        if not (base / 'quality-gates.json').exists():
            (base / 'quality-gates.json').write_text('{"gates": []}\n')
        print('BASELINE_INVENTORIED: ' + data['profile'] + '; agent review required')
        return 0
    if args.action == 'verify':
        if not fingerprint.exists():
            print('BASELINE_MISSING'); return 2
        if json.loads(fingerprint.read_text()) != snapshot(root):
            print('BASELINE_STALE: review changed project files and rescan'); return 3
        print('BASELINE_VALID: manifest fingerprint only'); return 0
    config = base / 'quality-gates.json'
    if not config.exists():
        print('QUALITY_UNAVAILABLE: no configuration'); return 2
    gates = json.loads(config.read_text()).get('gates', [])
    if not isinstance(gates, list) or not gates:
        print('QUALITY_UNAVAILABLE: no configured gates'); return 2
    prepared = []
    for gate in gates:
        cmd = gate.get('command')
        if not isinstance(cmd, list) or not cmd or not all(isinstance(x, str) and x for x in cmd):
            raise ValueError('gate command must be a non-empty argument array')
        cwd = (root / gate.get('cwd', '.')).resolve()
        cwd.relative_to(root)
        timeout = gate.get('timeout_seconds', 600)
        if not isinstance(timeout, (int, float)) or not 0 < timeout <= 86400:
            raise ValueError('invalid gate timeout')
        prepared.append((gate, cmd, cwd, timeout))
    results = []
    for gate, cmd, cwd, timeout in prepared:
        try:
            run = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout)
            result = {'name': gate.get('name', cmd[0]), 'command': cmd, 'returncode': run.returncode, 'status': 'passed' if run.returncode == 0 else 'failed', 'stdout': run.stdout[-12000:], 'stderr': run.stderr[-12000:]}
        except (OSError, subprocess.TimeoutExpired) as exc:
            result = {'name': gate.get('name', cmd[0]), 'command': cmd, 'status': 'unavailable', 'error': str(exc)}
        results.append(result)
        print(result['name'] + ': ' + result['status'])
    report = {'tested_at': datetime.now(timezone.utc).isoformat(), 'project_snapshot': snapshot(root), 'results': results}
    (base / 'quality-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0 if all(x['status'] == 'passed' for x in results) else 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(2)
