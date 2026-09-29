from pathlib import Path
import json,hashlib,subprocess,re,sys
root=Path(__file__).resolve().parent;s=Path('/Users/mac/.claude/skills/dev/core/scripts')
def hashes(d):return {str(x.relative_to(d)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(d.rglob('*')) if x.is_file() and '.git' not in x.parts and '__pycache__' not in x.parts}
for name in sys.argv[1:]:
 r=root/name;p=r/'project';b=json.loads((r/'before.json').read_text());cfg=json.loads((r/'case.json').read_text());report=Path(cfg['report']);calls=[];events=[];ret={};texts=[];result={}
 for l in (r/'stream.jsonl').read_text().splitlines():
  j=json.loads(l)
  if j.get('type')=='result':result={k:j.get(k) for k in ['subtype','is_error','total_cost_usd','duration_ms','num_turns','usage']}
  for c in j.get('message',{}).get('content',[]):
   if c.get('type')=='tool_use':
    z={'order':len(calls)+1,'event':len(events)+1,'id':c['id'],'name':c['name'],'input':c['input']};calls.append(z);events.append(z)
   if c.get('type')=='tool_result':
    z={'event':len(events)+1,'id':c.get('tool_use_id'),'is_error':c.get('is_error',False),'content':c.get('content')};ret[z['id']]=z;events.append(z)
   if c.get('type')=='text':texts.append(c['text'])
 critical=[];reads=[];mutations=[]
 for c in calls:
  i=c['input'];path=i.get('file_path','');cmd=i.get('command','');rr=ret.get(c['id'])
  is_mut=(c['name'] in ['Write','Edit'] and path.endswith('/spec/requirements.json') and 'complete' in (i.get('new_string','')+i.get('content',''))) or (c['name']=='Bash' and re.search(r"\[['\"]status['\"]\]\s*=\s*['\"]complete['\"]",cmd))
  if is_mut:mutations.append(c['order'])
  if path==str(report) or is_mut:critical.append({'call':c,'return':rr})
  if c['name']=='Read' and path==str(report):
   content=rr.get('content','') if rr else '';ls={int(n):t for n,t in re.findall(r'(?m)^\s*(\d+)\t(.*)$',content)} if isinstance(content,str) else {};reads.append({'call_order':c['order'],'call_event':c['event'],'return_event':rr['event'] if rr else None,'is_error':rr.get('is_error',False) if rr else True,'offset':i.get('offset',1),'line_numbers':sorted(ls),'lines':ls})
 hook=[json.loads(l) for l in (r/'hook-events.jsonl').read_text().splitlines()];injections=[x for x in hook if x['kind']!='tool_boundary'];after=hashes(p);changed=[k for k in sorted(set(after)|set(b['project'])) if after.get(k)!=b['project'].get(k)];feature=p/'.agent-workflow/features/E2E-0531';req=json.loads((feature/'spec/requirements.json').read_text());st=req['feature']['status']
 def git(*a):return subprocess.check_output(['git',*a],cwd=p,text=True)
 qa='.agent-workflow/project-baseline/quality-report.json';vf='.agent-workflow/features/E2E-0531/verification.json';src='.agent-workflow/features/E2E-0531/sources/prd-original.md';reporttext=report.read_text()
 checks=[]
 for script,args in [('validate-feature.py',['--stage','check']),('audit-delivery.py',[])]:
  v=subprocess.run(['python3',str(s/script),str(p),'E2E-0531',*args],capture_output=True,text=True);checks.append({'script':script,'exit':v.returncode,'stdout':v.stdout,'stderr':v.stderr})
 combined={}
 for read in reads:
  if not read['is_error']:combined.update(read['lines'])
 received='\n'.join(combined[i] for i in sorted(combined)).rstrip('\n');saved_at_read=json.loads((r/'report-at-save.json').read_text())['text'];full_received=received==saved_at_read.rstrip('\n')
 out={'case':cfg['case'],'execution':json.loads((r/'execution.json').read_text()),'cli_result':result,'actual_skill_calls':[c['input'] for c in calls if c['name']=='Skill'],'feature_status':st,'status_mutation_calls':mutations,'changed_project_files':changed,'business_diff_unchanged':git('diff','--binary')==b['diff'],'head_unchanged':git('rev-parse','HEAD').strip()==b['head'],'staged_unchanged':git('diff','--cached')==b['staged'],'quality_report_unchanged':after.get(qa)==b['project'].get(qa),'verification_history_unchanged':after.get(vf)==b['project'].get(vf),'installed_unchanged':hashes(Path('/Users/mac/.claude/skills/dev'))==b['installed'],'source_unchanged':after.get(src)==b['project'].get(src),'source_sha256_before':b['project'].get(src),'source_sha256_after':after.get(src),'read_calls':[{k:v for k,v in x.items() if k!='lines'} for x in reads],'received_complete_saved_report':full_received,'report_unchanged_since_save':hashlib.sha256(report.read_bytes()).hexdigest()==json.loads((r/'report-at-save.json').read_text())['sha256'],'report_explicit_blocker':('BLOCKED' in reporttext or 'read-back' in reporttext.lower() or 'read unavailable' in reporttext.lower()),'read_only_check_exit_codes':[x['exit'] for x in checks]}
 (r/'audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');(r/'critical-calls.json').write_text(json.dumps(critical,ensure_ascii=False,indent=2)+'\n');(r/'call-summary.json').write_text(json.dumps([{'order':c['order'],'event':c['event'],'name':c['name'],'file_path':c['input'].get('file_path'),'description':c['input'].get('description'),'command_prefix':c['input'].get('command','')[:240]} for c in calls],ensure_ascii=False,indent=2)+'\n');(r/'stage-statements.json').write_text(json.dumps(texts,ensure_ascii=False,indent=2)+'\n');(r/'injections.json').write_text(json.dumps(injections,ensure_ascii=False,indent=2)+'\n');(r/'read-only-checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
 print(name,json.dumps({k:v for k,v in out.items() if k not in ['changed_project_files','cli_result','read_calls']},ensure_ascii=False));print('reads',[(x['call_order'],x['is_error'],x['line_numbers'][:1],x['line_numbers'][-1:]) for x in reads])
