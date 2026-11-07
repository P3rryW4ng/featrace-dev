"""Owned walkthrough rounds; selected evidence is sealed before any managed deletion."""
import os
import fcntl
import hashlib
import re
import uuid
import task_storage

def inventory(w,root,path):
    folder=w.safe(root,path);result={}
    if not folder.is_dir():w.fail('WALK_OUTPUT_UNAVAILABLE')
    for count,p in enumerate(folder.rglob('*')):
        if count>=1024:w.fail('WALK_OUTPUT_COUNT_LIMIT')
        rel=p.relative_to(root).as_posix()
        w.safe(root,rel)
        if p.is_file():
            if len(result)>=512:w.fail('WALK_OUTPUT_COUNT_LIMIT')
            if p.stat().st_size>w.MAX_LOG:w.fail('WALK_OUTPUT_SIZE_LIMIT')
            result[rel]=w.file_identity(root,rel,True)
        elif not p.is_dir():w.fail('WALK_OUTPUT_INVALID')
    used=sum(p.stat().st_size for p in (root/'.featrace/artifacts').joinpath(folder.parent.name).rglob('*') if p.is_file())
    if used>64*1024*1024:w.fail('TASK_ARTIFACT_BUDGET')
    return result

def directories(w,root,path):
    folder=w.safe(root,path);result=[]
    for count,p in enumerate(folder.rglob('*')):
        if count>=1024:w.fail('WALK_OUTPUT_COUNT_LIMIT')
        rel=p.relative_to(root).as_posix();w.safe(root,rel)
        if p.is_dir():result.append(rel)
    return sorted(result)

def seal_lock(w,root,key):
    slot=int(hashlib.sha256(key.encode()).hexdigest()[:8],16)%64
    return w.safe(root,'.featrace/locks/walk-'+str(slot))

def validate(doc,fail):
    rounds=doc.get('walkthroughs',{})
    if not isinstance(rounds,dict) or len(rounds)>32:fail('WALK_LIMIT')
    for key,r in rounds.items():
        if (not isinstance(r,dict) or not re.fullmatch('[a-f0-9]{32}',key) or r.get('state') not in ('open','sealing','sealed','abandoned')
                or r.get('path')!='.featrace/artifacts/'+doc['id']+'/'+key+'.walk'
                or not r.get('criterion') or not r.get('target') or not r.get('input_digest')):
            fail('WALK_INVALID')
        origin=r.get('origin')
        if (not isinstance(origin,dict) or not isinstance(origin.get('criterion'),dict)
                or origin['criterion'].get('id')!=r['criterion']
                or not isinstance(origin.get('source_inputs'),dict)
                or task_storage.digest(origin['source_inputs'])!=r['input_digest']
                or task_storage.digest(origin)!=r.get('origin_digest')):
            fail('WALK_ORIGIN_INVALID')
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
        source_inputs=w.files(root,c['inputs'])
        stamp=w.criterion_stamp(root,doc,c)
        origin={'criterion':c,'source_inputs':source_inputs,
                'source_assets':w.task_assets.refs(root,doc,c.get('source_assets',[]),w.fail),
                'git_head':w.git(root,'rev-parse','HEAD').decode().strip()}
        if (w.digest(source_inputs)!=w.observation_stamp(root,c)
                or stamp!=w.criterion_stamp(root,doc,c)):w.fail('INPUT_MOVED')
        rounds[key]={'path':path,'criterion':criterion,'target':target,'input_digest':w.digest(source_inputs),
                     'criterion_digest':stamp,'origin':origin,'origin_digest':w.digest(origin),
                     'state':'open','started_at':w.now()}
        folder=w.safe(root,path);folder.mkdir(parents=True,exist_ok=False)
        try:w.save(root,doc)
        except Exception:
            try:published=key in w.load(root,ident).get('walkthroughs',{})
            except (ValueError,OSError):published=True
            if not published:folder.rmdir()
            raise
        return {'attempt':key,'output_directory':path,'boundary':'Metadata/output ownership only, not device permission or proof of execution.'}

def check(w,root,doc,key,c,historical=False):
    r=doc.get('walkthroughs',{}).get(key)
    if not r or r['state'] not in ('open','sealing'):w.fail('WALK_NOT_OPEN')
    if historical:
        origin=r['origin']
        if w.task_assets.refs(root,doc,origin['criterion'].get('source_assets',[]),w.fail)!=origin['source_assets']:
            w.fail('WALK_ORIGIN_INVALID')
    else:
        if r.get('discovery'):w.fail('WALK_NEGATIVE_PENDING')
        live=next((x for x in doc['plan']['criteria'] if x['id']==r['criterion']),None)
        if (not c or live!=c or r['criterion']!=c['id'] or r['input_digest']!=w.observation_stamp(root,c)
                or r['criterion_digest']!=w.criterion_stamp(root,doc,c)):w.fail('WALK_INPUT_CHANGED')
    if r.get('outputs') is not None and (inventory(w,root,r['path'])!=r['outputs'] or directories(w,root,r['path'])!=r.get('output_dirs',[])):w.fail('WALK_OUTPUT_CHANGED')
    return r


def seal(w,root,ident,key,observed_at,actual,evidence,status,conditions=None,historical=False,capture_basis=None):
    if status not in ('passed','failed','unavailable') or not w.text(actual):w.fail('OBSERVATION_REQUIRED')
    if historical and status=='passed':w.fail('WALK_HISTORICAL_PASS_REFUSED')
    if not historical and capture_basis is not None:w.fail('WALK_HISTORICAL_FLAG_REQUIRED')
    if capture_basis is not None and (not w.text(capture_basis) or len(capture_basis)>2048):w.fail('WALK_CAPTURE_BASIS_INVALID')
    if not observed_at and not historical:w.fail('OBSERVATION_REQUIRED')
    if observed_at and w.instant(observed_at)>w.datetime.now(w.timezone.utc):w.fail('FUTURE_OBSERVATION')
    conditions=w.task_failures.conditions({} if conditions is None else conditions,w.fail)
    intent={'status':status,'observed_at':observed_at,'actual':actual,'evidence':evidence,'conditions':conditions}
    if historical:intent.update(historical=True,capture_basis=capture_basis)
    if not evidence or len(evidence)>32 or len(set(evidence))!=len(evidence):w.fail('WALK_EVIDENCE_REQUIRED')
    with w.locked(root,ident):
        doc=w.load(root,ident);w.mutable(doc);r=doc.get('walkthroughs',{}).get(key)
        if not r:w.fail('WALK_NOT_OPEN')
        if r['state']=='sealed':
            if r.get('seal_intent')!=intent:w.fail('WALK_ALREADY_SEALED')
            return {'attempt':key,'fact':r['fact'],'reused':True}
        c=next((x for x in doc['plan']['criteria'] if x['id']==r['criterion']),None)
        check(w,root,doc,key,c,historical)
        if observed_at and w.instant(observed_at)<w.instant(r['started_at']):w.fail('WALK_OBSERVATION_PREDATES_ROUND')
        lock=seal_lock(w,root,key)
        fd=os.open(lock,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BaseException as exc:
            os.close(fd)
            if isinstance(exc,BlockingIOError):w.fail('WALK_SEAL_BUSY')
            raise
    try:
        outputs=inventory(w,root,r['path'])
        if any(p not in outputs for p in evidence):w.fail('WALK_EVIDENCE_OUTSIDE_ROUND')
        with w.locked(root,ident):
            doc=w.load(root,ident);w.mutable(doc);r=check(w,root,doc,key,c,historical)
            if r.get('seal_intent') is not None and r['seal_intent']!=intent:w.fail('WALK_SEAL_INTENT_CHANGED')
            if r.get('discovery'):
                original=r['discovery']['intent']
                if any(intent[field]!=original[field] for field in ('status','actual','evidence','conditions')):
                    w.fail('WALK_DISCOVERY_INTENT_CHANGED')
            output_dirs=directories(w,root,r['path'])
            if historical and (not observed_at or not capture_basis):
                if not r.get('discovery'):
                    r.update(outputs=outputs,output_dirs=output_dirs,discovery={'at':w.now(),'intent':intent})
                    w.save(root,doc)
                return {'attempt':key,'state':'discovery','reason':'WALK_CAPTURE_BASIS_REQUIRED','fact':None}
            r.update(state='sealing',outputs=outputs,output_dirs=output_dirs,seal_intent=intent);w.save(root,doc)
        copies=[]
        for path in evidence:
            doc=w.load(root,ident);source=w.safe(root,path)
            existing=next((a for a in doc.get('attachments',{}).values()
                           if a['origin']==str(source.resolve()) and a['sha256']==outputs[path]['sha256']
                           and w.artifact_ok(root,a)),None)
            copies.append(existing['path'] if existing else w.attach(root,ident,path)['path'])
        if historical:
            with w.locked(root,ident):
                doc=w.load(root,ident);w.mutable(doc);r=check(w,root,doc,key,c,True)
                if len(doc['facts'])>=w.MAX_FACTS:w.fail('FACT_LIMIT')
                refs=w.files(root,copies,True)
                for source,copy in zip(evidence,copies):
                    if refs[copy]['sha256']!=r['outputs'][source]['sha256']:w.fail('WALK_OUTPUT_CHANGED')
                origin=r['origin'];fact=uuid.uuid4().hex
                doc['facts'][fact]={'id':fact,'kind':'runtime_observation','criterion':r['criterion'],'status':status,
                    'observed_at':observed_at,'at':w.now(),'actual':actual,'input_digest':r['input_digest'],
                    'git_head_at_registration':w.git(root,'rev-parse','HEAD').decode().strip(),
                    'observed_target':r['target'],'source_assets':origin['criterion'].get('source_assets',[]),
                    'source_inputs':origin['source_inputs'],'evidence':refs,'conditions':conditions,
                    'walkthrough':key,'historical_negative':True,'capture_basis':capture_basis}
                # Historical negatives never become the latest current observation.
                # A failed fact still enters the ordinary pending-failure set.
                r.update(state='sealed',fact=fact);w.save(root,doc)
            return {'attempt':key,'fact':fact,'historical_negative':True,'selected_artifacts':len(copies)}
        doc=w.load(root,ident)
        f=next((f for f in doc['facts'].values() if f.get('walkthrough')==key),None)
        fact=f['id'] if f else w.observe(root,ident,c['id'],'runtime_observation',observed_at,actual,copies,status,
                                      r['target'],conditions=conditions,walkthrough=key)['fact']
        with w.locked(root,ident):
            doc=w.load(root,ident);r=check(w,root,doc,key,c);r.update(state='sealed',fact=fact);w.save(root,doc)
        return {'attempt':key,'fact':fact,'selected_artifacts':len(copies)}
    finally:os.close(fd)

def cleanup_files(w,root,doc):
    result=[];folders=[]
    for r in doc.get('walkthroughs',{}).values():
        if r['state'] not in ('sealed','abandoned'):w.fail('WALK_UNSEALED')
        folder=w.safe(root,r['path'])
        if not folder.exists():continue
        current=inventory(w,root,r['path'])
        # Permit already-deleted owned files on a cleanup retry, never new or modified files.
        if any(r.get('outputs',{}).get(p)!=identity for p,identity in current.items()):w.fail('WALK_OUTPUT_CHANGED')
        current_dirs=directories(w,root,r['path'])
        if set(current_dirs)-set(r.get('output_dirs',[])):w.fail('WALK_OUTPUT_CHANGED')
        result.extend(w.safe(root,p) for p in current)
        folders.extend(sorted((w.safe(root,p) for p in current_dirs),key=lambda p:len(p.parts),reverse=True))
        folders.append(folder)
    return result,folders
