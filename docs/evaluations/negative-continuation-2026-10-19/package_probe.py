from pathlib import Path
import hashlib,json,subprocess,tarfile,io,os,tempfile,sys
r=Path('/Users/mac/Entrepôt/featrace-dev');out=Path('/private/tmp/ft-8024-review');base='196039f9c2bbf9d357e8a3964d7304923d3adf27'
work=Path(tempfile.mkdtemp(prefix='ft-0182-scoped-'));old=work/'old';package=work/'candidate';home=work/'home'
raw=subprocess.check_output(['git','archive',base,'skills/dev','scripts/install.py','VERSION'],cwd=r)
for target in (old,package):
 target.mkdir()
 with tarfile.open(fileobj=io.BytesIO(raw)) as a:
  assert all(m.isfile() or m.isdir() for m in a.getmembers());a.extractall(target)
changed=['core/scripts/manual_scope.py','core/scripts/verification.py','core/scripts/feature-status.py','core/references/manual-scope.md','core/references/check-execution.md']
for name in changed:
 src=r/'skills/dev'/name;dst=package/'skills/dev'/name;dst.write_bytes(src.read_bytes());dst.chmod(src.stat().st_mode&0o777)
name='core/references/orchestration.md';heading='### Acceptance continuation (source candidate)';section=heading+(r/'skills/dev'/name).read_text().split(heading,1)[1];p=package/'skills/dev'/name;p.write_text(p.read_text()+'\n\n'+section);changed.append(name)
(package/'VERSION').write_text('0.18.2\n')
def inventory(root):
 return {p.relative_to(root).as_posix():{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mode':oct(p.stat().st_mode&0o777)} for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
before=inventory(old/'skills/dev');after=inventory(package/'skills/dev');assert len(before)==len(after)==113 and set(before)==set(after)
assert {p for p in before if before[p]!=after[p]}==set(changed)
assert after['SKILL.md']==before['SKILL.md']
for n in changed[:3]:assert after[n]==inventory(r/'skills/dev')[n]
commands=[]
def run(args,expected=0):
 p=subprocess.run([sys.executable,'-B',*map(str,args)],capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
 commands.append({'entry':Path(args[0]).name,'action':str(args[1]) if len(args)>1 else '', 'returncode':p.returncode})
 assert p.returncode==expected,p.stdout+p.stderr;return p
run([old/'scripts/install.py','--agent','claude','--home',home]);installed=home/'.claude/skills/dev';original=inventory(installed)
run([package/'scripts/install.py','--agent','claude','--home',home,'--update'])
backups=list((home/'.feature-delivery/backups').iterdir());assert len(backups)==1 and inventory(backups[0])==original
marker=json.loads((installed/'.feature-delivery-install.json').read_text());assert marker['version']=='0.18.2' and len(marker['files'])==113
for n,v in after.items():assert inventory(installed)[n]==v and marker['files'][n]==v['sha256']
for script in ('project.py','verification.py','evidence_carry.py','regression_continuity.py'):run([installed/'core/scripts'/script,'--help'])
sys.path.insert(0,str(r/'tests'))
import test_manual_scope as t
x=t.ManualScopeTests();x.setUp()
try:
 req=work/'requests.json';req.write_text(json.dumps([{'item_id':i,'contract_revision':x.records_at} for i in x.ids]))
 frozen=json.loads(run([installed/'core/scripts/evidence_carry.py','capture-batch',x.root,'FEAT-001','--requests',req]).stdout)
 snap=work/'snapshot.json';snap.write_text(json.dumps(frozen));review=work/'review.json';review.write_text(json.dumps(x.negative_review(frozen)))
 run([installed/'core/scripts/evidence_carry.py','apply-batch',x.root,'FEAT-001','--snapshot',snap,'--review',review])
 status=json.loads(run([installed/'core/scripts/verification.py','status',x.root,'FEAT-001'],2).stdout)
 assert status['continuation']['contract']=='legacy' and all(i['status']=='stale' for i in status['items'] if i['mode']=='manual')
 assert not (x.folder/'check-runs').exists() and not (x.h.base/'quality-report.json').exists()
finally:x.doCleanups()
run([package/'scripts/install.py','--agent','claude','--home',home,'--uninstall']);assert not installed.exists()
run([old/'scripts/install.py','--agent','claude','--home',home]);assert inventory(installed)==original
result={'synthetic_only':True,'version':'0.18.2','runtime_files':113,'baseline':base,'runtime_changes':changed,'preserved_entrypoint':'SKILL.md','preserved_orchestration_body':True,'file_manifest':after,'python_matches_tested_source':True,'isolated_upgrade_backup_restore':True,'installed_zero_adoption_and_status_gap':True,'commands':commands,'package_path':str(package),'daily_install_changed':False}
(out/'scoped-package.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='file_manifest'},indent=2))
