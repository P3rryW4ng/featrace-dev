#!/usr/bin/env python3
"""Install a self-contained copy; update only unchanged installations we own."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
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

def source_identity(development=False):
    files=hashes(SOURCE);version=(REPO/'VERSION').read_text().strip()
    def git(*args):
        result=subprocess.run(['git','-C',str(REPO),*args],capture_output=True,text=True)
        return result.stdout.strip() if result.returncode==0 else None
    commit=git('rev-parse','HEAD')
    package_digest=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
    if development:
        return {'version':version+'+dev.'+(commit[:12] if commit else 'uncommitted')+'.'+package_digest[:12],
                'base_version':version,'channel':'development','source_commit':commit,'installer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'content_sha256':package_digest,
                'boundary':'Development checkout, not a formal release.'}
    manifest=REPO/'release.json'
    if not manifest.is_file() or manifest.is_symlink():raise ValueError('RELEASE_DESCRIPTOR_REQUIRED; development trials require --development')
    descriptor=json.loads(manifest.read_text())
    if (descriptor.get('channel')!='release' or descriptor.get('version')!=version or descriptor.get('files')!=files
            or descriptor.get('installer_sha256')!=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()):
        raise ValueError('RELEASE_CONTENT_MISMATCH')
    ref='refs/heads/release/'+version
    tag='refs/tags/v'+version
    pinned=git('rev-parse',tag+'^{commit}') or git('rev-parse',ref+'^{commit}')
    if not commit or pinned!=commit:raise ValueError('RELEASE_REF_MISMATCH')
    # Runtime + descriptor + installer + VERSION must all be tracked and match this immutable commit.
    for name in ['VERSION','scripts/install.py','release.json']+['skills/dev/'+p for p in files]:
        if git('ls-files','--error-unmatch','--',name) is None:raise ValueError('RELEASE_INPUT_UNTRACKED')
    changed=git('status','--porcelain','--untracked-files=all','--','VERSION','scripts/install.py','release.json','skills/dev')
    if changed is None or changed:raise ValueError('RELEASE_WORKTREE_CHANGED')
    return {'version':version,'channel':'release','source_commit':commit,'installer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'content_sha256':package_digest,
            'release_ref':tag if git('rev-parse',tag+'^{commit}') else ref,
            'boundary':'Matches the local pinned release ref and descriptor; not a signed remote-origin attestation.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent', choices=['claude', 'codex', 'both'], default='both')
    parser.add_argument('--home', type=Path, default=Path.home(), help='Override home for isolated testing')
    parser.add_argument('--update', action='store_true', help='Update our unchanged installs, keeping backups')
    parser.add_argument('--development',action='store_true',help='Explicit candidate install with a development identity; never the base release version')
    parser.add_argument('--uninstall', action='store_true', help='Move our unchanged installs to backups')
    args = parser.parse_args()
    if args.update and args.uninstall:
        parser.error('--update and --uninstall are mutually exclusive')
    home = args.home.expanduser().resolve()
    locations = {'claude': home / '.claude/skills/dev', 'codex': home / '.agents/skills/dev'}
    targets = list(locations.values()) if args.agent == 'both' else [locations[args.agent]]
    identity=source_identity(args.development) if not args.uninstall else None
    source_hash=hashes(SOURCE) if not args.uninstall else {}
    version=identity['version'] if identity else None
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
                    and old.get('package') == PACKAGE and old.get('version') == version and old.get('source')==identity):
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
                if hashes(temp)!=source_hash:raise ValueError('SOURCE_MOVED_DURING_INSTALL')
                if source_identity(args.development)!=identity:raise ValueError('SOURCE_IDENTITY_MOVED')
                (temp / MARKER).write_text(json.dumps({'package': PACKAGE, 'version': version, 'files': hashes(temp),'source':identity}, indent=2) + '\n')
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
        print('FeatraceDev by Perry Wang | Claude: /dev | Codex: $dev. Open a new agent session if not discovered.')
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, TypeError) as exc:
        print('INSTALL_ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(1)
