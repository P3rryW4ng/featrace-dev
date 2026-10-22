from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,time
r=Path('/Users/mac/Entrepôt/featrace-dev');out=Path('/private/tmp/featrace-whole-full-final-20261022');out.mkdir(exist_ok=False)
def snap():
 paths=list((r/'skills/dev').rglob('*'))+list((r/'tests').rglob('*'))+[r/'scripts/install.py',r/'VERSION']
 return {p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths)) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
before=snap();(out/'inputs-before.json').write_text(json.dumps(before,indent=2)+'\n');start=datetime.now(timezone.utc).isoformat();t=time.monotonic()
with (out/'full.log').open('wb') as log:
 result=subprocess.run(['python3','-m','unittest','discover','-s','tests','-v'],cwd=r,stdout=log,stderr=subprocess.STDOUT)
after=snap();report={'started_at':start,'finished_at':datetime.now(timezone.utc).isoformat(),'duration_seconds':time.monotonic()-t,'exit_code':result.returncode,'inputs_equal':before==after,'input_files':len(before)}
(out/'inputs-after.json').write_text(json.dumps(after,indent=2)+'\n');(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
