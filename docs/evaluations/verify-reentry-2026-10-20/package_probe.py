from pathlib import Path
import hashlib,json,subprocess,tarfile,io,os,tempfile,sys
r=Path('/Users/mac/Entrepôt/featrace-dev');out=Path('/private/tmp/ft-verify-loop-0184');base='cd050faacc0432d83928b7d5b9b4de533cc77c96';work=Path(tempfile.mkdtemp(prefix='ft-0184-scoped-'));old=work/'old';package=work/'candidate';home=work/'home'
archive=subprocess.check_output(['git','-C',str(r),'archive',base,'VERSION','scripts/install.py','skills/dev']);old.mkdir()
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
 for member in tar.getmembers():
  assert not Path(member.name).is_absolute() and '..' not in Path(member.name).parts and not member.issym() and not member.islnk()
 tar.extractall(old)
import shutil
shutil.copytree(old,package)
for root in (old,package):
 for line in subprocess.check_output(['git','-C',str(r),'ls-tree','-r',base,'--','scripts/install.py','skills/dev'],text=True).splitlines():
  meta,name=line.split('\t');(root/name).chmod(int(meta.split()[0][-3:],8))
changed=['core/scripts/verification.py','core/scripts/verify-inputs.py','core/references/technical-test.md','core/references/verification-workflow.md','core/references/orchestration.md']
for name in changed[:-1]:shutil.copyfile(r/'skills/dev'/name,package/'skills/dev'/name)
name=changed[-1];formal=(old/'skills/dev'/name).read_text();before=(subprocess.check_output(['git','-C',str(r),'show','056eee0:skills/dev/'+name]).decode());current=(r/'skills/dev'/name).read_text()
needle='At ordinary Verify entry, read the continuation guidance in verify-inputs.py';replacement='At ordinary Verify entry, read the compact next_step and continuation guidance in verify-inputs.py';assert formal.count(needle)==before.count(needle)==1
before=before.replace(needle,replacement);formal=formal.replace(needle,replacement);assert current.startswith(before);tail=current[len(before):];assert tail.startswith('\nOrdinary Verify reentry:');(package/'skills/dev'/name).write_text(formal+tail);(package/'VERSION').write_text('0.18.4\n')
def inventory(root):return {p.relative_to(root).as_posix():{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mode':oct(p.stat().st_mode&0o777)} for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
previous=inventory(old/'skills/dev');manifest=inventory(package/'skills/dev');assert len(previous)==len(manifest)==113 and set(previous)==set(manifest);assert {n for n in manifest if manifest[n]!=previous[n]}==set(changed);assert manifest['SKILL.md']==previous['SKILL.md']
commands=[]
def run(args,expected=0):
 p=subprocess.run([sys.executable,'-B',*map(str,args)],capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'});commands.append({'entry':Path(args[0]).name,'action':str(args[1]) if len(args)>1 else '', 'returncode':p.returncode});assert p.returncode==expected,p.stdout+p.stderr;return p
run([old/'scripts/install.py','--agent','claude','--home',home]);installed=home/'.claude/skills/dev';original=inventory(installed)
run([package/'scripts/install.py','--agent','claude','--home',home,'--update']);backups=list((home/'.feature-delivery/backups').iterdir());assert len(backups)==1 and inventory(backups[0])==original
marker=json.loads((installed/'.feature-delivery-install.json').read_text());assert marker['version']=='0.18.4' and len(marker['files'])==113
for n,value in manifest.items():assert inventory(installed)[n]==value and marker['files'][n]==value['sha256']
for script in ('project.py','verification.py','evidence_carry.py','regression_continuity.py'):run([installed/'core/scripts'/script,'--help'])
sys.path.insert(0,str(r/'tests'));import test_verification as fixtures;import verification as v
from intake_helpers import attach_intake
x=fixtures.VerificationTests();x.setUp()
try:
 scripts=installed/'core/scripts';root=x.root.resolve();folder=x.folder.resolve()
 run([scripts/'verification.py','run',root,'FEAT-001'],2)
 before=(x.base/'quality-report.json').read_bytes();g=json.loads(run([scripts/'verify-inputs.py',root,'FEAT-001']).stdout);assert g['next_step']['action']=='review_delivery'
 req=v.read(folder/'spec/requirements.json');req['requirements'][0]['acceptance_criteria'].append('Synthetic icon matches approved reference');attach_intake(folder,req)
 g=json.loads(run([scripts/'verify-inputs.py',root,'FEAT-001']).stdout);assert g['next_step']['action']=='sync_then_reinspect'
 run([scripts/'verification.py','sync',root,'FEAT-001']);g=json.loads(run([scripts/'verify-inputs.py',root,'FEAT-001']).stdout);assert g['next_step']['action']=='review_legacy_binding';assert before==(x.base/'quality-report.json').read_bytes();assert not (folder/'check-runs').exists() and 'manual_scope_contract' not in v.load_plan(folder)
 x.gates([sys.executable,'-c','raise SystemExit(8)']);run([scripts/'verification.py','sync',root,'FEAT-001']);run([scripts/'verification.py','run',root,'FEAT-001'],2);g=json.loads(run([scripts/'verify-inputs.py',root,'FEAT-001']).stdout);assert g['next_step']['action']=='investigate_execution' and 'failed' in g['continuation']['reason']
finally:x.doCleanups()
run([package/'scripts/install.py','--agent','claude','--home',home,'--uninstall']);assert not installed.exists();run([old/'scripts/install.py','--agent','claude','--home',home]);assert inventory(installed)==original
record={'version':'0.18.4','baseline':base,'synthetic_only':True,'runtime_files':113,'runtime_changes':changed,'file_manifest':manifest,'package_path':str(package),'isolated_upgrade_backup_restore':True,'preserved_SKILL':True,'unpublished_main_progress_excluded':True,'commands':commands,'daily_install_changed':False}
(out/'scoped-package.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:v for k,v in record.items() if k!='file_manifest'},indent=2))
