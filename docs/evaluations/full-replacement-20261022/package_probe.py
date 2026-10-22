from pathlib import Path
from datetime import datetime,timezone,timedelta
import hashlib,importlib.util,json,subprocess,sys,tempfile,time
r=Path('/Users/mac/Entrepôt/featrace-dev');work=Path(tempfile.mkdtemp(prefix='featrace-whole-probe-',dir='/private/tmp'))
report={'candidate_not_release':True,'work':str(work),'hosts':[]}
def execute(argv,root=None):
 result=subprocess.run(list(map(str,argv)),cwd=root,capture_output=True,text=True)
 if result.returncode:raise RuntimeError(json.dumps({'command_kind':Path(str(argv[0])).name,'exit':result.returncode,'output':result.stdout[:3000],'error':result.stderr[:1000]}))
 return result.stdout
execute([sys.executable,r/'scripts/install.py','--agent','both','--home',work/'home'])
for host in ('.claude','.agents'):
 install=work/'home'/host/'skills/dev';script=install/'core/scripts/task_workflow.py';root=work/host.strip('.');root.mkdir()
 def cli(action,*args):return json.loads(execute([sys.executable,script,action,root,*args]))
 def git(*args):execute(['git','-C',root,*args])
 git('init','-q');git('config','user.name','Synthetic');git('config','user.email','fixture@example.invalid')
 (root/'app').mkdir();(root/'app/ui.txt').write_text('before')
 (root/'check.py').write_text('from pathlib import Path\np=Path("run-count");p.write_text(str(int(p.read_text())+1) if p.exists() else "1")\nassert Path("app/ui.txt").read_text()=="after"\nprint("actual synthetic assertion passed")\n')
 (root/'.gitignore').write_text('run-count\n');(root/'issues.md').write_text('Synthetic probe only; no physical Android device verified.\n')
 policy={'policy_contract':1,'authority':'Synthetic isolated test permission','timezone':'Asia/Shanghai','retention_days':7,'cleanup':'forget','handoff':'issues.md','rules':[]}
 file=work/(host+'.policy.json');file.write_text(json.dumps(policy));cli('policy','--json',file)
 git('add','.');git('commit','-qm','synthetic baseline');cli('begin','PROBE','--request','Update isolated label only')
 (root/'app/ui.txt').write_text('after')
 plan={'reason':'Actual single label file and synthetic assertion; no business behavior claim','categories':['presentation'],'scope':['app/ui.txt','check.py'],'exclusions':{},'constraints':{},'unknowns':[],
       'criteria':[{'id':'LABEL','expected':'The label reads after','kind':'changed','inputs':['app/ui.txt']}],
       'checks':[{'id':'render','argv':[sys.executable,'check.py'],'inputs':[],'input_sets':[{'kind':'git_tree','path':'.'}],
                  'covers':['LABEL'],'reason':'Actual label assertion','timeout':10,'environment':{'kind':'local','target':'synthetic label fixture'}}],
       'review':{'independent':False,'reason':'Single local fixture; not a host Agent independence test'}}
 pf=work/(host+'.plan.json');pf.write_text(json.dumps(plan));cli('plan','PROBE','--json',pf)
 raw=root/'.featrace/scratch/PROBE/frame.txt';raw.parent.mkdir(parents=True);raw.write_text('synthetic snapshot, not a device image')
 copied=cli('attach','PROBE','--file',raw.relative_to(root).as_posix());raw.unlink()
 first=cli('run','PROBE','--check','render');second=cli('run','PROBE','--check','render')
 assert not first['reused'] and second['reused'] and (root/'run-count').read_text()=='1'
 facts=cli('review-input','PROBE','--criterion','LABEL');assert facts['facts']==[first['execution']]
 cli('assess','PROBE','--criterion','LABEL','--verdict','supported','--reason','Driver inspected actual assertion; no Agent semantic independence claim')
 cli('close','PROBE','--limitation','Synthetic probe only; no physical Android device verified.')
 status=cli('status','PROBE');assert status['state']=='complete'
 aged='''import sys,json\nfrom pathlib import Path\nfrom datetime import datetime,timedelta\nsys.path.insert(0,sys.argv[1]);import task_workflow as w\nclass Clock(datetime):\n @classmethod\n def now(cls,tz=None):return datetime.now(tz)+timedelta(days=8)\nw.datetime=Clock\nprint(json.dumps(w.maintain(Path(sys.argv[2]))))\n'''
 sweep=json.loads(execute([sys.executable,'-c',aged,script.parent,root]));assert sweep['cleaned']==1
 assert not (root/'.featrace/tasks/PROBE.json').exists() and (root/'issues.md').exists()
 assert not (root/copied['path']).exists()
 assert not (root/'.agent-workflow').exists()
 marker=json.loads((install/'.feature-delivery-install.json').read_text());actual={p.relative_to(install).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in install.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='.feature-delivery-install.json'}
 assert actual==marker['files'] and len(actual)==10
 report['hosts'].append({'layout':host,'runtime_files':len(actual),'marker_base_version':marker['version'],'first_run_physical':not first['reused'],'second_run_reused':second['reused'],'complete':True,'registered_evidence_copy_cleaned':not (root/copied['path']).exists(),'sweep_simulated_plus_days':8,'cleaned':sweep['cleaned'],'local_task_files_after_forget':len(list((root/'.featrace/tasks').glob('*.json'))),'installed_kernel_sha256':actual['core/scripts/task_workflow.py']})
# Lifecycle scale, actual 200 executions; deliberately synthetic local workload, NOT 50-person concurrency.
sys.path.insert(0,str(r/'skills/dev/core/scripts'));import task_workflow as w
root=work/'scale';root.mkdir();execute(['git','init','-q',root]);execute(['git','-C',root,'config','user.name','Synthetic']);execute(['git','-C',root,'config','user.email','fixture@example.invalid'])
(root/'.gitignore').write_text('run-count\n');(root/'label.txt').write_text('after')
(root/'check.py').write_text('from pathlib import Path\np=Path("run-count");p.write_text(str(int(p.read_text())+1) if p.exists() else "1")\nassert Path("label.txt").read_text()=="after"\n')
w.task_policy.prepare(root,{**policy,'handoff':None},w.git);execute(['git','-C',root,'add','.']);execute(['git','-C',root,'commit','-qm','baseline'])
plan['scope']=['label.txt','check.py'];plan['criteria'][0]['inputs']=['label.txt'];start=time.monotonic()
for i in range(200):
 ident=f'T-{i:04d}';w.begin(root,ident,'Synthetic label assertion');w.set_plan(root,ident,plan);w.run_check(root,ident,'render');w.assess(root,ident,'LABEL','supported','Actual isolated label assertion');w.close(root,ident,[])
paths=list((root/'.featrace/tasks').glob('*.json'));sizes=[p.stat().st_size for p in paths]
report['scale']={'tasks':len(paths),'total_task_bytes':sum(sizes),'max_task_bytes':max(sizes),'actual_executions':int((root/'run-count').read_text()),'create_execute_close_seconds':time.monotonic()-start,'concurrency':'single process sequential; not team stress'}
class Clock(datetime):
 @classmethod
 def now(cls,tz=None):return datetime.now(tz)+timedelta(days=8)
w.datetime=Clock;start=time.monotonic()
for _ in range(3):w.maintain(root,limit=100)
report['scale'].update({'simulated_clock_plus_days':8,'sweep_seconds':time.monotonic()-start,'remaining_task_files':len(list((root/'.featrace/tasks').glob('*.json'))),'remaining_log_files':len(list((root/'.featrace/artifacts').rglob('*.log'))),'lock_files':len(list((root/'.featrace/locks').iterdir()))})
out=Path('/private/tmp/featrace-whole-probe-result-final.json');out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert report['scale']['remaining_task_files']==0 and report['scale']['remaining_log_files']==0
print(json.dumps(report,ensure_ascii=False))
