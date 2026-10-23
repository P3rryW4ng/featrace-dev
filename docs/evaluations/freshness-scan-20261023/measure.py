"""Synthetic read-cost measurement; no runtime edits, persistent cache or business tests."""
from pathlib import Path
from tempfile import TemporaryDirectory
import copy
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path('/Users/mac/Entrepôt/featrace-dev')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'skills/dev/core/scripts'))
import task_workflow as w


def git(root, *args):
    subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True)


def measure(source_files, file_bytes, external_files, external_bytes):
    with TemporaryDirectory(prefix='featrace-scan-bench-') as temporary:
        base = Path(temporary).resolve()
        root = base/'project';root.mkdir()
        toolchain = base/'synthetic-toolchain';toolchain.mkdir()
        git(root, 'init', '-q')
        git(root, 'config', 'user.name', 'Synthetic measurement')
        git(root, 'config', 'user.email', 'synthetic@example.invalid')
        (root/'src').mkdir()
        for i in range(source_files):
            (root/'src'/f'file-{i}.txt').write_bytes(bytes([65+i % 26])*file_bytes)
        for i in range(external_files):
            (toolchain/f'dependency-{i}.bin').write_bytes(bytes([i])*external_bytes)
        w.task_policy.prepare(root, {'policy_contract':1,'authority':'Synthetic local measurement only',
                                    'timezone':'UTC','retention_days':7,'cleanup':'manual','handoff':None,'rules':[]}, w.git)
        git(root, 'add', '.')
        git(root, 'commit', '-qm', 'Synthetic benchmark inputs')
        w.begin(root, 'BENCH', 'Measure identity reads; no business correctness claim')
        plan = {'reason':'Synthetic checks deliberately share all selected inputs',
                'categories':['configuration'],'scope':['src/file-0.txt'],'exclusions':{},'constraints':{},'unknowns':[],
                'criteria':[{'id':'C1','expected':'Synthetic command completes','kind':'changed','inputs':['src/file-0.txt']}],
                'checks':[], 'review':{'independent':False,'reason':'Timing fixture only'}}
        for i in range(8):
            plan['checks'].append({'id':f'CHECK-{i}','argv':[sys.executable,'-c',f'print("synthetic check {i}")'],
                                   'inputs':[],'input_sets':[{'kind':'git_tree','path':'src'}],
                                   'external_inputs':[{'kind':'tree','path':str(toolchain)}],
                                   'covers':['C1'],'reason':'Shared-input read-cost fixture','timeout':5,
                                   'environment':{'kind':'local','target':'Synthetic local process'}})
        w.set_plan(root, 'BENCH', plan)
        signature = w.task_inputs.signature
        events = []
        def timed_signature(*args, **kwargs):
            tic=time.perf_counter();value=signature(*args, **kwargs)
            events.append({'seconds':time.perf_counter()-tic,'bytes':value['bytes'],'entries':value['entries']})
            return value
        w.task_inputs.signature = timed_signature
        try:
            tic=time.perf_counter()
            for i in range(8):w.run_check(root, 'BENCH', f'CHECK-{i}')
            initial={'wall_seconds':time.perf_counter()-tic,'fingerprints':copy.deepcopy(events)}
            w.assess(root, 'BENCH','C1','supported','Synthetic command exit only; no real test claim')
            rows=[]
            for count in (1,4,8):
                selected=copy.deepcopy(plan);selected['checks']=selected['checks'][:count]
                w.set_plan(root,'BENCH',selected)
                for repetition in range(3):
                    events.clear()
                    before={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (root/'.featrace').rglob('*') if p.is_file()}
                    tic=time.perf_counter();status=w.view(root,'BENCH');elapsed=time.perf_counter()-tic
                    after={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in (root/'.featrace').rglob('*') if p.is_file()}
                    rows.append({'checks':count,'repetition':repetition+1,'wall_seconds':elapsed,
                                 'fingerprint_seconds':sum(x['seconds'] for x in events),'fingerprint_calls':len(events),
                                 'logical_bytes_hashed':sum(x['bytes'] for x in events),'state':status['state'],
                                 'readonly':before==after})
            # Mutation is in an existing selected input: member list stays the same.
            (root/'src/file-1.txt').write_bytes(b'Changed selected content\n')
            events.clear();status=w.view(root,'BENCH')
            mutation={'eligible':status['eligible'],'blocking_checks':[b for b in status['blockers'] if b.startswith('CHECK:')],
                      'fingerprint_calls':len(events)}
        finally:
            w.task_inputs.signature=signature
        return {'source_files':source_files,'source_bytes':source_files*file_bytes,
                'external_files':external_files,'external_bytes':external_files*external_bytes,
                'initial_execution':initial,'status_queries':rows,'selected_input_mutation':mutation}


def observation_probe():
    # Existing fixture defines a bounded synthetic task; no project changes outside temp.
    sys.path.insert(0,str(ROOT/'tests'))
    from test_task_workflow import TaskWorkflowTests
    fixture=TaskWorkflowTests();fixture.setUp()
    try:
        fixture.plan['checks']=[];fixture.refresh()
        at=w.now()
        fixture.observe('C1','runtime_observation',at,'Synthetic capture; environment later changes independently',['app.py'])
        fixture.support()
        with __import__('unittest.mock',fromlist=['patch']).patch.object(w,'datetime') as clock:
            from datetime import datetime as actual_datetime, timedelta
            clock.now.side_effect=lambda *args:actual_datetime.now(timezone.utc)+timedelta(days=30)
            clock.fromisoformat.side_effect=actual_datetime.fromisoformat
            status=w.view(fixture.root,fixture.ident)
        return {'simulated_days_elapsed':30,'eligible_with_unchanged_selected_files':status['eligible'],
                'interpretation':'Existing observation has no expiry. This is appropriate only for an as-of claim, not proof a live remote state remains current.'}
    finally:fixture.doCleanups()


if __name__=='__main__':
    files=[ROOT/'skills/dev/core/scripts'/n for n in ('task_workflow.py','task_inputs.py','task_policy.py')]
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    started=datetime.now(timezone.utc).isoformat()
    data={'scope':'Synthetic current-source identity-cost measurement; warm OS cache, no cold-cache or Android/real SDK claims.',
          'started_at':started,'inputs':before,'datasets':[measure(32,65536,2,1048576),measure(128,524288,8,2097152)],
          'observation_probe':observation_probe()}
    data['source_unchanged']=before=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    data['finished_at']=datetime.now(timezone.utc).isoformat()
    (OUT/'results.json').write_text(json.dumps(data,indent=2)+'\n')
    for dataset in data['datasets']:
        for count in (1,4,8):
            rows=[r for r in dataset['status_queries'] if r['checks']==count]
            print(json.dumps({'dataset_bytes':dataset['source_bytes']+dataset['external_bytes'],'checks':count,
                              'wall_seconds':[round(r['wall_seconds'],6) for r in rows],
                              'hash_seconds':[round(r['fingerprint_seconds'],6) for r in rows],
                              'calls':[r['fingerprint_calls'] for r in rows],
                              'logical_bytes':[r['logical_bytes_hashed'] for r in rows]}))
    print(json.dumps({'source_unchanged':data['source_unchanged'],'observation_probe':data['observation_probe']}))
