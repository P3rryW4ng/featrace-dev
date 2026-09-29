from pathlib import Path
import subprocess,json,time,sys
r=Path(sys.argv[1]);args=['claude','--print','--verbose','--output-format','stream-json','--no-session-persistence','--no-chrome','--setting-sources','user','--strict-mcp-config','--mcp-config','{"mcpServers":{}}','--permission-mode','dontAsk','--tools','Skill,Read,Glob,Grep,Bash,Write,Edit','--allowedTools','Skill,Read,Glob,Grep,Bash,Write,Edit','--add-dir',str(r),'--plugin-dir',str(r.parent/'plugin'),'--max-budget-usd','2.8','--settings',str(r/'settings.json')]
start=time.time()
with (r/'stream.jsonl').open('w') as o,(r/'stderr.txt').open('w') as e:
 try:v=subprocess.run(args,input=(r/'prompt.txt').read_text(),cwd=r/'project',text=True,stdout=o,stderr=e,timeout=500);code=v.returncode
 except subprocess.TimeoutExpired:code='timeout'
d={'exit_code':code,'elapsed_seconds':round(time.time()-start,3)};(r/'execution.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
