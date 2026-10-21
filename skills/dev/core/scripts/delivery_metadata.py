#!/usr/bin/env python3
"""Typed publication observation; never product authority or a new delivery pass."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

from check_runs import safe, read, save
from impact import git
from verification_policy import full_revision, need

FIELDS = {'schema_version','feature_id','code_revision','tracking_ref','tracking_revision','observed_at'}


def validate(value, feature_id):
    need(isinstance(value,dict) and set(value) == FIELDS and type(value['schema_version']) is int and value['schema_version'] == 1 and value['feature_id'] == feature_id, 'unsupported delivery metadata')
    for key in ('code_revision','tracking_revision'):
        need(isinstance(value[key],str) and re.fullmatch(r'[a-f0-9]{40}|[a-f0-9]{64}',value[key]), 'invalid publication revision')
    need(isinstance(value['tracking_ref'],str) and re.fullmatch(r'refs/remotes/[A-Za-z0-9_.\-/]+',value['tracking_ref']) and '..' not in value['tracking_ref'] and not value['tracking_ref'].endswith('/HEAD'), 'explicit remote-tracking ref required')
    need(isinstance(value['observed_at'],str), 'publication time required')
    try: instant=datetime.fromisoformat(value['observed_at'])
    except ValueError: raise ValueError('invalid publication time')
    need(instant.tzinfo is not None, 'timezone required')
    return value


def view(root, folder):
    path=safe(root,folder/'delivery-metadata.json')
    if not path.exists(): return None
    value=validate(read(root,path),folder.name)
    full_revision(root,value['code_revision'])
    # Tracking may move or be deleted. Original object/observation is history,
    # not a fresh network check and not evidence of remote state now.
    git(root,'cat-file','-e',value['tracking_revision']+'^{commit}')
    result=dict(value)
    try:
        git(root,'merge-base','--is-ancestor',value['code_revision'],value['tracking_revision'])
        result['publication_observation']='contained_in_observed_tracking_ref'
    except ValueError: result['publication_observation']='not_contained_in_observed_tracking_ref'
    result['authority']='feature.status; this is a historical local tracking observation, not a live remote query'
    return result


def record(root,folder,revision,tracking_ref):
    from acceptance_contract import mutation
    with mutation(root,folder):
        revision=full_revision(root,revision)
        # Validate ref grammar before passing even a prefixed ref to Git.
        trial=dict(schema_version=1,feature_id=folder.name,code_revision=revision,
                   tracking_ref=tracking_ref,tracking_revision=revision,observed_at=datetime.now(timezone.utc).isoformat())
        validate(trial,folder.name)
        resolved=git(root,'rev-parse','--verify',tracking_ref+'^{commit}').decode().strip()
        trial['tracking_revision']=resolved
        validate(trial,folder.name)
        save(root,folder/'delivery-metadata.json',trial)
    return view(root,folder)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('feature_id')
    p.add_argument('--revision');p.add_argument('--tracking-ref')
    args=p.parse_args();root=args.root.resolve();folder=safe(root,'.agent-workflow/features/'+args.feature_id)
    if bool(args.revision)!=bool(args.tracking_ref):p.error('revision and tracking-ref must be supplied together')
    value=record(root,folder,args.revision,args.tracking_ref) if args.revision else view(root,folder)
    print(json.dumps(value,ensure_ascii=False,indent=2));return 0


if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,KeyError,TypeError) as exc:print(str(exc),file=sys.stderr);sys.exit(2)
