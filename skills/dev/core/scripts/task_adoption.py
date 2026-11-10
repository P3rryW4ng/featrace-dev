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


def check_basis(w,root,doc,check):
    return w.digest({'check':check,'criteria':{c['id']:basis(w,root,doc,c)
                    for c in doc['plan']['criteria'] if c['id'] in check['covers']}})


def check_available(w,root,doc,check,f):
    if (f.get('kind')!='applicable_command' or f.get('check')!=check['id'] or f.get('status')!='passed'
            or check.get('acceptance',{}).get('mode')!='applicable_result'
            or check['environment']['kind'] not in ('local','test') or check.get('operation')=='device'):return False
    w.ready(root,doc,check=check)
    old=doc['facts'].get(f.get('original'))
    if (not old or old['kind']!='command' or old['status']!='passed'
            or doc['executions'].get(check['id'])!=old['id']
            or not w.timely(check,old) or not w.artifact_ok(root,old['artifact'])):return False
    stamp=check_basis(w,root,doc,check)
    if old.get('adoption_basis')!=stamp or f.get('basis')!=stamp:return False
    components={};current=w.check_stamp(root,doc,check,components)
    prior=old.get('identity_components',{})
    if (set(prior)!=set(components) or any(prior[k]!=components[k] for k in components if k!='selected_inputs')
            or current!=f.get('input_digest') or current==old['input_digest']):return False
    criteria=[c for c in doc['plan']['criteria'] if c['id'] in check['covers']]
    analyses=f.get('analyses',[])
    if not analyses or len(analyses)>64 or len(set(analyses))!=len(analyses):return False
    covered=set()
    for c in criteria:
        if (c.get('validity',{}).get('mode')=='current' or w.task_failures.pending(doc,c['id'])
                or w.task_failures.review_pending(w,root,doc,c['id']) or c['id'] in w.active_deferrals(root,doc)):return False
        if f.get('criterion_digests',{}).get(c['id'])!=w.criterion_stamp(root,doc,c):return False
        for fid in analyses:
            analysis=doc['facts'].get(fid,{})
            if analysis.get('criterion')==c['id']:
                if analysis.get('kind')!='static_analysis' or not w.fact_available(root,doc,c,analysis):return False
                covered.add(c['id'])
    return covered==set(check['covers']) and all(doc['facts'].get(fid,{}).get('criterion') in covered for fid in analyses)


def check_adopt(w,root,ident,check_id,original,analyses,reason):
    if not w.text(reason):w.fail('ADOPTION_ANALYSIS_REQUIRED')
    with w.locked(root,ident):
        doc=w.load(root,ident);w.mutable(doc)
        check=next((x for x in (doc.get('plan') or {}).get('checks',[]) if x['id']==check_id),None)
        if check is None:w.fail('CHECK_NOT_SELECTED')
        w.ready(root,doc,check=check)
        f={'id':uuid.uuid4().hex,'kind':'applicable_command','status':'passed','check':check_id,
           'original':original,'analyses':analyses,'at':w.now(),'reason':reason,
           'input_digest':w.check_stamp(root,doc,check),'basis':check_basis(w,root,doc,check),
           'criterion_digests':{c['id']:w.criterion_stamp(root,doc,c) for c in doc['plan']['criteria'] if c['id'] in check['covers']},
           'boundary':'Historical command applicability, not a current execution or new test result.'}
        if not check_available(w,root,doc,check,f):w.fail('CHECK_ADOPTION_UNAVAILABLE')
        comparable=lambda x:{k:v for k,v in x.items() if k not in ('id','at')}
        prior=next((x for x in doc['facts'].values() if comparable(x)==comparable(f)),None)
        if prior:return {'fact':prior['id'],'original':original,'execution':'adopted'}
        doc['facts'][f['id']]=f;w.save(root,doc)
        return {'fact':f['id'],'original':original,'execution':'adopted'}


def selected_check_application(w,root,doc,check):
    # Closure is based on each covered claim's explicit selection, never mere existence.
    common=None
    for cid in check['covers']:
        ids=set(doc['assessments'].get(cid,{}).get('facts',[]))
        valid={fid for fid in ids if doc['facts'].get(fid,{}).get('kind')=='applicable_command'
               and check_available(w,root,doc,check,doc['facts'][fid])}
        common=valid if common is None else common&valid
    return sorted(common or [])
