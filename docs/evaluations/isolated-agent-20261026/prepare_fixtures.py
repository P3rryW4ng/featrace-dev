#!/usr/bin/env python3
"""Restore only synthetic initial fixture files into a new, explicit destination."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    root=args.destination.expanduser().absolute()
    if root.exists():raise SystemExit('Destination must not exist; original exercises are never overwritten')
    data=json.loads((Path(__file__).parent/'fixture-source.json').read_text())
    for case,entry in data['cases'].items():
        if not case.startswith('SC-') or '/' in case:raise SystemExit('Invalid case name')
        for name,key in entry['files'].items():
            path=Path(name)
            if path.is_absolute() or '..' in path.parts or '.git' in path.parts or name.startswith('.featrace'):
                raise SystemExit('Unsafe fixture source path')
            if hashlib.sha256(data['blobs'][key].encode()).hexdigest()!=key:raise SystemExit('Fixture content changed')
    root.mkdir(parents=True)
    for case,entry in data['cases'].items():
        target=root/case;target.mkdir()
        for name,key in entry['files'].items():
            p=target/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data['blobs'][key].encode())
        for command in [('init','-q'),('config','user.name','Synthetic exercise'),('config','user.email','exercise@example.invalid'),('add','.'),('commit','-qm','Synthetic project baseline')]:
            subprocess.run(['git','-C',str(target),*command],check=True,capture_output=True)
    print(json.dumps({'cases':len(data['cases']),'destination':str(root),'scope':'Synthetic initial projects only; no Agent or browser launched'}))


if __name__=='__main__':main()
