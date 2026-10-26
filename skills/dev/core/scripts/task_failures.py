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
