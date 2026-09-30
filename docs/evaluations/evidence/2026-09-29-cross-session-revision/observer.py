from pathlib import Path
import sys,json,hashlib,subprocess,time
r=Path(sys.argv[1]);p=r/'project';c=r/'round2';d=json.load(sys.stdin);f=p/'.agent-workflow/features/RESUME-001';req=f/'spec/requirements.json'
if not req.exists():sys.exit(0)
v=json.loads(req.read_text());b=v.get('feature',{}).get('baseline',{});version=b.get('version');event={'time_ns':time.time_ns(),'tool':d.get('tool_name'),'tool_use_id':d.get('tool_use_id'),'baseline_version':version,'baseline_digest':b.get('digest'),'status':v.get('feature',{}).get('status')}
with (c/'observation-events.jsonl').open('a') as out:out.write(json.dumps(event)+'\n')
if isinstance(version,int) and version>=2 and not (c/'after-revision-before-new-checks.json').exists():
 checks=[];s=Path('/Users/mac/.claude/skills/dev/core/scripts')
 for script,args in [('validate-feature.py',['--stage','check']),('audit-delivery.py',[]),('verification.py',['status'])]:
  command=['python3',str(s/script),str(p),'RESUME-001',*args] if script!='verification.py' else ['python3',str(s/script),'status',str(p),'RESUME-001']
  x=subprocess.run(command,capture_output=True,text=True);checks.append({'script':script,'exit_code':x.returncode,'stdout':x.stdout,'stderr':x.stderr})
 q=p/'.agent-workflow/project-baseline/quality-report.json'
 record={'observation':event,'requirements':v,'quality_report':json.loads(q.read_text()) if q.exists() else None,'read_only_checks':checks,'code_hashes':{str(x.relative_to(p)):hashlib.sha256(x.read_bytes()).hexdigest() for x in (p/'src').rglob('*.py')}}
 (c/'after-revision-before-new-checks.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
