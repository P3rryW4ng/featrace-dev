from pathlib import Path
import hashlib,json,subprocess,tarfile,io,os,tempfile,sys
r=Path('/Users/mac/Entrepôt/featrace-dev');out=Path('/private/tmp/ft-local-acceptance');base='4c61d353f12df904d8a7e826bc486c851dd29811'
work=Path(tempfile.mkdtemp(prefix='ft-0183-scoped-'));old=work/'old';package=work/'candidate';home=work/'home'
raw=subprocess.check_output(['git','archive',base,'skills/dev','scripts/install.py','VERSION'],cwd=r)
for target in (old,package):
 target.mkdir()
 with tarfile.open(fileobj=io.BytesIO(raw)) as a:
  assert all(m.isfile() or m.isdir() for m in a.getmembers());a.extractall(target)
 for line in subprocess.check_output(['git','ls-tree','-r',base,'--','skills/dev','scripts/install.py','VERSION'],cwd=r,text=True).splitlines():
  meta,name=line.split('\t',1);(target/name).chmod(int(meta.split()[0][-3:],8))
changed=['core/scripts/verification.py','core/scripts/verify-inputs.py','core/references/technical-test.md','core/references/verification-workflow.md','core/references/claim-evidence-review.md']
for name in changed:
 src=r/'skills/dev'/name;dst=package/'skills/dev'/name;dst.write_bytes(src.read_bytes());dst.chmod(src.stat().st_mode&0o777)
name='core/references/orchestration.md';original=subprocess.check_output(['git','show','HEAD:skills/dev/'+name],cwd=r,text=True);current=(r/'skills/dev'/name).read_text();formal=(old/'skills/dev'/name).read_text()
edits=[('Technical Test hands Verify the current `quality-report.json` plus per-row coverage/results in `verification.json`','Technical Test hands Verify the current legacy `quality-report.json` or contract-2 feature attempt/result reference, plus per-row coverage/results in `verification.json`'),('Before repeating checks solely because acceptance is stale, read the existing verification status continuation guidance.','At ordinary Verify entry, read the continuation guidance in verify-inputs.py before scheduling checks or promising old evidence can be reused; the same guidance remains available in status.')]
for before,after in edits:
 assert original.count(before)==formal.count(before)==1;original=original.replace(before,after);formal=formal.replace(before,after)
tail=current[len(original):];assert current.startswith(original) and tail.startswith('\n\nWhen manual rows are stale,');(package/'skills/dev'/name).write_text(formal+tail);changed.append(name)
(package/'VERSION').write_text('0.18.3\n')
def inventory(root):
 return {p.relative_to(root).as_posix():{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mode':oct(p.stat().st_mode&0o777)} for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
before=inventory(old/'skills/dev');after=inventory(package/'skills/dev');assert len(before)==len(after)==113 and set(before)==set(after);assert {p for p in before if before[p]!=after[p]}==set(changed);assert before['SKILL.md']==after['SKILL.md']
for n in changed[:2]:assert after[n]==inventory(r/'skills/dev')[n]
commands=[]
def run(args,expected=0):
 p=subprocess.run([sys.executable,'-B',*map(str,args)],capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'});commands.append({'entry':Path(args[0]).name,'action':str(args[1]) if len(args)>1 else '', 'returncode':p.returncode});assert p.returncode==expected,p.stdout+p.stderr;return p
run([old/'scripts/install.py','--agent','claude','--home',home]);installed=home/'.claude/skills/dev';original_install=inventory(installed)
run([package/'scripts/install.py','--agent','claude','--home',home,'--update']);backups=list((home/'.feature-delivery/backups').iterdir());assert len(backups)==1 and inventory(backups[0])==original_install
marker=json.loads((installed/'.feature-delivery-install.json').read_text());assert marker['version']=='0.18.3' and len(marker['files'])==113
for n,value in after.items():assert inventory(installed)[n]==value and marker['files'][n]==value['sha256']
for script in ('project.py','verification.py','evidence_carry.py','regression_continuity.py'):run([installed/'core/scripts'/script,'--help'])
sys.path.insert(0,str(r/'tests'));import test_manual_scope as fixture;import verification as v
x=fixture.ManualScopeTests();x.setUp()
try:
 doc=v.load_plan(x.folder);doc.pop('manual_scope_contract');doc.pop('manual_scope_reviews');doc['schema_version']=1;v.save(x.folder/'verification.json',doc)
 guide=json.loads(run([installed/'core/scripts/verify-inputs.py',x.root,'FEAT-001']).stdout)['continuation'];assert guide['manual_applicability']['contract']=='legacy' and set(guide['manual_applicability']['review_candidates'])==set(x.ids)
 run([installed/'core/scripts/evidence_carry.py','prepare-batch',x.root,'FEAT-001'])
 request=work/'requests.json';request.write_text(json.dumps([{'item_id':i,'contract_revision':x.records_at} for i in x.ids]))
 snap=json.loads(run([installed/'core/scripts/evidence_carry.py','capture-batch',x.root,'FEAT-001','--requests',request]).stdout)
 a,b=work/'snapshot.json',work/'review.json';a.write_text(json.dumps(snap));b.write_text(json.dumps(x.negative_review(snap)))
 run([installed/'core/scripts/evidence_carry.py','apply-batch',x.root,'FEAT-001','--snapshot',a,'--review',b])
 guide=json.loads(run([installed/'core/scripts/verify-inputs.py',x.root,'FEAT-001']).stdout)['continuation']['manual_applicability'];assert not guide['review_candidates'] and set(guide['prior_negative_assessments'])==set(x.ids)
 assert not (x.folder/'check-runs').exists() and not (x.h.base/'quality-report.json').exists()
finally:x.doCleanups()
import test_check_runs as checks
x=checks.CheckRunTests();x.setUp()
try:
 ident=x.map_claim();fact=x.execute();x.adopt(ident);doc=v.read(x.folder/'decisions.json');doc['decisions'].append({'id':'D-INSTALL','status':'approved','evidence':'Synthetic authority interpretation change'});(x.folder/'decisions.json').write_text(json.dumps(doc))
 guide=json.loads(run([installed/'core/scripts/verify-inputs.py',x.root,'FEAT-001']).stdout)['continuation'];assert guide['attempt_id']==fact['attempt_id'] and ident in guide['claim_review_targets'];assert x.counter.read_text()=='1'
finally:x.doCleanups()
run([package/'scripts/install.py','--agent','claude','--home',home,'--uninstall']);assert not installed.exists();run([old/'scripts/install.py','--agent','claude','--home',home]);assert inventory(installed)==original_install
record={'synthetic_only':True,'version':'0.18.3','runtime_files':113,'baseline':base,'runtime_changes':changed,'file_manifest':after,'preserved_SKILL':True,'only_three_orchestration_edits_on_formal_body':True,'python_matches_tested_source':True,'isolated_upgrade_backup_restore':True,'installed_ordinary_legacy_batch_negative_and_mode2_guidance':True,'commands':commands,'package_path':str(package),'daily_install_changed':False}
(out/'scoped-package.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:v for k,v in record.items() if k!='file_manifest'},indent=2))
