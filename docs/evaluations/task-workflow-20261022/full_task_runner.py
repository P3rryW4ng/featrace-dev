from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import time

repo=Path('/Users/mac/Entrepôt/featrace-dev');out=Path('/tmp/featrace-task-full');out.mkdir(exist_ok=True)
def inputs():
    paths=list((repo/'skills/dev').rglob('*'))+list((repo/'tests').glob('*.py'))+[repo/'scripts/install.py']
    return {p.relative_to(repo).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
before=inputs();(out/'inputs-before.json').write_text(json.dumps(before,indent=2))
start=datetime.now(timezone.utc).isoformat();tick=time.perf_counter()
with (out/'full.log').open('wb') as stream:
    run=subprocess.run(['python3','-m','unittest','discover','-s','tests','-v'],cwd=repo,stdout=stream,stderr=subprocess.STDOUT)
after=inputs();(out/'inputs-after.json').write_text(json.dumps(after,indent=2))
result={'started_at':start,'ended_at':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.perf_counter()-tick,
        'exit_code':run.returncode,'input_count':len(before),'inputs_unchanged':before==after,
        'source_base':'54c5260fd6688a0bca9c83f29bad240321a67b52','candidate':True}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
raise SystemExit(run.returncode or (0 if before==after else 3))
