"""Bounded failure/disposition relationships; facts are never re-signed here."""
MAX_ACTIONS = 8


def text(value):
    return isinstance(value, str) and bool(value.strip())


def conditions(value, fail, required=False):
    if (not isinstance(value, dict) or len(value)>16 or (required and not value)
            or any(not text(k) or len(k)>80 or not text(v) or len(v)>256 for k,v in value.items())):
        fail('FAILURE_CONDITIONS_REQUIRED' if required else 'OBSERVATION_CONDITIONS_INVALID')
    return value


def failure_facts(doc, criterion=None):
    return {fid:f for fid,f in doc.get('facts',{}).items()
            if f['kind']=='runtime_observation' and f['status']=='failed'
            and (criterion is None or f['criterion']==criterion)}


def resolved(doc, fid):
    entries=doc.get('failure_actions',{}).get(fid,[])
    return bool(entries and entries[-1]['action']=='resolve')


def pending(doc, criterion=None):
    return {fid:f for fid,f in failure_facts(doc,criterion).items() if not resolved(doc,fid)}


def reproduction(doc, fid):
    for entry in reversed(doc.get('failure_actions',{}).get(fid,[])):
        if entry['action']=='clarify':return entry['conditions']
    return doc['facts'][fid].get('conditions',{})


def append(mapping, key, entry, fail):
    entries=mapping.setdefault(key,[])
    if len(entries)>=MAX_ACTIONS:fail('FAILURE_ACTION_LIMIT')
    entries.append(entry)


def validate(doc, fail):
    if 'facts' not in doc:return  # A compacted complete receipt retains the disposition summary.
    if 'runtime_failures' in doc:fail('TASK_CONTRACT_UNSUPPORTED_USE_PINNED_TOOL')
    failures=failure_facts(doc)
    for field,maximum in [('failure_actions',128),('claim_deferrals',64)]:
        mapping=doc.get(field)
        if not isinstance(mapping,dict) or len(mapping)>maximum:fail('FAILURE_DISPOSITION_INVALID')
        for key,entries in mapping.items():
            if not isinstance(entries,list) or not 1<=len(entries)<=MAX_ACTIONS:fail('FAILURE_DISPOSITION_INVALID')
            if field=='failure_actions' and key not in failures:fail('FAILURE_REFERENCE_REQUIRED')
            for entry in entries:
                if (not isinstance(entry,dict) or not all(text(entry.get(k)) for k in ('id','at','action','reason'))):
                    fail('FAILURE_DISPOSITION_INVALID')
                base={'id','at','action','reason'}
                if field=='failure_actions':
                    action=entry['action']
                    extra={'resolve':{'evidence'},'clarify':{'conditions'},'reopen':set()}.get(action)
                    if extra is None or set(entry)!=base|extra:fail('FAILURE_DISPOSITION_INVALID')
                    if action=='clarify':conditions(entry['conditions'],fail,True)
                    if action=='resolve':
                        refs=entry['evidence']
                        if (not isinstance(refs,list) or not refs or len(refs)>32 or len(set(refs))!=len(refs)
                                or any(fid not in doc['facts'] for fid in refs)):fail('FACT_REFERENCE_MISSING')
                else:
                    if entry['action']=='reopen':
                        if set(entry)!=base|{'authority','decision_at'} or not text(entry['authority']) or not text(entry['decision_at']):fail('CLAIM_DEFERRAL_INVALID')
                    elif entry['action']=='defer':
                        if set(entry)!=base|{'authority','decision_at','handoff','criterion_digest','failures','checks'}:
                            fail('CLAIM_DEFERRAL_INVALID')
                        if (not text(entry['authority']) or not text(entry['decision_at']) or not text(entry['criterion_digest'])
                                or not isinstance(entry['handoff'],dict) or set(entry['handoff'])!={'path','sha256'}
                                or not all(text(x) for x in entry['handoff'].values())
                                or not isinstance(entry['failures'],list) or not isinstance(entry['checks'],list)
                                or any(fid not in doc['facts'] or doc['facts'][fid]['kind']!='command' for fid in entry['checks'])
                                or any(fid not in failures or failures[fid]['criterion']!=key for fid in entry['failures'])):
                            fail('CLAIM_DEFERRAL_INVALID')
                    else:fail('CLAIM_DEFERRAL_INVALID')
    for fact in doc['facts'].values():
        if 'resolved_failure' in fact:fail('FACT_LEGACY_RESOLUTION_REFUSED')
        if fact['kind']=='runtime_observation':conditions(fact.get('conditions',{}),fail)

# Review findings are bounded task-local judgments, not runtime failures.
MAX_REVIEW_FINDINGS = 64


def validate_reviews(doc, fail):
    if 'facts' not in doc:return
    findings=doc.get('review_findings')
    if not isinstance(findings,dict) or len(findings)>MAX_REVIEW_FINDINGS:fail('REVIEW_FINDING_LIMIT')
    for key,item in findings.items():
        if (not isinstance(item,dict) or set(item)!={'id','criterion','assessment','intent','dispositions'}
                or item['id']!=key or not text(item['criterion']) or not text(item['intent'])):fail('REVIEW_FINDING_INVALID')
        a=item['assessment']
        if (not isinstance(a,dict) or a.get('verdict') not in ('partial','unknown')
                or not text(a.get('reason')) or not text(a.get('criterion_digest'))
                or not isinstance(a.get('facts'),list) or any(x not in doc['facts'] for x in a['facts'])):fail('REVIEW_FINDING_INVALID')
        entries=item['dispositions']
        if not isinstance(entries,list) or len(entries)>MAX_ACTIONS:fail('REVIEW_DISPOSITION_LIMIT')
        for entry in entries:
            if (not isinstance(entry,dict) or set(entry)!={'id','at','action','reason','facts','criterion_digest','provenance'}
                    or entry['action'] not in ('addressed','judgment_error')
                    or not all(text(entry[k]) for k in ('id','at','reason','criterion_digest'))
                    or not isinstance(entry['facts'],list) or not entry['facts']
                    or any(x not in doc['facts'] for x in entry['facts'])):fail('REVIEW_DISPOSITION_INVALID')


def review_entries(doc):
    for item in doc.get('review_findings',{}).values():
        yield item['assessment']
        yield from item['dispositions']


def review_capture(w,doc,c,finding):
    intent=w.digest({'criterion':c['id'],'assessment':{k:v for k,v in finding.items() if k!='at'}})
    prior=next((x for x in doc['review_findings'].values() if x['intent']==intent and not x['dispositions']),None)
    if prior:return prior['id']
    if len(doc['review_findings'])>=MAX_REVIEW_FINDINGS:w.fail('REVIEW_FINDING_LIMIT')
    key=w.uuid.uuid4().hex
    doc['review_findings'][key]={'id':key,'criterion':c['id'],'assessment':finding,
                                 'intent':intent,'dispositions':[]}
    return key


def review_pending(w,root,doc,criterion=None):
    result={}
    for key,item in doc.get('review_findings',{}).items():
        if criterion is not None and item['criterion']!=criterion:continue
        c=next((x for x in (doc.get('plan') or {}).get('criteria',[]) if x['id']==item['criterion']),None)
        try:
            entry=item['dispositions'][-1] if item['dispositions'] else None
            valid=bool(c and entry and entry['criterion_digest']==w.criterion_stamp(root,doc,c)
                       and all(doc['facts'][fid]['kind'] in w.EVIDENCE_KINDS
                               and w.fact_available(root,doc,c,doc['facts'][fid]) for fid in entry['facts']))
            if valid and (item['assessment']['independent'] or w.review_required(doc['plan'],c)):
                valid=w.provenance_ok(root,doc,entry['provenance'])
            if valid and item['assessment'].get('provenance'):
                valid=w.provenance_ok(root,doc,item['assessment']['provenance'])
        except (ValueError,OSError,KeyError,TypeError):valid=False
        if not valid:result[key]=item
    return result


def review_dispose(w,root,ident,key,action,reason,refs,provenance=None):
    if action not in ('addressed','judgment_error') or not w.text(reason):w.fail('REVIEW_DISPOSITION_REQUIRED')
    if (not isinstance(refs,list) or not refs or len(set(refs))!=len(refs)
            or any(not isinstance(x,str) for x in refs)):w.fail('SUPPORT_SELECTION_REQUIRED')
    refs=sorted(refs)
    with w.locked(root,ident):
        doc=w.load(root,ident);w.mutable(doc)
        item=doc['review_findings'].get(key)
        if not item:w.fail('REVIEW_FINDING_REQUIRED')
        c=next(x for x in doc['plan']['criteria'] if x['id']==item['criterion'])
        w.ready(root,doc,criterion=c)
        if c['id'] in w.active_deferrals(root,doc):w.fail('CLAIM_DEFERRED_NOT_SUPPORTED')
        old=item['assessment'];stamp=w.criterion_stamp(root,doc,c)
        if any(fid not in doc['facts'] or doc['facts'][fid]['kind'] not in w.EVIDENCE_KINDS
               or not w.fact_available(root,doc,c,doc['facts'][fid]) for fid in refs):w.fail('CURRENT_FACT_REQUIRED')
        if action=='judgment_error':
            if stamp!=old['criterion_digest'] or refs!=old['facts']:w.fail('REVIEW_CORRECTION_BASIS_CHANGED')
        elif not any(w.instant(doc['facts'][fid]['at'])>w.instant(old['at']) for fid in refs):
            w.fail('REVIEW_NEW_FACT_REQUIRED')
        required=old['independent'] or w.review_required(doc['plan'],c)
        if required and not provenance:w.fail('REVIEW_PROVENANCE_REQUIRED')
        with w.ExitStack() as stack:
            proof=stack.enter_context(w.review_proof(root,doc,c,stamp,refs,'supported',provenance,
                                      {'finding':key,'disposition':action})) if provenance else None
            if old.get('provenance') and not w.provenance_ok(root,doc,old['provenance']):w.fail('REVIEW_PROVENANCE_INVALID')
            if action=='judgment_error' and old['independent']:
                original=w.read_json(w.safe(root,old['provenance']['path']))
                current=w.read_json(w.safe(root,proof['path']))
                if any(original[k]!=current[k] for k in ('host','context_id','reviewer')):w.fail('REVIEW_CORRECTION_CONTEXT_CHANGED')
            entry={'id':w.uuid.uuid4().hex,'at':w.now(),'action':action,'reason':reason,
                   'facts':refs,'criterion_digest':stamp,'provenance':proof}
            same=lambda e:{k:v for k,v in e.items() if k not in ('id','at')}
            if item['dispositions'] and same(item['dispositions'][-1])==same(entry):
                return {'finding':key,'criterion':c['id'],'disposition':action,'action_id':item['dispositions'][-1]['id']}
            if len(item['dispositions'])>=MAX_ACTIONS:w.fail('REVIEW_DISPOSITION_LIMIT')
            item['dispositions'].append(entry);doc['assessments'].pop(c['id'],None)
            w.save(root,doc)
        return {'finding':key,'criterion':c['id'],'disposition':action,'action_id':entry['id']}
