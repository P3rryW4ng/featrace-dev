#!/usr/bin/env python3
"""Optional local timing journal; never acceptance evidence or a workflow gate."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from functools import wraps
from pathlib import Path
import re
import sys
import time

from impact import digest, git
from verification import save

CATEGORIES = ('test', 'verify', 'waiting', 'record_maintenance')


def usage(value):
    if value is None or value == {'tokens': None, 'cost': None, 'basis': 'unmeasured'}: return {'tokens': None, 'cost': None, 'basis': 'unmeasured'}
    if not isinstance(value, dict) or value.get('scope') != 'interval' or not isinstance(value.get('source'), str) or not value['source'].strip():
        raise ValueError('usage must identify actual interval-scoped source; account/session/context totals are not interval usage')
    if set(value) - {'scope', 'source', 'tokens', 'cost'}: raise ValueError('unsupported usage fields')
    tokens, cost = value.get('tokens'), value.get('cost')
    if tokens is not None:
        if not isinstance(tokens, dict) or not tokens or set(tokens) - {'input', 'output', 'cache_read', 'cache_write'}:
            raise ValueError('token categories required; context size is not usage')
        if any(type(n) is not int or n < 0 for n in tokens.values()): raise ValueError('invalid token count')
    if cost is not None:
        if (not isinstance(cost, dict) or set(cost) != {'value', 'currency'} or type(cost['value']) not in (int, float)
                or not math.isfinite(cost['value']) or cost['value'] < 0 or not re.fullmatch('[A-Z]{3}', str(cost['currency']))):
            raise ValueError('invalid measured cost/currency')
    return dict(value, tokens=tokens, cost=cost)


def location(root, feature_id):
    root = Path(root).resolve()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', feature_id): raise ValueError('invalid feature ID')
    if Path(git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != root:
        raise ValueError('project must be Git root')
    name = '.agent-workflow/scratch/' + feature_id + '/stage-cost.json'
    target = root
    for component in Path(name).parts:
        target = target / component
        if target.is_symlink(): raise ValueError('unsafe cost journal path')
    try: git(root, 'check-ignore', '--', name)
    except Exception as exc: raise ValueError('cost journal must be Git ignored; skip optional measurement if unavailable') from exc
    folder = root / '.agent-workflow/features' / feature_id
    if folder.is_symlink() or not folder.resolve().is_relative_to(root): raise ValueError('unsafe feature directory')
    from stage_view import records
    req = records.read_record(root, '.agent-workflow/features/' + feature_id + '/spec/requirements.json', {})
    if req.get('feature', {}).get('id') != feature_id: raise ValueError('feature mismatch')
    return root, folder, target


def load(path, feature_id):
    doc = json.loads(path.read_text()) if path.exists() else {'schema_version': 1, 'feature_id': feature_id, 'intervals': [], 'active': None}
    if doc.get('schema_version') != 1 or doc.get('feature_id') != feature_id or not isinstance(doc.get('intervals'), list):
        raise ValueError('invalid timing journal')
    for interval in doc['intervals']:
        if interval.get('category') not in CATEGORIES or type(interval.get('wall_seconds')) not in (int, float) or not math.isfinite(interval['wall_seconds']) or interval['wall_seconds'] < 0:
            raise ValueError('invalid recorded interval')
        usage(interval.get('usage'))
    return doc


def status(root, feature_id):
    _, _, path = location(root, feature_id); doc = load(path, feature_id)
    totals = {key: sum(r['wall_seconds'] for r in doc['intervals'] if r['category'] == key) for key in CATEGORIES}
    return {'feature_id': feature_id, 'interval_count': len(doc['intervals']), 'wall_seconds_by_category': totals,
            'active_category': None if doc.get('active') is None else doc['active']['category'],
            'intervals': doc['intervals'], 'not_measured': ['Agent CPU time', 'unreported intervals', 'unprovided run-scoped tokens/cost'],
            'note': 'Local ignored journal; measured elapsed intervals, not feature total time, proof of actual activity, acceptance or net benefit.'}


def journal_mutation(function):
    @wraps(function)
    def wrapped(root, folder, path, *args, **kwargs):
        checked_root, checked_folder, checked_path = location(root, folder.name)
        if Path(path).resolve() != checked_path.resolve() or Path(folder).resolve() != checked_folder.resolve():
            raise ValueError('cost mutation must use its ignored project-local journal')
        path.parent.mkdir(parents=True, exist_ok=True)
        lock = path.with_suffix('.lock')
        if lock.is_symlink(): raise ValueError('unsafe cost journal lock')
        with lock.open('a') as stream:
            try:
                if os.name == 'nt':
                    import msvcrt
                    stream.seek(0); stream.write('0'); stream.flush(); stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise ValueError('cost journal busy; skip optional measurement') from exc
            return function(checked_root, checked_folder, checked_path, *args, **kwargs)
    return wrapped


@journal_mutation
def mutate(root, folder, path, action, category=None, measured=None):
    doc = load(path, folder.name)
    now, wall = time.monotonic(), time.time()
    timestamp = datetime.now(timezone.utc).isoformat()
    if action == 'start':
        if doc.get('active') is not None: raise ValueError('timing interval already active; stop before switching category')
        if category not in CATEGORIES: raise ValueError('invalid timing category')
        doc['active'] = {'category': category, 'started_at': timestamp, 'monotonic': now, 'wall_clock': wall}
    else:
        active = doc.get('active')
        if not isinstance(active, dict) or active.get('category') not in CATEGORIES: raise ValueError('no valid active timing interval')
        elapsed = now - active['monotonic']
        if elapsed < 0 or abs(elapsed - (wall - active['wall_clock'])) > 30:
            raise ValueError('clock/boot changed; preserve journal and report interval unavailable')
        doc['intervals'].append({'category': active['category'], 'started_at': active['started_at'], 'ended_at': timestamp,
                                 'wall_seconds': elapsed, 'usage': usage(measured)})
        doc['active'] = None
    path.parent.mkdir(parents=True, exist_ok=True); save(path, doc)
    return status(root, folder.name)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('action', choices=('start', 'stop', 'status'))
    p.add_argument('root', type=Path); p.add_argument('feature_id'); p.add_argument('--category', choices=CATEGORIES); p.add_argument('--usage', type=Path)
    a = p.parse_args()
    try:
        root, folder, path = location(a.root, a.feature_id)
        if a.action == 'status': result = status(root, a.feature_id)
        else: result = mutate(root, folder, path, a.action, a.category, None if not a.usage else json.loads(a.usage.read_text()))
        print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('STAGE_COST_UNAVAILABLE: ' + str(exc), file=sys.stderr); return 1


if __name__ == '__main__': sys.exit(main())
