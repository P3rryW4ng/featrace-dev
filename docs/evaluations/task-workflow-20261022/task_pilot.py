"""Synthetic scale and isolated installed-CLI probes; no business project."""
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT=Path('/Users/mac/Entrepôt/featrace-dev')
OUT=Path('/tmp/featrace-task-pilot');OUT.mkdir(exist_ok=True)
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'skills/dev/core/scripts')]
from test_task_workflow import TaskWorkflowTests
import task_workflow as w

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def installed_cli(script,root,*args):
    p=subprocess.run([sys.executable,str(script),args[0],str(root),*args[1:]],capture_output=True,text=True)
    if p.returncode:raise RuntimeError('Installed CLI failed: '+p.stdout+p.stderr)
    return json.loads(p.stdout)

fixture=TaskWorkflowTests();fixture.setUp()
try:
    root=fixture.root;start=time.perf_counter();code_sha=sha(root/'app.py');sizes=[]
    for i in range(200):
        ident=fixture.ident if i==0 else f'SCALE-{i:04}'
        if i:
            w.begin(root,ident,'Synthetic local label change, scale sample')
            w.set_plan(root,ident,fixture.plan)
        result=w.run_check(root,ident,'target')
        w.assess(root,ident,'C1','supported','Synthetic actual assertion covers exact local criterion')
        w.close(root,ident,[])
        sizes.append(w.task_path(root,ident).stat().st_size)
        if i%50==49:print('Synthetic completed tasks:',i+1,flush=True)
    before={'task_records':len(list((root/'.featrace/tasks').glob('*.json'))),
            'task_bytes':sum(sizes),'max_task_bytes':max(sizes),
            'default_status_bytes':len(w.canonical(w.view(root,'SCALE-0199'))),
            'log_files':len(list((root/'.featrace/artifacts').rglob('*.log')))}
    create_seconds=time.perf_counter()-start
    class Future(datetime):
        @classmethod
        def now(cls,tz=None):return datetime.now(tz)+timedelta(days=8)
    start=time.perf_counter()
    with patch.object(w,'datetime',Future):
        for i in range(200):
            ident=fixture.ident if i==0 else f'SCALE-{i:04}'
            w.cleanup(root,ident,apply=True,forget=True)
    cleanup_seconds=time.perf_counter()-start
    after={'task_records':len(list((root/'.featrace/tasks').glob('*.json'))),
           'log_files':len(list((root/'.featrace/artifacts').rglob('*.log'))),
           'lock_slots':len(list((root/'.featrace/locks').iterdir())),
           'code_unchanged':sha(root/'app.py')==code_sha,
           'legacy_directory_created':(root/'.agent-workflow').exists()}
    assert before['task_records']==200 and after['task_records']==0 and after['log_files']==0 and after['code_unchanged']
    scale={'synthetic_tasks':200,'before':before,'after':after,'create_execute_close_seconds':create_seconds,
           'cleanup_seconds':cleanup_seconds,'actual_executions':int((root/'run-count').read_text()),
           'clock':'Cleanup uses simulated +8 days; execution timestamps not rewritten',
           'limits':'Single host sequential synthetic tasks, not team concurrency or real effort/time-saving comparison'}
    (OUT/'scale.json').write_text(json.dumps(scale,indent=2)+'\n')
finally:fixture.doCleanups()

fixture=TaskWorkflowTests();fixture.setUp()
try:
    with tempfile.TemporaryDirectory(prefix='featrace-task-install-') as home:
        p=subprocess.run([sys.executable,str(ROOT/'scripts/install.py'),'--agent','both','--home',home],capture_output=True,text=True)
        assert p.returncode==0,p.stderr
        probes=[]
        for label,directory in [('claude','.claude'),('codex','.agents')]:
            base=Path(home)/directory/'skills/dev';script=base/'core/scripts/task_workflow.py'
            ident='CLI-'+label
            installed_cli(script,fixture.root,'begin',ident,'--request','Synthetic installed CLI local label')
            plan=fixture.root/'.featrace/plan.json';plan.write_text(json.dumps(fixture.plan))
            installed_cli(script,fixture.root,'plan',ident,'--json',str(plan))
            first=installed_cli(script,fixture.root,'run',ident,'--check','target')
            second=installed_cli(script,fixture.root,'run',ident,'--check','target')
            installed_cli(script,fixture.root,'assess',ident,'--criterion','C1','--verdict','supported','--reason','Actual synthetic assertion checked')
            receipt=installed_cli(script,fixture.root,'close',ident)
            status=installed_cli(script,fixture.root,'status',ident)
            assert not first['reused'] and second['reused'] and status['state']=='complete'
            marker=json.loads((base/'.feature-delivery-install.json').read_text())
            probes.append({'host_directory':label,'base_version':marker['version'],'candidate_not_release':True,
                           'files':len(marker['files']),'script_sha256':sha(script),
                           'execution_reused':second['execution']==first['execution'],'completed':status['state']=='complete',
                           'legacy_directory_created':(fixture.root/'.agent-workflow').exists()})
        (OUT/'installed-cli.json').write_text(json.dumps({'probes':probes,'daily_install_changed':False,
                'boundary':'Actual CLI in isolated copies, not actual Claude/Codex Agent semantic execution'},indent=2)+'\n')
finally:fixture.doCleanups()
print('Synthetic scale and isolated CLI probes complete',flush=True)
