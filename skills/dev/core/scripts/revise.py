#!/usr/bin/env python3
"""Version confirmed requirement meaning; proposals remain separate from live requirements."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from feature_lifecycle import read_record, require_active
from revisions import apply_changes, digest, inspect, nonempty, semantics, validate_proposal


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_save(path, doc, original=None):
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as f:
            temp = Path(f.name)
            json.dump(doc, f, ensure_ascii=False, indent=2)
            f.write('\n')
        if original is not None and path.read_bytes() != original:
            raise ValueError('Record changed during operation; inspect before retrying')
        if original is None:
            os.link(temp, path)  # Exclusive creation; never overwrite a proposal.
        else:
            os.replace(temp, path)
    finally:
        if temp and temp.exists(): temp.unlink()


def run_check(root, fid, script, *options):
    out = subprocess.run([sys.executable, str(Path(__file__).with_name(script)), *options, str(root), fid],
                         capture_output=True, text=True)
    if out.returncode:
        raise ValueError(script + ' failed:\n' + out.stdout + out.stderr)


def confirmations(folder, record):
    if not record['decision_ids']:
        raise ValueError('Apply needs an approved decision reference; later date alone is not authority')
    doc = json.loads((folder/'decisions.json').read_text())
    if doc.get('feature_id') != record['feature_id'] or not isinstance(doc.get('decisions'), list):
        raise ValueError('Invalid decision record')
    selected = []
    for did in record['decision_ids']:
        matches = [x for x in doc['decisions'] if isinstance(x, dict) and x.get('id') == did]
        if len(matches) != 1 or matches[0].get('status') != 'approved' or not nonempty(matches[0].get('chosen')):
            raise ValueError('Revision decision not approved: ' + did)
        selected.append(matches[0])
    return selected


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('init', 'propose', 'apply', 'cancel', 'verify', 'status'))
    p.add_argument('project', type=Path)
    p.add_argument('feature_id')
    p.add_argument('--input', type=Path)
    p.add_argument('--revision')
    p.add_argument('--reason', default='')
    p.add_argument('--code-revision', default='')
    p.add_argument('--evidence', default='delivery-report.md')
    p.add_argument('--source', type=Path, action='append', default=[])
    args = p.parse_args()
    root = args.project.resolve()
    path, original, doc = read_record(root, args.feature_id)
    folder = path.parent.parent
    b, records, pending = inspect(folder, doc)
    if args.action == 'status':
        print(json.dumps({'baseline_version': b['version'] if b else None,
                          'verified_version': max((x['version'] for x in b['deliveries']), default=0) if b else None,
                          'pending': [x['id'] for x in pending]}, indent=2))
        return 0
    require_active(doc['feature'])
    if args.action == 'init':
        if b:
            print('BASELINE_ALREADY_REGISTERED'); return 0
        if not args.reason.strip(): raise ValueError('Baseline confirmation reason required')
        run_check(root, args.feature_id, 'validate-feature.py', '--stage', 'develop')
        sem = semantics(doc['requirements'])
        # Validate semantic shape without requiring an actual revision.
        if not sem or any(x['status'] not in {'confirmed', 'deprecated'} for x in sem):
            raise ValueError('Confirm original requirements before registering a baseline')
        b = {'version': 1, 'digest': digest(sem), 'initial_requirements': sem,
             'registered_at': now(), 'reason': args.reason.strip(), 'applied': [], 'cancelled': [], 'deliveries': []}
        doc['feature']['baseline'] = b
        if doc['feature'].get('status') == 'complete': doc['feature']['status'] = 'provisional'
    elif b is None:
        raise ValueError('Register confirmed baseline v1 with init first; legacy features are not migrated implicitly')
    elif args.action == 'propose':
        if args.input is None: raise ValueError('Proposal JSON input required')
        record = json.loads(args.input.read_text())
        if not isinstance(record, dict): raise ValueError('Proposal input must be an object')
        numbers = [int(k[4:]) for k in records]
        record.update(id='CHG-%03d' % (max(numbers, default=0)+1), feature_id=args.feature_id)
        validate_proposal(record, args.feature_id)
        if record['base_version'] != b['version'] or record['base_digest'] != b['digest']:
            raise ValueError('Proposal is based on a stale baseline')
        apply_changes(doc['requirements'], record['changes'])
        # Duplicate input does not generate repeated revisions (including applied/cancelled ones).
        comparable = lambda x: {k:v for k,v in x.items() if k not in {'id', 'created_at', 'source_files'}}
        for old in records.values():
            if comparable(old) == comparable(record) and not args.source:
                print('REVISION_ALREADY_RECORDED: ' + old['id']); return 0
        if pending: raise ValueError('One open revision at a time; apply or cancel it first')
        if b['version'] > 1 and not any(x['version'] == b['version'] for x in b['deliveries']):
            raise ValueError('Finish and verify the current revision before proposing another')
        record['source_files'] = []
        sources = []
        for source in args.source:
            if source.is_symlink() or not source.is_file(): raise ValueError('Source must be a regular file')
            data = source.read_bytes()
            sha = hashlib.sha256(data).hexdigest()
            extension = source.suffix if source.suffix.isascii() else '.bin'
            relative = 'sources/revisions/' + sha + extension
            sources.append((relative, data))
            record['source_files'].append({'path': relative, 'sha256': sha})
        # Validate paths before writing any source; byte-identical originals are reused.
        for relative, data in sources:
            target = folder/relative
            if target.resolve() != target: raise ValueError('Symlinked source path rejected')
            if target.exists() and target.read_bytes() != data: raise ValueError('Source digest collision')
        for relative, data in sources:
            target = folder/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                with target.open('xb') as f: f.write(data)
        record['created_at'] = now()
        directory = folder/'revisions'
        directory.mkdir(exist_ok=True)
        if path.read_bytes() != original: raise ValueError('Baseline changed; inspect before retrying')
        atomic_save(directory/(record['id']+'.json'), record)
        print('REVISION_PROPOSED: ' + record['id']); return 0
    elif args.action in {'apply', 'cancel'}:
        if len(pending) != 1 or pending[0]['id'] != args.revision:
            raise ValueError('Name the current pending revision explicitly')
        record = pending[0]
        if args.action == 'cancel':
            if not args.reason.strip(): raise ValueError('Cancellation reason required')
            b['cancelled'].append({'id': record['id'], 'proposal_digest': digest(record), 'at': now(), 'reason': args.reason.strip()})
        else:
            if record['base_version'] != b['version'] or record['base_digest'] != b['digest']:
                raise ValueError('Stale revision; cancel and create a reviewed replacement')
            decisions = confirmations(folder, record)
            for source in record.get('source_files', []):
                target = folder/source['path']
                if not target.resolve().is_relative_to(folder) or hashlib.sha256(target.read_bytes()).hexdigest() != source['sha256']:
                    raise ValueError('Revision source unavailable or changed')
            doc['requirements'] = apply_changes(doc['requirements'], record['changes'])
            b['version'] += 1
            b['digest'] = digest(semantics(doc['requirements']))
            b['applied'].append({'id': record['id'], 'version': b['version'], 'proposal_digest': digest(record),
                                 'result_digest': b['digest'], 'decision_digest': digest(decisions), 'at': now()})
            doc['feature']['status'] = 'provisional'
    elif args.action == 'verify':
        if pending: raise ValueError('Resolve pending revision before verifying delivery')
        if not args.code_revision.strip(): raise ValueError('Tested code revision required')
        report = folder/args.evidence
        if Path(args.evidence).is_absolute() or report.resolve() != report or not report.resolve().is_relative_to(folder):
            raise ValueError('Evidence must be a feature-relative regular report')
        content = report.read_bytes()
        if not content.strip(): raise ValueError('Empty delivery report')
        run_check(root, args.feature_id, 'validate-feature.py', '--stage', 'check')
        run_check(root, args.feature_id, 'audit-delivery.py')
        quality = json.loads((root/'.agent-workflow/project-baseline/quality-report.json').read_text())
        selected = {tid for item in quality['results'] for tid in item.get('test_ids', [])}
        if b['applied']:
            latest = records[b['applied'][-1]['id']]
            if any(tid not in selected for tid in latest['test_ids']):
                raise ValueError('Revision test IDs were not selected by passed checks; include manual-only coverage in the report, not test_ids')
        tasks = json.loads((folder/'tasks.json').read_text())['tasks']
        states = doc['feature'].get('source_status', {})
        if (not tasks or any(x.get('status') != 'done' for x in tasks)
                or any(states.get(k) not in {'present','not_applicable'} for k in ('prd','api','figma'))):
            raise ValueError('Complete tasks and resolve required sources before verifying')
        head = subprocess.run(['git','-C',str(root),'rev-parse','HEAD'], capture_output=True, text=True)
        requested = subprocess.run(['git','-C',str(root),'rev-parse','--verify',args.code_revision+'^{commit}'], capture_output=True,text=True)
        if head.returncode or requested.returncode or head.stdout.strip() != requested.stdout.strip():
            raise ValueError('Tested revision must resolve to current Git HEAD for this verification')
        event = {'version': b['version'], 'requirements_digest': b['digest'], 'code_revision': head.stdout.strip(),
                 'evidence': args.evidence, 'evidence_sha256': hashlib.sha256(content).hexdigest(), 'at': now()}
        b['deliveries'].append(event)
        # Completion still requires the Agent to check actual meaning/UI and acceptance.
    atomic_save(path, doc, original)
    print('REVISION_' + args.action.upper() + ': baseline v' + str(b['version']))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        print('REVISION_ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(1)
