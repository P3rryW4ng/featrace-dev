"""Explicit bounded applicability proofs. Original observations are never rewritten."""
import hashlib
import re
import uuid

def basis(w,root,doc,c):
    return w.digest({'criterion':c,'authority':w.files(root,c.get('sources',[]),True),
                     'constraints':w.files(root,w.selected_constraints(doc['plan'],criterion=c),True),
                     'review':w.review_required(doc['plan'],c),
                     'policy':w.task_authorization.material(w.task_policy.effective(root,c['inputs'],environment='any')),
                     'assets':w.task_assets.refs(root,doc,c.get('source_assets',[]),w.fail)})

def historical(w,root,doc,c,old):
    if (not old or old.get('kind')!='runtime_observation' or old.get('status')!='passed'
            or old.get('criterion')!=c['id'] or not old.get('conditions')
            or old.get('adoption_basis')!=basis(w,root,doc,c)
            or w.fact_applicability(c,old) not in ('UNDECLARED','AS_OF','CURRENT')
            or w.files(root,old['evidence'],True)!=old['evidence']):return False
    if old.get('producer'):
        run=doc['facts'].get(old['producer'])
        if (not run or run.get('kind')!='command' or run.get('status')!='passed'
                or not w.artifact_ok(root,run['artifact'])
                or not w.instant(run['started_at'])<=w.instant(old['observed_at'])<=w.instant(run['at'])):return False
    return bool(old.get('source_inputs')) and w.digest(old['source_inputs'])==old['input_digest']

def baseline(w,root,revision,old):
    if not isinstance(revision,str) or not re.fullmatch('[a-f0-9]{40}',revision):w.fail('ADOPTION_FIXED_REVISION_REQUIRED')
    if w.git(root,'rev-parse',revision+'^{commit}').decode().strip()!=revision:w.fail('ADOPTION_FIXED_REVISION_REQUIRED')
    for name,identity in old['source_inputs'].items():
        tree=w.git(root,'ls-tree','-z',revision,'--',name)
        if identity['state']=='missing':
            if tree:w.fail('ADOPTION_BASELINE_MISMATCH')
        else:
            if not tree or tree.split(b' ',1)[0] not in (b'100644',b'100755'):w.fail('ADOPTION_BASELINE_MISMATCH')
            if int(w.git(root,'cat-file','-s',revision+':'+name))>w.MAX_LOG:w.fail('ADOPTION_BASELINE_SIZE_LIMIT')
            data=w.git(root,'show',revision+':'+name)
            if (hashlib.sha256(data).hexdigest()!=identity.get('sha256')
                    or (tree.startswith(b'100755')!=identity.get('executable'))):w.fail('ADOPTION_BASELINE_MISMATCH')

def available(w,root,doc,c,f):
    if f.get('criterion')!=c['id'] or f.get('status')!='passed':return False
    if w.task_failures.pending(doc,c['id']):return False
    old=doc['facts'].get(f.get('original'))
    if not historical(w,root,doc,c,old):return False
    if f.get('criterion_digest')!=w.criterion_stamp(root,doc,c):return False
    baseline(w,root,f['baseline_revision'],old)
    return bool(f.get('analyses')) and all(
        doc['facts'].get(fid,{}).get('kind')=='static_analysis'
        and doc['facts'][fid].get('criterion')==c['id']
        and w.fact_available(root,doc,c,doc['facts'][fid]) for fid in f['analyses'])

def adopt(w,root,ident,criterion,original,revision,analyses,reason):
    if not w.text(reason) or not isinstance(analyses,list) or not analyses or len(analyses)>16 or len(set(analyses))!=len(analyses):
        w.fail('ADOPTION_ANALYSIS_REQUIRED')
    with w.locked(root,ident):
        doc=w.load(root,ident);w.mutable(doc)
        c=next((x for x in doc['plan']['criteria'] if x['id']==criterion),None)
        if c is None:w.fail('CRITERION_UNKNOWN')
        w.ready(root,doc,criterion=c)
        if w.task_failures.pending(doc,criterion) or criterion in w.active_deferrals(root,doc):w.fail('ADOPTION_FAILURE_OR_DEFERRAL')
        old=doc['facts'].get(original)
        if not historical(w,root,doc,c,old):w.fail('ADOPTION_ORIGINAL_UNAVAILABLE')
        baseline(w,root,revision,old)
        current=w.files(root,c['inputs'])
        changed=sorted(n for n in set(current)|set(old['source_inputs']) if current.get(n)!=old['source_inputs'].get(n))
        if not changed:w.fail('ADOPTION_NOT_NEEDED')
        f={'id':uuid.uuid4().hex,'kind':'application','status':'passed','criterion':criterion,
           'at':w.now(),'original':original,'baseline_revision':revision,'analyses':analyses,
           'criterion_digest':w.criterion_stamp(root,doc,c),'changed_paths':changed,
           'reason':reason,'boundary':'Current applicability judgment, not a new runtime observation or execution.'}
        if not available(w,root,doc,c,f):w.fail('ADOPTION_ANALYSIS_UNAVAILABLE')
        doc['facts'][f['id']]=f;w.save(root,doc)
        return {'fact':f['id'],'original':original,'changed_path_count':len(changed)}
