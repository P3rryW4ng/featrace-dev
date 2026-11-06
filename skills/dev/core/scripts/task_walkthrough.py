"""Owned walkthrough rounds; selected evidence is sealed before any managed deletion."""
import os
import re
import uuid

def inventory(w,root,path):
    folder=w.safe(root,path);result={}
    if not folder.is_dir():w.fail('WALK_OUTPUT_UNAVAILABLE')
    for count,p in enumerate(folder.rglob('*')):
        if count>=1024:w.fail('WALK_OUTPUT_COUNT_LIMIT')
        rel=p.relative_to(root).as_posix()
        w.safe(root,rel)
        if p.name=='.seal-lock':continue
        if p.is_file():
            if len(result)>=512:w.fail('WALK_OUTPUT_COUNT_LIMIT')
            if p.stat().st_size>w.MAX_LOG:w.fail('WALK_OUTPUT_SIZE_LIMIT')
            result[rel]=w.file_identity(root,rel,True)
        elif not p.is_dir():w.fail('WALK_OUTPUT_INVALID')
    used=sum(p.stat().st_size for p in (root/'.featrace/artifacts').joinpath(folder.parent.name).rglob('*') if p.is_file())
    if used>64*1024*1024:w.fail('TASK_ARTIFACT_BUDGET')
    return result

def validate(doc,fail):
    rounds=doc.get('walkthroughs',{})
    if not isinstance(rounds,dict) or len(rounds)>32:fail('WALK_LIMIT')
    for key,r in rounds.items():
        if (not re.fullmatch('[a-f0-9]{32}',key) or r.get('state') not in ('open','sealing','sealed','abandoned')
                or r.get('path')!='.featrace/artifacts/'+doc['id']+'/'+key+'.walk'
                or not r.get('criterion') or not r.get('target') or not r.get('input_digest')):
            fail('WALK_INVALID')
        if r['state']=='abandoned' and doc.get('state')!='retired':fail('WALK_INVALID')
        if r['state']=='sealed' and 'facts' in doc:
            f=doc['facts'].get(r.get('fact'))
            if not f or f.get('walkthrough')!=key:fail('WALK_FACT_MISSING')

def start(w,root,ident,criterion,target):
    if not w.text(target):w.fail('OBSERVED_TARGET_REQUIRED')
    with w.locked(root,ident):
        doc=w.load(root,ident);w.mutable(doc)
        c=next((x for x in doc['plan']['criteria'] if x['id']==criterion),None)
        if c is None:w.fail('CRITERION_UNKNOWN')
        w.ready(root,doc,criterion=c)
        rounds=doc.setdefault('walkthroughs',{})
        if len(rounds)>=32:w.fail('WALK_LIMIT')
        key=uuid.uuid4().hex;path='.featrace/artifacts/'+ident+'/'+key+'.walk'
        rounds[key]={'path':path,'criterion':criterion,'target':target,'input_digest':w.observation_stamp(root,c),
                     'criterion_digest':w.criterion_stamp(root,doc,c),'state':'open','started_at':w.now()}
        folder=w.safe(root,path);folder.mkdir(parents=True,exist_ok=False)
        try:w.save(root,doc)
        except BaseException:folder.rmdir();raise
        return {'attempt':key,'output_directory':path,'boundary':'Metadata/output ownership only, not device permission or proof of execution.'}

def check(w,root,doc,key,c):
    r=doc.get('walkthroughs',{}).get(key)
    if not r or r['state']=='sealed' or r['criterion']!=c['id']:w.fail('WALK_NOT_OPEN')
    if r['input_digest']!=w.observation_stamp(root,c) or r['criterion_digest']!=w.criterion_stamp(root,doc,c):w.fail('WALK_INPUT_CHANGED')
    if r.get('outputs') is not None and inventory(w,root,r['path'])!=r['outputs']:w.fail('WALK_OUTPUT_CHANGED')
    return r

def seal(w,root,ident,key,observed_at,actual,evidence,status,conditions=None):
    if status not in ('passed','failed','unavailable') or not w.text(actual):w.fail('OBSERVATION_REQUIRED')
    if w.instant(observed_at)>w.datetime.now(w.timezone.utc):w.fail('FUTURE_OBSERVATION')
    w.task_failures.conditions({} if conditions is None else conditions,w.fail)
    if not evidence or len(evidence)>32 or len(set(evidence))!=len(evidence):w.fail('WALK_EVIDENCE_REQUIRED')
    with w.locked(root,ident):
        doc=w.load(root,ident);w.mutable(doc);r=doc.get('walkthroughs',{}).get(key)
        if not r:w.fail('WALK_NOT_OPEN')
        if r['state']=='sealed':
            f=doc['facts'][r['fact']]
            if (f['status']!=status or f['observed_at']!=observed_at or f['actual']!=actual):w.fail('WALK_ALREADY_SEALED')
            return {'attempt':key,'fact':r['fact'],'reused':True}
        c=next(x for x in doc['plan']['criteria'] if x['id']==r['criterion'])
        check(w,root,doc,key,c)
        if w.instant(observed_at)<w.instant(r['started_at']):w.fail('WALK_OBSERVATION_PREDATES_ROUND')
        folder=w.safe(root,r['path']);lock=folder/'.seal-lock'
        try:fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        except FileExistsError:w.fail('WALK_SEAL_BUSY')
        os.close(fd)
    try:
        outputs=inventory(w,root,r['path'])
        if any(p not in outputs for p in evidence):w.fail('WALK_EVIDENCE_OUTSIDE_ROUND')
        with w.locked(root,ident):
            doc=w.load(root,ident);r=check(w,root,doc,key,c)
            intent={'status':status,'observed_at':observed_at,'actual':actual,'evidence':evidence,'conditions':conditions}
            if r.get('seal_intent') is not None and r['seal_intent']!=intent:w.fail('WALK_SEAL_INTENT_CHANGED')
            r.update(state='sealing',outputs=outputs,seal_intent=intent);w.save(root,doc)
        copies=[]
        for path in evidence:
            doc=w.load(root,ident);source=w.safe(root,path)
            existing=next((a for a in doc.get('attachments',{}).values()
                           if a['origin']==str(source.resolve()) and a['sha256']==outputs[path]['sha256']
                           and w.artifact_ok(root,a)),None)
            copies.append(existing['path'] if existing else w.attach(root,ident,path)['path'])
        doc=w.load(root,ident)
        f=next((f for f in doc['facts'].values() if f.get('walkthrough')==key),None)
        fact=f['id'] if f else w.observe(root,ident,c['id'],'runtime_observation',observed_at,actual,copies,status,
                                      r['target'],conditions=conditions,walkthrough=key)['fact']
        with w.locked(root,ident):
            doc=w.load(root,ident);r=check(w,root,doc,key,c);r.update(state='sealed',fact=fact);w.save(root,doc)
        return {'attempt':key,'fact':fact,'selected_artifacts':len(copies)}
    finally:lock.unlink(missing_ok=True)

def cleanup_files(w,root,doc):
    result=[];folders=[]
    for r in doc.get('walkthroughs',{}).values():
        if r['state'] not in ('sealed','abandoned'):w.fail('WALK_UNSEALED')
        folder=w.safe(root,r['path'])
        if not folder.exists():continue
        current=inventory(w,root,r['path'])
        # Permit already-deleted owned files on a cleanup retry, never new or modified files.
        if any(r.get('outputs',{}).get(p)!=identity for p,identity in current.items()):w.fail('WALK_OUTPUT_CHANGED')
        result.extend(w.safe(root,p) for p in current)
        folders.extend(sorted((p for p in folder.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True))
        folders.append(folder)
    return result,folders
