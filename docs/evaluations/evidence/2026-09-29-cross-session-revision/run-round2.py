from pathlib import Path
import subprocess,json,time,sys
c=Path(sys.argv[1]);p=c.parent/'project'
a=['claude','--print','--verbose','--output-format','stream-json','--no-session-persistence','--no-chrome','--setting-sources','user','--strict-mcp-config','--mcp-config','{"mcpServers":{}}','--permission-mode','dontAsk','--tools','Skill,Read,Glob,Grep,Bash,Write,Edit','--allowedTools','Skill,Read,Glob,Grep,Bash,Write,Edit','--add-dir',str(c.parent),'--max-budget-usd','5.5','--settings',str(c/'settings.json')]
t=time.time()
with (c/'stream.jsonl').open('w') as o,(c/'stderr.txt').open('w') as e:
 try:v=subprocess.run(a,input=(c/'prompt.txt').read_text(),cwd=p,text=True,stdout=o,stderr=e,timeout=700);code=v.returncode
 except subprocess.TimeoutExpired:code='timeout'
d={'exit_code':code,'elapsed_seconds':round(time.time()-t,3)};(c/'execution.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
