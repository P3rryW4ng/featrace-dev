"""Synthetic bounded-record, fresh-process, old-reader and package probes. No business inputs."""
import hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path

r=Path.cwd();out=Path(__file__).resolve().parent
sys.path.insert(0,str(r/'tests'));from test_task_workflow import TaskWorkflowTests,w
fixture=TaskWorkflowTests();fixture.setUp()
try:
    plan=fixture.plan;plan['checks']=[]
    plan['criteria']=[{'id':'C'+str(n),'expected':'Synthetic local rendering state '+str(n),
        'kind':'changed','inputs':['app.py'],'proof':{'any_of':[['runtime_observation']],
        'reason':'Two synthetic state observations, not a real device trial'}} for n in range(64)]
    w.set_plan(fixture.root,fixture.ident,plan)
    for c in plan['criteria']:
        ids=[]
        for mode in ('success','error-handled'):
            ids.append(w.observe(fixture.root,fixture.ident,c['id'],'runtime_observation',w.now(),
                'Synthetic '+mode+' state; not real runtime',['app.py'],target='synthetic-size-fixture')['fact'])
        w.assess(fixture.root,fixture.ident,c['id'],'supported','Both explicitly selected synthetic states',fact_ids=ids)
    path=w.task_path(fixture.root,fixture.ident);before=hashlib.sha256(path.read_bytes()).hexdigest()
    fresh=subprocess.run([sys.executable,'-B',str(r/'skills/dev/core/scripts/task_workflow.py'),'status',str(fixture.root),fixture.ident],capture_output=True,text=True)
    assert fresh.returncode==0,fresh.stdout+fresh.stderr
    status=json.loads(fresh.stdout);assert status['eligible'] and status['total']==64 and status['next_offset']==20
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before
    old=Path(tempfile.mkdtemp(prefix='featrace-fixed025-probe-'));manifest=json.loads(subprocess.check_output(['git','show','v0.25.0:release.json'],cwd=r))
    for name in ('task_workflow.py','task_inputs.py','task_policy.py'):
        data=subprocess.check_output(['git','show','v0.25.0:skills/dev/core/scripts/'+name],cwd=r)
        assert hashlib.sha256(data).hexdigest()==manifest['files']['core/scripts/'+name]
        (old/name).write_bytes(data)
    legacy=subprocess.run([sys.executable,'-B',str(old/'task_workflow.py'),'status',str(fixture.root),fixture.ident],capture_output=True,text=True)
    assert legacy.returncode==2 and json.loads(legacy.stdout)['reason']=='TASK_CONTRACT_UNSUPPORTED'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before
    result={'criteria':64,'facts':128,'record_bytes':path.stat().st_size,'record_limit':w.MAX_RECORD,
            'new_process_read_only_ready':True,'query_paginated':True,'fixed025_reader_refuses_without_write':True,
            'old_reader_bytes_match_tag':True,'business_operations':False,'natural_agent_trial':False}
    home=Path(tempfile.mkdtemp(prefix='featrace-newcore-package-'))
    installed=subprocess.run([sys.executable,'-B',str(r/'scripts/install.py'),'--development','--agent','both','--home',str(home)],capture_output=True,text=True)
    assert installed.returncode==0,installed.stdout+installed.stderr
    source={p.relative_to(r/'skills/dev').as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (r/'skills/dev').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    for folder in ('.claude','.agents'):
        target=home/folder/'skills/dev';mark=json.loads((target/'.feature-delivery-install.json').read_text())
        actual={p.relative_to(target).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in target.rglob('*') if p.is_file() and p.name!='.feature-delivery-install.json' and '__pycache__' not in p.parts and p.suffix!='.pyc'}
        assert source==mark['files']==actual and mark['source']['channel']=='development'
    result['isolated_package']={'files':len(source),'both_hosts_match':True,'channel':'development','daily_install_changed':False}
    (out/'probe-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
finally:
    fixture.doCleanups()
