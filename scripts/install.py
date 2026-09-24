#!/usr/bin/env python3
"""Install a self-contained copy; update only unchanged installations we own."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import uuid

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / 'skills/dev'
MARKER = '.feature-delivery-install.json'
PACKAGE = 'featrace-dev'
LEGACY_PACKAGE = 'feature-delivery-skill'

def hashes(folder):
    result = {}
    for p in sorted(folder.rglob('*')):
        if '__pycache__' in p.parts or p.suffix == '.pyc':
            continue
        if p.is_symlink():
            raise ValueError('Symlink in skill tree: ' + str(p))
        if p.is_file() and p.name != MARKER:
            result[p.relative_to(folder).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent', choices=['claude', 'codex', 'both'], default='both')
    parser.add_argument('--home', type=Path, default=Path.home(), help='Override home for isolated testing')
    parser.add_argument('--update', action='store_true', help='Update our unchanged installs, keeping backups')
    parser.add_argument('--uninstall', action='store_true', help='Move our unchanged installs to backups')
    args = parser.parse_args()
    if args.update and args.uninstall:
        parser.error('--update and --uninstall are mutually exclusive')
    home = args.home.expanduser().resolve()
    locations = {'claude': home / '.claude/skills/dev', 'codex': home / '.agents/skills/dev'}
    targets = list(locations.values()) if args.agent == 'both' else [locations[args.agent]]
    source_hash = hashes(SOURCE)
    version = (REPO / 'VERSION').read_text().strip()
    actions = []
    # Preflight all destinations before mutation: never overwrite someone else's dev skill.
    for target in targets:
        if target.is_symlink():
            raise ValueError('Refusing existing symlink: ' + str(target))
        if target.exists():
            marker = target / MARKER
            if not marker.is_file():
                raise ValueError('Existing unowned skill; choose a different install location or move it yourself: ' + str(target))
            old = json.loads(marker.read_text())
            if old.get('package') not in {PACKAGE, LEGACY_PACKAGE} or hashes(target) != old.get('files'):
                raise ValueError('Existing skill is unowned or locally modified; preserve/reconcile changes first: ' + str(target))
            if (not args.uninstall and hashes(target) == source_hash
                    and old.get('package') == PACKAGE and old.get('version') == version):
                print('ALREADY_INSTALLED: ' + str(target)); continue
            if not args.update and not args.uninstall:
                raise ValueError('New package differs; rerun with --update: ' + str(target))
        elif args.uninstall:
            print('NOT_INSTALLED: ' + str(target)); continue
        actions.append(target)
    for target in actions:
        target.parent.mkdir(parents=True, exist_ok=True)
        backup = None
        temp = None
        if not args.uninstall:
            temp = Path(tempfile.mkdtemp(prefix='.feature-delivery-stage-', dir=target.parent))
            try:
                shutil.copytree(SOURCE, temp, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                (temp / MARKER).write_text(json.dumps({'package': PACKAGE, 'version': version, 'files': hashes(temp)}, indent=2) + '\n')
            except Exception:
                shutil.rmtree(temp); raise
        try:
            if target.exists():
                # Backups live outside discovery paths; they must not load as duplicate skills.
                label = 'claude' if '.claude' in target.parts else 'codex'
                backup = home / '.feature-delivery/backups' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + label + '-' + uuid.uuid4().hex[:8])
                backup.parent.mkdir(parents=True, exist_ok=True)
                target.rename(backup)
            if temp:
                temp.rename(target)
        except Exception:
            if backup and backup.exists() and not target.exists():
                backup.rename(target)
            if temp and temp.exists():
                shutil.rmtree(temp)
            raise
        print(('UNINSTALLED: ' if args.uninstall else 'INSTALLED: ') + str(target))
        if backup:
            print('BACKUP: ' + str(backup))
    if not args.uninstall:
        print('FeatraceDev by Perry Wang | Claude: /dev scan | Codex: $dev scan. Open a new agent session if not discovered.')
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, TypeError) as exc:
        print('INSTALL_ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(1)
