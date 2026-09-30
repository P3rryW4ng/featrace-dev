from pathlib import Path
import json,hashlib,subprocess,sys,re
r=Path('/private/tmp/featrace-resume-0533-e0zic_sg');p=r/'project';name=sys.argv[1];c=r/name
b=json.loads((r/'before.json').read_text())
def hashes(d):return {str(x.relative_to(d)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(d.rglob('*')) if x.is_file() and '.git' not in x.parts and '__pycache__' not in x.parts}
calls=[];events=[];returns={};texts=[];res={}
for line in (c/'stream.jsonl').read_text().splitlines():
 j=json.loads(line)
 if j.get('type')=='result':res={k:j.get(k) for k in ['subtype','is_error','total_cost_usd','duration_ms','num_turns','usage']}
 for x in j.get('message',{}).get('content',[]):
  if x.get('type')=='tool_use':
   z={'order':len(calls)+1,'event':len(events)+1,'id':x['id'],'name':x['name'],'input':x['input']};calls.append(z);events.append(z)
  if x.get('type')=='tool_result':
   z={'event':len(events)+1,'id':x.get('tool_use_id'),'is_error':x.get('is_error',False),'content':x.get('content')};returns[z['id']]=z;events.append(z)
  if x.get('type')=='text':texts.append(x['text'])
summary=[{'order':x['order'],'event':x['event'],'name':x['name'],'path':x['input'].get('file_path'),'description':x['input'].get('description'),'command_prefix':x['input'].get('command','')[:400]} for x in calls]
(c/'call-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');(c/'stage-statements.json').write_text(json.dumps(texts,ensure_ascii=False,indent=2)+'\n')
# Actual commands/errors with old evidence rejection, revision, tests and closure; preserve exact tool boundaries.
critical=[]
for x in calls:
 i=x['input'];v=i.get('command','')+i.get('file_path','');rr=returns.get(x['id'],{})
 if any(t in v for t in ['revise.py','review-prd.py','task_review.py','task-review','verification.py','quality-report','delivery-report.md','register-source.py','unittest','validate-feature.py','audit-delivery.py','requirements.json','prd-original']):critical.append({'call':x,'return':rr})
(c/'critical-calls.json').write_text(json.dumps(critical,ensure_ascii=False,indent=2)+'\n')
state=hashes(p);f=p/'.agent-workflow/features/RESUME-001';req=json.loads((f/'spec/requirements.json').read_text()) if (f/'spec/requirements.json').exists() else {};tasks=json.loads((f/'tasks.json').read_text()) if (f/'tasks.json').exists() else {}
quality=p/'.agent-workflow/project-baseline/quality-report.json';q=json.loads(quality.read_text()) if quality.exists() else {}
a={'execution':json.loads((c/'execution.json').read_text()),'cli_result':res,'skill_calls':[x['input'] for x in calls if x['name']=='Skill'],'agent_calls':[x['name'] for x in calls if x['name']=='Agent'],'feature':req.get('feature'),'requirements':req.get('requirements'),'tasks':tasks,'quality_report':q,'legacy_test_unchanged':state.get('tests/test_legacy.py')==b['project'].get('tests/test_legacy.py'),'installed_unchanged':hashes(Path('/Users/mac/.claude/skills/dev'))==b['installed'],'source_hashes':{k:v for k,v in state.items() if '/sources/' in k},'current_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=p,text=True).strip(),'project_files':state}
(c/'audit.json').write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n')
print(name,'status',req.get('feature',{}).get('status'),'cost',res.get('total_cost_usd'),'calls',len(calls),'legacy',a['legacy_test_unchanged'],'install',a['installed_unchanged'])
