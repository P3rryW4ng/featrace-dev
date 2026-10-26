#!/usr/bin/env python3
"""Current-task delivery kernel. No legacy records, snapshots or history replay."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
import task_inputs
import task_policy
import task_execution
import task_failures
import task_authorization
import task_assets
from zoneinfo import ZoneInfo

CONTRACT = 5
MAX_CORRECTIONS = 8
MAX_FACTS = 128
EVIDENCE_KINDS = {'static_analysis', 'runtime_observation', 'command'}
MAX_RECORD = 256 * 1024
MAX_LOG = 16 * 1024 * 1024
MAX_OUTPUT = 16384
MAX_INPUTS = 512
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z')
CATEGORIES = {'presentation', 'interaction', 'state', 'interface', 'shared', 'device', 'configuration'}

class TaskError(ValueError):
    pass

def fail(message):
    raise TaskError(message)

class Parser(argparse.ArgumentParser):
    def error(self,message):
        fail('INVALID_ARGUMENTS')

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def now():
    return datetime.now(timezone.utc).isoformat()

def instant(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None: fail('TIMEZONE_REQUIRED')
    return result

def text(value):
    return isinstance(value, str) and bool(value.strip())

def git(root, *args):
    result = subprocess.run(['git', '--literal-pathspecs', '-C', str(root), *args], capture_output=True,
                            env={**os.environ, 'GIT_OPTIONAL_LOCKS':'0'})
    if result.returncode: fail('GIT_UNAVAILABLE')
    return result.stdout

def project(value):
    root = Path(value).resolve()
    if Path(os.fsdecode(git(root, 'rev-parse', '--show-toplevel')).strip()).resolve() != root:
        fail('GIT_ROOT_REQUIRED')
    return root

def safe(root, name):
    rel = Path(name)
    if (not text(name) or rel.is_absolute() or rel.as_posix() != name
            or any(p in ('.', '..', '.git') for p in rel.parts)):
        fail('UNSAFE_PATH')
    path = root
    for part in rel.parts:
        path /= part
        if path.is_symlink(): fail('SYMLINK_INPUT')
    return path

def task_path(root, ident):
    if not isinstance(ident, str) or not ID.fullmatch(ident) or ident in ('.', '..'):
        fail('INVALID_TASK_ID')
    return safe(root, '.featrace/tasks/' + ident + '.json')

def read_json(path):
    if path.is_symlink() or path.stat().st_size > MAX_RECORD: fail('RECORD_UNAVAILABLE')
    def pairs(items):
        out = {}
        for k,v in items:
            if k in out: fail('DUPLICATE_KEY')
            out[k] = v
        return out
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda _:fail('INVALID_JSON_CONSTANT'))

def load(root, ident):
    doc=read_json(task_path(root,ident))
    if doc.get('task_contract')!=CONTRACT or doc.get('id')!=ident:fail('TASK_CONTRACT_UNSUPPORTED_USE_PINNED_TOOL')
    if doc.get('checksum')!=digest({k:v for k,v in doc.items() if k!='checksum'}):fail('TASK_CHANGED')
    entries=doc.get('corrections',[])
    if not isinstance(entries,list) or len(entries)>MAX_CORRECTIONS:fail('CORRECTION_CONTRACT_INVALID')
    for entry in entries:
        if (not isinstance(entry,dict) or entry.get('status') not in ('open','complete')
                or not text(entry.get('reason')) or not text(entry.get('authority'))
                or not isinstance(entry.get('affected'),list) or not entry['affected']
                or entry.get('prior_receipt_digest')!=digest(entry.get('prior_receipt'))):fail('CORRECTION_CONTRACT_INVALID')
    if entries and (any(e['status']!='complete' for e in entries[:-1])
                    or (doc.get('state')=='complete')!=(entries[-1]['status']=='complete')):fail('CORRECTION_CONTRACT_INVALID')
    if 'facts' in doc:
        if not isinstance(doc['facts'],dict) or len(doc['facts'])>MAX_FACTS:fail('FACT_LIMIT')
        for fid,fact in doc['facts'].items():
            if fact.get('id')!=fid or fact.get('kind') not in EVIDENCE_KINDS:fail('FACT_INVALID')
        for section in ('executions','observations'):
            if any(fid not in doc['facts'] for fid in doc[section].values()):fail('FACT_REFERENCE_MISSING')
    task_failures.validate(doc,fail)
    task_authorization.validate(doc,fail)
    task_assets.validate(doc,fail)
    return doc

def save(root, doc):
    task_failures.validate(doc,fail)
    task_authorization.validate(doc,fail)
    task_assets.validate(doc,fail)
    path = task_path(root, doc['id'])
    doc['updated_at'] = now()
    doc['checksum'] = digest({k:v for k,v in doc.items() if k != 'checksum'})
    data = json.dumps(doc, ensure_ascii=False, indent=2, allow_nan=False).encode() + b'\n'
    if len(doc.get('facts',{}))>MAX_FACTS:fail('FACT_LIMIT')
    if len(data) > MAX_RECORD: fail('TASK_SIZE_LIMIT')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)

@contextmanager
def locked(root, ident, control=False):
    task_path(root, ident)
    slot = 'maintenance' if control else int(hashlib.sha256(ident.encode()).hexdigest()[:8],16) % 64
    path = safe(root, '.featrace/locks/' + str(slot))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as stream:
        try: fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: fail('TASK_BUSY')
        try: yield
        finally: fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

def mutable(doc):
    if doc['state'] == 'complete': fail('TASK_ALREADY_COMPLETE')


def open_correction(doc):
    entries=doc.get('corrections',[])
    return entries[-1] if entries and entries[-1]['status']=='open' else None


def correct(root,ident,affected,reason,authority):
    if (not text(reason) or not text(authority) or not isinstance(affected,list) or not affected
            or any(not isinstance(x,str) for x in affected) or len(set(affected))!=len(affected)):
        fail('CORRECTION_SCOPE_REQUIRED')
    with locked(root,ident):
        doc=load(root,ident)
        if doc['state']!='complete':fail('CORRECTION_REQUIRES_COMPLETE')
        if not doc.get('plan') or 'executions' not in doc:fail('CORRECTION_SOURCE_EXPIRED')
        validate_plan(root,doc['plan']);task_policy.check_local(root,git)
        criteria={c['id']:c for c in doc['plan']['criteria']}
        if set(affected)-set(criteria):fail('CORRECTION_SCOPE_REQUIRED')
        entries=doc.setdefault('corrections',[])
        if len(entries)>=MAX_CORRECTIONS:fail('CORRECTION_LIMIT')
        entry={'id':uuid.uuid4().hex,'status':'open','opened_at':now(),'reason':reason,'authority':authority,
               'affected':sorted(affected),'prior_receipt':doc['receipt'],'prior_receipt_digest':digest(doc['receipt']),
               'prior_claims':{c:{'criterion':criteria[c],'assessment':doc['assessments'].get(c),
                                  'observation':doc['observations'].get(c)} for c in affected},
               'prior_checks':{c['id']:doc['executions'].get(c['id']) for c in doc['plan']['checks'] if set(c['covers'])&set(affected)}}
        entries.append(entry)
        for c in affected:doc['assessments'].pop(c,None)
        doc['state']='correcting'
        save(root,doc)
    return {'id':ident,'state':'correcting','correction':entry['id'],'affected':entry['affected'],
            'boundary':'Original receipt/facts retained; only explicitly selected claims are reassessed. No old-contract conversion.'}

def file_identity(root, name, required=False):
    path = safe(root, name)
    if not path.exists():
        if required: fail('INPUT_MISSING')
        return {'state':'missing'}
    if not path.is_file(): fail('REGULAR_FILE_REQUIRED')
    before = path.stat(); h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024), b''): h.update(block)
    after = path.stat()
    if (before.st_ino,before.st_size,before.st_mtime_ns,before.st_mode) != (
            after.st_ino,after.st_size,after.st_mtime_ns,after.st_mode): fail('INPUT_MOVED')
    return {'state':'file','sha256':h.hexdigest(),'executable':bool(after.st_mode & 0o111)}

def files(root, names, required=False):
    return {name:file_identity(root,name,required) for name in sorted(set(names))}

def changes(root, baseline):
    tracked = git(root, 'diff', '--no-ext-diff', '--name-only', '-z', baseline, '--')
    new = git(root, 'ls-files', '--others', '--exclude-standard', '-z')
    return sorted({os.fsdecode(p) for p in (tracked+new).split(b'\0') if p
                   and not os.fsdecode(p).startswith(('.featrace/', '.agent-workflow/')) and os.fsdecode(p)!=task_policy.NAME})

def valid_inputs(root, values):
    if (not isinstance(values,list) or len(values)>MAX_INPUTS or any(not isinstance(p,str) for p in values)
            or len(set(values))!=len(values)): fail('INVALID_INPUT_LIST')
    for name in values:
        safe(root,name)
        if name==task_policy.NAME or name.startswith(('.featrace/', '.agent-workflow/')): fail('GENERATED_SCOPE_INPUT')

def validate_plan(root, plan):
    validate_execution_plan(root,plan)
    validate_acceptance_plan(root,plan)


def validate_execution_plan(root, plan):
    """Validate causal inputs, execution shape and freshness; no review-policy decision."""
    if not isinstance(plan,dict) or set(plan) != {'reason','categories','scope','exclusions','constraints','unknowns','criteria','checks','review'}:
        fail('PLAN_FIELDS_INVALID')
    if not text(plan['reason']) or not isinstance(plan['categories'],list) or not plan['categories'] or set(plan['categories'])-CATEGORIES:
        fail('PLAN_SCOPE_REQUIRED')
    valid_inputs(root,plan['scope'])
    if not plan['scope']: fail('PLAN_SCOPE_REQUIRED')
    if not isinstance(plan['exclusions'],dict) or not all(text(x) for x in plan['exclusions'].values()): fail('EXCLUSION_REASON_REQUIRED')
    valid_inputs(root,list(plan['exclusions']))
    if set(plan['scope']) & set(plan['exclusions']): fail('SCOPE_EXCLUSION_OVERLAP')
    if not isinstance(plan['constraints'],dict): fail('CONSTRAINT_DECISION_REQUIRED')
    valid_inputs(root,list(plan['constraints']))
    if not isinstance(plan['unknowns'],list) or len(plan['unknowns'])>64:fail('INVALID_UNKNOWNS')
    if not isinstance(plan['criteria'],list) or not 1<=len(plan['criteria'])<=64: fail('CRITERIA_REQUIRED')
    seen=set()
    for c in plan['criteria']:
        if (not isinstance(c,dict) or not {'id','expected','kind','inputs','proof'}<=set(c) or set(c)-{'id','expected','kind','inputs','sources','validity','proof','source_assets'} or not isinstance(c['id'],str)
                or not ID.fullmatch(c['id']) or c['id'] in seen or not text(c['expected'])
                or c['kind'] not in ('changed','unaffected')): fail('CRITERION_INVALID')
        valid_inputs(root,c['inputs']);valid_inputs(root,c.get('sources',[]))
        if not c['inputs'] or set(c['inputs'])-set(plan['scope']): fail('CRITERION_SCOPE_INVALID')
        if 'validity' in c:
            validity=c['validity']
            if not isinstance(validity,dict):fail('CRITERION_VALIDITY_INVALID')
            if validity.get('mode')=='as_of':
                if set(validity)!={'mode'}:fail('CRITERION_VALIDITY_INVALID')
            elif validity.get('mode')=='current':
                if (set(validity)!={'mode','target','max_age_seconds','reason'} or not text(validity['target'])
                        or not text(validity['reason']) or type(validity['max_age_seconds']) is not int
                        or validity['max_age_seconds']<=0):fail('CRITERION_VALIDITY_INVALID')
            else:fail('CRITERION_VALIDITY_INVALID')
        if not isinstance(c.get('source_assets',[]),list) or any(not isinstance(x,str) for x in c.get('source_assets',[])):fail('ASSET_SELECTION_INVALID')
        seen.add(c['id'])
    check_ids=set()
    if not isinstance(plan['checks'],list) or len(plan['checks'])>32: fail('CHECKS_INVALID')
    for c in plan['checks']:
        if (not isinstance(c,dict) or not {'id','argv','inputs','covers','reason','timeout','environment'}<=set(c)
                or set(c)-{'id','argv','inputs','covers','reason','timeout','environment','input_sets','external_inputs','env_keys','cache','operation','input_assets'}
                or not isinstance(c['id'],str) or not ID.fullmatch(c['id']) or c['id'] in check_ids
                or not isinstance(c['argv'],list) or not c['argv'] or not all(text(x) for x in c['argv'])
                or not text(c['reason']) or type(c['timeout']) is not int or not 1<=c['timeout']<=3600
                or not isinstance(c['environment'],dict) or not c['environment']
                or not all(text(k) and text(v) for k,v in c['environment'].items())): fail('CHECK_INVALID')
        valid_inputs(root,c['inputs'])
        task_inputs.validate_sets(c.get('input_sets',[]));task_inputs.validate_sets(c.get('external_inputs',[]),True)
        if not c['inputs'] and not c.get('input_sets'):fail('CHECK_SCOPE_INVALID')
        if c.get('operation','test') not in ('test','build','device'):fail('CHECK_OPERATION_INVALID')
        cache=c.get('cache',{'mode':'content'})
        if not isinstance(cache,dict) or set(cache)-{'mode','max_age_seconds'} or cache.get('mode') not in ('content','never'):fail('CHECK_CACHE_INVALID')
        if 'max_age_seconds' in cache and (type(cache['max_age_seconds']) is not int or not 0<cache['max_age_seconds']<=86400):fail('CHECK_CACHE_INVALID')
        if c['environment'].get('kind') not in ('local','test','remote','device','production'):fail('ENVIRONMENT_KIND_REQUIRED')
        if not text(c['environment'].get('target')):fail('ENVIRONMENT_TARGET_REQUIRED')
        if c['environment']['kind'] in ('remote','device') and c['environment'].get('policy_environment') not in ('local','test','production'):fail('POLICY_ENVIRONMENT_REQUIRED')
        if c['environment'].get('kind') in ('remote','device','production') and (cache['mode']!='never' or 'max_age_seconds' not in cache):fail('MUTABLE_ENVIRONMENT_CACHE_REFUSED')
        if not isinstance(c['covers'],list) or not c['covers'] or set(c['covers'])-seen: fail('CHECK_COVERAGE_INVALID')
        required={p for criterion in plan['criteria'] if criterion['id'] in c['covers'] for p in criterion['inputs']}
        if any(not task_inputs.covers(name,c['inputs'],c.get('input_sets',[])) for name in required):fail('CHECK_MISSING_CRITERION_INPUTS')
        if not isinstance(c.get('input_assets',[]),list) or any(not isinstance(x,str) for x in c.get('input_assets',[])):fail('ASSET_SELECTION_INVALID')
        check_ids.add(c['id'])
    for unknown in plan['unknowns']:
        if text(unknown):continue  # Explicit whole-task unknown.
        if (not isinstance(unknown,dict) or set(unknown)!={'reason','criteria','checks'} or not text(unknown['reason'])
                or not isinstance(unknown['criteria'],list) or not isinstance(unknown['checks'],list)
                or not (unknown['criteria'] or unknown['checks'])
                or any(not isinstance(x,str) or x not in seen for x in unknown['criteria'])
                or any(not isinstance(x,str) or x not in check_ids for x in unknown['checks'])):fail('INVALID_UNKNOWNS')
    for rule in plan['constraints'].values():
        if text(rule):continue  # Legacy strings explicitly retain task-wide applicability.
        if (not isinstance(rule,dict) or set(rule)!={'decision','criteria','checks'} or not text(rule['decision'])
                or not isinstance(rule['criteria'],list) or not isinstance(rule['checks'],list)
                or not (rule['criteria'] or rule['checks'])
                or any(not isinstance(x,str) or x not in seen for x in rule['criteria'])
                or any(not isinstance(x,str) or x not in check_ids for x in rule['checks'])):fail('CONSTRAINT_SCOPE_INVALID')


def validate_acceptance_plan(root, plan):
    """Validate proof and selected review; semantic necessity remains an actual investigation."""
    seen={c['id'] for c in plan['criteria']}
    for c in plan['criteria']:
        proof=c['proof']
        if (not isinstance(proof,dict) or set(proof)!={'any_of','reason'} or not text(proof['reason'])
                or not isinstance(proof['any_of'],list) or not 1<=len(proof['any_of'])<=8
                or any(not isinstance(group,list) or not group or len(set(group))!=len(group)
                       or any(not isinstance(k,str) or k not in EVIDENCE_KINDS for k in group) for group in proof['any_of'])):
            fail('PROOF_REQUIREMENTS_INVALID')
    review=plan['review']
    if (not isinstance(review,dict) or not {'independent','reason'}<=set(review) or set(review)-{'independent','reason','criteria'} or type(review['independent']) is not bool
            or not text(review['reason'])): fail('REVIEW_SCOPE_REQUIRED')
    if 'criteria' in review:
        selected=review['criteria']
        if (not isinstance(selected,list) or any(not isinstance(x,str) or x not in seen for x in selected)
                or len(set(selected))!=len(selected) or bool(selected)!=review['independent']):fail('REVIEW_SCOPE_REQUIRED')


def selected_constraints(plan,criterion=None,check=None):
    return {name:value for name,value in plan['constraints'].items()
            if text(value) or (criterion is None and check is None)
            or (criterion is not None and criterion['id'] in value['criteria'])
            or (check is not None and check['id'] in value['checks'])}


def review_required(plan,criterion):
    review=plan['review']
    return review['independent'] and criterion['id'] in review.get('criteria',[c['id'] for c in plan['criteria']])

def analysis(root, doc, plan=None):
    p = plan or doc['plan']
    changed=changes(root,doc['baseline'])
    authority={name for c in p['criteria'] for name in c.get('sources',[])}
    unexplained=sorted(set(changed)-set(p['scope'])-set(p['exclusions'])-set(p['constraints'])-authority)
    value={'scope':files(root,p['scope']), 'authority':files(root,authority,True),
           'constraints':files(root,p['constraints'],True),
           'source_assets':task_assets.refs(root,doc,sorted({x for c in p['criteria'] for x in c.get('source_assets',[])}),fail), 'policy':task_authorization.material(task_policy.effective(root,p['scope'],environment='any')),}
    return digest(value), unexplained

def begin(root, ident, request):
    task_policy.load(root);task_policy.check_local(root,git)
    try:maintenance=maintain(root,automatic=True)
    except (ValueError,OSError):maintenance={'retained':True,'reason':'MAINTENANCE_DEFERRED'}
    if not text(request): fail('REQUEST_REQUIRED')
    with locked(root,ident):
        if task_path(root,ident).exists(): fail('TASK_EXISTS')
        doc={'task_contract':CONTRACT,'id':ident,'request':request,'baseline':git(root,'rev-parse','HEAD').decode().strip(),
             'created_at':now(),'state':'draft','plan':None,'analysis_digest':None,'executions':{},
             'observations':{},'facts':{},'authorizations':{},'failure_actions':{},'claim_deferrals':{},'assessments':{},'limitations':[],'receipt':None}
        save(root,doc)
    return {'id':ident,'state':'draft','maintenance':maintenance}

def set_plan(root,ident,plan):
    validate_plan(root,plan)
    with locked(root,ident):
        doc=load(root,ident);mutable(doc)
        selected={c['id'] for c in plan['checks']};criteria={c['id'] for c in plan['criteria']}
        correction=open_correction(doc)
        if correction and set(correction['affected'])-criteria:fail('CORRECTION_CLAIM_REMOVED')
        if any(c not in selected and doc['facts'][fid]['status']!='passed' for c,fid in doc['executions'].items()):
            fail('UNRESOLVED_CHECK_REMOVED')
        if {f['criterion'] for f in task_failures.pending(doc).values()}-criteria:fail('UNRESOLVED_OBSERVATION_REMOVED')
        if set(doc.get('claim_deferrals',{}))-criteria:fail('DISPOSITION_CLAIM_REMOVED')
        if any(c not in criteria and doc['facts'][fid].get('status') in ('failed','unavailable') for c,fid in doc['observations'].items()):
            fail('UNRESOLVED_OBSERVATION_REMOVED')
        for criterion in plan['criteria']:
            task_assets.refs(root,doc,criterion.get('source_assets',[]),fail)
        for check in plan['checks']:
            task_assets.command(root,doc,check,fail)
        stamp,unexplained=analysis(root,doc,plan)
        doc['analysis_inputs']=files(root,set(plan['scope'])|set(plan['constraints']))
        doc['plan']=plan;doc['analysis_digest']=stamp;doc['state']='correcting' if correction else 'planned';save(root,doc)
    return {'id':ident,'state':'planned','unknowns':plan['unknowns'],'outside_scope_change_count':len(unexplained),
            'boundary':'Scope is declared task ownership, not all branch changes. Inspect actually related callers; outside changes do not certify no influence.'}

def relevant_paths(doc,criterion=None,check=None):
    if criterion is not None:return set(criterion['inputs'])
    if check is not None:
        return {p for c in doc['plan']['criteria'] if c['id'] in check['covers'] for p in c['inputs']} | (set(check['inputs'])&set(doc['plan']['scope']))
    return set(doc['plan']['scope'])


def ready(root,doc,criterion=None,check=None,investigate=False,excluded=()):
    if doc['plan'] is None: fail('PLAN_REQUIRED')
    execution_ready(root,doc,criterion,check,investigate,excluded)
    validate_acceptance_plan(root,doc['plan'])


def execution_ready(root,doc,criterion=None,check=None,investigate=False,excluded=()):
    if doc['plan'] is None: fail('PLAN_REQUIRED')
    validate_execution_plan(root,doc['plan'])
    selected=relevant_paths(doc,criterion,check)|set(selected_constraints(doc['plan'],criterion,check))
    baseline=doc.get('analysis_inputs')
    if baseline is None or any(file_identity(root,p)!=baseline.get(p) for p in selected):fail('SCOPE_REVIEW_REQUIRED')
    task_policy.effective(root,relevant_paths(doc,criterion,check),environment='any')
    criteria={criterion['id']} if criterion else set(check['covers']) if check else {c['id'] for c in doc['plan']['criteria']}
    criteria-=set(excluded)
    checks={check['id']} if check else {c['id'] for c in doc['plan']['checks'] if criteria.intersection(c['covers'])}
    for unknown in doc['plan']['unknowns']:
        if investigate:continue
        if text(unknown) or criteria.intersection(unknown['criteria']) or checks.intersection(unknown['checks']):fail('SCOPE_UNKNOWN')


def check_policy(root,doc,check,enforce=False):
    paths=relevant_paths(doc,check=check)|set(check['inputs'])
    for arg in check['argv']:
        candidate=Path(arg)
        if candidate.is_absolute():
            try:candidate=candidate.relative_to(root)
            except ValueError:continue
        if '..' not in candidate.parts and (root/candidate).is_file():paths.add(candidate.as_posix())
    environment=check['environment']
    realm=environment.get('policy_environment',environment['kind'])
    return task_policy.effective(root,paths,check.get('operation','test'),realm,enforce,
                                 check.get('input_sets',[]))


def check_identity_payload(root,doc,check):
    task_assets.command(root,doc,check,fail)
    command=check['argv'][0]
    if '/' in command:executable=Path(command) if Path(command).is_absolute() else root/command
    else:
        search=os.pathsep.join(str(Path(x) if Path(x).is_absolute() else root/x) for x in os.get_exec_path())
        found=shutil.which(command,path=search)
        if not found:fail('EXECUTABLE_UNAVAILABLE')
        executable=Path(found)
    executable=executable.resolve()
    runner=file_identity(executable.parent,executable.name,True)
    return {'argv':check['argv'],'inputs':task_inputs.signature(root,check['inputs'],check.get('input_sets',[]),check.get('external_inputs',[]),check.get('env_keys',[])),
            'input_assets':task_assets.refs(root,doc,check.get('input_assets',[]),fail),
            'executable':{'path':str(executable),'identity':runner},'environment':check['environment'],
            'constraints':files(root,selected_constraints(doc['plan'],check=check),True),
            'policy':task_authorization.material(check_policy(root,doc,check)),'protocol':task_execution.protocol(__file__)}

def check_stamp(root,doc,check):
    return digest(check_identity_payload(root,doc,check))


def execution_profile(root,doc,check,record,payload=None):
    payload=check_identity_payload(root,doc,check) if payload is None else payload
    return 'current' if record.get('input_digest')==digest(payload) else None

def criterion_stamp(root,doc,c):
    return digest({'criterion':c,'inputs':files(root,c['inputs']),'source_assets':task_assets.refs(root,doc,c.get('source_assets',[]),fail),'authority':files(root,c.get('sources',[]),True),
                   'constraints':files(root,selected_constraints(doc['plan'],criterion=c),True),
                   'review_required':review_required(doc['plan'],c),
                   'policy':task_authorization.material(task_policy.effective(root,c['inputs'],environment='any'))})

def timely(check,record):
    age=check.get('cache',{}).get('max_age_seconds')
    return age is None or (datetime.now(timezone.utc)-instant(record['at'])).total_seconds()<=age

def reusable(check,record):
    return check.get('cache',{}).get('mode','content')!='never' and timely(check,record)

def observation_stamp(root,c):
    # Facts describe actual selected behavior inputs, not a mutable acceptance sentence.
    return digest(files(root,c['inputs']))


def fact_applicability(criterion,record,environment=None):
    """Apply a claim's temporal scope without rewriting or expiring its original fact."""
    validity=criterion.get('validity')
    if validity is None:return 'UNDECLARED'
    if validity['mode']=='as_of':return 'AS_OF'
    if environment is None:
        if record.get('kind')!='runtime_observation':return 'CURRENT_STATE_NEEDS_RUNTIME'
        target=record.get('observed_target');at=record.get('observed_at')
    else:
        target=environment.get('target');at=record.get('started_at')
    if target!=validity['target']:return 'CURRENT_TARGET_MISMATCH'
    try:age=(datetime.now(timezone.utc)-instant(at)).total_seconds()
    except (ValueError,TypeError,AttributeError):return 'TIME_UNAVAILABLE'
    if age<0:return 'TIME_UNAVAILABLE'
    return 'CURRENT' if age<=validity['max_age_seconds'] else 'EXPIRED'


def artifact_ok(root,record):
    return file_identity(root,record['path'],True)['sha256']==record['sha256']

def authorization_stamp(doc,check):
    correction=open_correction(doc)
    return digest({'check':{k:v for k,v in check.items() if k not in ('reason','covers')},
                   'paths':sorted(relevant_paths(doc,check=check)),
                   'correction':correction['id'] if correction else None})


def authorize(root,ident,check_id,mode,authority,decision_at,expires_at,reason):
    if mode not in ('once','task') or not all(text(x) for x in (authority,decision_at,expires_at,reason)):fail('AUTHORIZATION_REQUIRED')
    decision=instant(decision_at);expiry=instant(expires_at);current=datetime.now(timezone.utc)
    if decision>current or not current<expiry or (expiry-current).total_seconds()>7*86400:fail('AUTHORIZATION_TIME_INVALID')
    with locked(root,ident):
        doc=load(root,ident);mutable(doc);task_policy.check_local(root,git)
        check=next((c for c in doc['plan']['checks'] if c['id']==check_id),None)
        if check is None:fail('CHECK_NOT_SELECTED')
        execution_ready(root,doc,check=check,investigate=True)
        rules=check_policy(root,doc,check)
        if any(r['permission']=='denied' for r in rules):fail('OPERATION_POLICY_DENIED')
        doc['authorizations']={gid:g for gid,g in doc['authorizations'].items()
            if not (instant(g['expires_at'])<=current or (g['mode']=='once' and g['uses']))}
        if len(doc['authorizations'])>=task_authorization.MAX_GRANTS:fail('AUTHORIZATION_LIMIT')
        gid=uuid.uuid4().hex
        doc['authorizations'][gid]={'id':gid,'check':check_id,'definition_digest':authorization_stamp(doc,check),
            'execution_digest':check_stamp(root,doc,check) if mode=='once' else None,
            'policy_digest':digest(task_authorization.material(rules)),'mode':mode,
            'authority':authority,'decision_at':decision_at,'reason':reason,'expires_at':expiry.isoformat(),'uses':[]}
        save(root,doc)
        return {'authorization':gid,'mode':mode,'check':check_id,'expires_at':expiry.isoformat(),
                'boundary':'Actual scoped human authority must exist; no standing policy or host permission changed.'}


def run_check(root,ident,check_id,investigate=False):
    with locked(root,ident):
        doc=load(root,ident);mutable(doc)
        task_policy.check_local(root,git)
        check=next((c for c in doc['plan']['checks'] if c['id']==check_id),None)
        if check is None:fail('CHECK_NOT_SELECTED')
        execution_ready(root,doc,check=check,investigate=investigate)
        stamp=check_stamp(root,doc,check);previous=doc['facts'].get(doc['executions'].get(check_id))
        expired=bool(previous and any(fact_applicability(c,previous,check['environment'])=='EXPIRED'
                                      for c in doc['plan']['criteria'] if c['id'] in check['covers']))
        if (previous and not expired and previous['status']=='passed' and previous['input_digest']==stamp
                and artifact_ok(root,previous['artifact']) and reusable(check,previous)):
            return {'check':check_id,'status':'passed','reused':True,'execution':previous['id']}
        if len(doc['facts'])>=MAX_FACTS:fail('FACT_LIMIT_USE_PRUNE')
        aid=uuid.uuid4().hex;rel='.featrace/artifacts/'+ident+'/'+aid+'.log';path=safe(root,rel)
        path.parent.mkdir(parents=True,exist_ok=True)
        used=sum(p.stat().st_size for p in path.parent.iterdir() if p.is_file())
        budget=min(MAX_LOG,64*1024*1024-used)
        if budget<4096:fail('TASK_ARTIFACT_BUDGET')
        started=now()
        rules=check_policy(root,doc,check)
        authorization=task_authorization.select(doc,check,stamp,digest(task_authorization.material(rules)),authorization_stamp(doc,check),rules,started,fail)
        if authorization['kind']=='grant':authorization['grant_proof']={k:v for k,v in doc['authorizations'][authorization['grant']].items() if k!='uses'}
        authorization['authority']=(doc['authorizations'][authorization['grant']]['authority'] if authorization['kind']=='grant' else task_policy.load(root)['authority'])
        authorization['rule_sources']=[{'source':rule['source'],'sha256':rule['sha256'],'authority':rule['authority']} for rule in rules]
        revision=git(root,'rev-parse','HEAD').decode().strip()
        source=task_execution.producer(__file__)
        start={'task':ident,'id':aid,'check':check_id,'input_digest':stamp,'input_format':1,
               'started_at':started,'producer':source,'definition_digest':digest(check),'authorization':authorization}
        reservation={'id':aid,'kind':'command','check':check_id,'status':'unavailable',
                     'purpose':'investigation' if investigate else 'verification','authorization':authorization,'input_assets':check.get('input_assets',[]),'input_digest':stamp,'definition_digest':digest(check),
                     'environment':check['environment'],'producer':source,'git_head_at_start':revision,
                     'started_at':started,'at':started,'exit_code':None,'reason':'EXECUTION_RESERVED_OUTCOME_UNKNOWN',
                     'artifact':{'path':rel,'sha256':'0'*64}}
        if previous:
            reservation['previous_result']=previous['id']
            if previous['status']!='passed':reservation['previous_failure']=previous['id']
        projected={**doc,'facts':{**doc['facts'],aid:reservation},'executions':{**doc['executions'],check_id:aid}}
        if len(json.dumps(projected,ensure_ascii=False,indent=2).encode())+1024>MAX_RECORD:fail('TASK_SIZE_LIMIT_BEFORE_EXECUTION')
        if authorization['kind']=='grant':
            g=doc['authorizations'][authorization['grant']]
            if len(g['uses'])>=128:fail('AUTHORIZATION_LIMIT')
            g['uses'].append(aid)
        doc['facts'][aid]=reservation;doc['executions'][check_id]=aid
        save(root,doc)  # The unavailable reservation and grant use are atomic before launching.
        status,code,interrupted,reason=task_execution.invoke(check['argv'],root,path,budget,check['timeout'],start)
        try:
            if check_stamp(root,doc,check)!=stamp:status='unavailable';reason=reason or 'EXECUTION_INPUT_MOVED'
        except (ValueError,OSError):
            status='unavailable';reason=reason or 'EXECUTION_IDENTITY_UNAVAILABLE'
        ended=now()
        record={'id':aid,'kind':'command','check':check_id,'status':status,
                'purpose':'investigation' if investigate else 'verification','authorization':authorization,'input_assets':check.get('input_assets',[]),'input_digest':stamp,
                'definition_digest':digest(check),'environment':check['environment'],'producer':source,
                'git_head_at_start':revision,'started_at':started,'at':ended,'exit_code':code}
        if reason:record['reason']=reason
        task_execution.finish(path,budget,{'id':aid,'status':status,'exit_code':code,'ended_at':ended,'reason':reason})
        record['artifact']={'path':rel,'sha256':file_identity(root,rel,True)['sha256']}
        if previous:
            if interrupted:record['previous_result']=previous['id']
            if previous['status']!='passed':record['previous_failure']=previous['id']
        doc['facts'][aid]=record;doc['executions'][check_id]=aid;save(root,doc)
        if interrupted is not None:raise interrupted
        return {'check':check_id,'status':status,'reused':False,'execution':aid}

def attach(root,ident,source,role="evidence"):
    """Copy only selected evidence; never claim ownership of or delete its original."""
    with locked(root,ident):
        doc=load(root,ident);mutable(doc)
        original=task_assets.source(root,ident,source,role,fail)
        if not original.is_file():fail('ATTACHMENT_SOURCE_REQUIRED')
        before=original.stat()
        if before.st_size>MAX_LOG:fail('ATTACHMENT_SIZE_LIMIT')
        attachments=doc.setdefault('attachments',{})
        if len(attachments)>=32:fail('ATTACHMENT_COUNT_LIMIT')
        suffix=original.suffix
        if not re.fullmatch(r'\.[A-Za-z0-9]{1,10}',suffix) or suffix=='.log':suffix='.asset'
        key=uuid.uuid4().hex;rel='.featrace/artifacts/'+ident+'/'+key+suffix;target=safe(root,rel)
        target.parent.mkdir(parents=True,exist_ok=True)
        used=sum(p.stat().st_size for p in target.parent.iterdir() if p.is_file())
        if used+before.st_size>64*1024*1024:fail('TASK_ARTIFACT_BUDGET')
        try:
            h=hashlib.sha256();written=0
            with original.open('rb') as reader,target.open('xb') as output:
                for block in iter(lambda:reader.read(65536),b''):
                    written+=len(block)
                    if written>MAX_LOG or used+written>64*1024*1024:fail('ATTACHMENT_SIZE_LIMIT')
                    h.update(block);output.write(block)
            after=original.stat()
            if (before.st_ino,before.st_size,before.st_mtime_ns,before.st_mode)!=(after.st_ino,after.st_size,after.st_mtime_ns,after.st_mode):fail('INPUT_MOVED')
            attachments[key]={'path':rel,'sha256':h.hexdigest(),'bytes':written,'captured_at':now(),'role':role,'origin':str(original)}
            save(root,doc)
        except BaseException:
            target.unlink(missing_ok=True);raise
        return {'attachment':key,'path':rel,'bytes':written,'role':role,'original_preserved':True,'boundary':'Selected snapshot only, not a claim that the external source is still current.'}


def observe(root,ident,criterion,kind,observed_at,actual,evidence,status='passed',target=None,producer=None,conditions=None):
    if (kind not in ('static_analysis','runtime_observation') or not text(actual) or not evidence
            or status not in ('passed','failed','unavailable')):fail('OBSERVATION_REQUIRED')
    if instant(observed_at)>datetime.now(timezone.utc):fail('FUTURE_OBSERVATION')
    with locked(root,ident):
        doc=load(root,ident);mutable(doc)
        if len(doc['facts'])>=MAX_FACTS:fail('FACT_LIMIT')
        if instant(observed_at)<instant(doc['created_at']):fail('OBSERVATION_PREDATES_TASK')
        if kind=='runtime_observation' and not text(target):fail('OBSERVED_TARGET_REQUIRED')
        c=next((c for c in doc['plan']['criteria'] if c['id']==criterion),None)
        if c is None:fail('CRITERION_UNKNOWN')
        ready(root,doc,criterion=c)
        stamp=observation_stamp(root,c);refs=files(root,evidence,True)
        if observation_stamp(root,c)!=stamp:fail('INPUT_MOVED')
        rec={'id':uuid.uuid4().hex,'kind':kind,'criterion':criterion,'status':status,'observed_at':observed_at,
             'at':now(),'actual':actual,'input_digest':stamp,
             'git_head_at_registration':git(root,'rev-parse','HEAD').decode().strip(),
             'observed_target':target if kind=='runtime_observation' else 'local selected sources','source_assets':c.get('source_assets',[]),'evidence':refs}
        if kind=='runtime_observation':rec['conditions']=task_failures.conditions({} if conditions is None else conditions,fail)
        elif conditions is not None:fail('CONDITIONS_REQUIRE_RUNTIME')
        if producer:
            run=doc['facts'].get(producer)
            check=next((x for x in doc['plan']['checks'] if run and x['id']==run.get('check')),None)
            if (not run or run['kind']!='command' or run['status']!='passed' or not check or criterion not in check['covers']
                    or not execution_profile(root,doc,check,run) or not artifact_ok(root,run['artifact'])
                    or not instant(run['started_at'])<=instant(observed_at)<=instant(run['at'])):fail('PRODUCER_NOT_APPLICABLE')
            rec['producer']=producer
        applicability=fact_applicability(c,rec)
        if status=='passed' and applicability in ('CURRENT_TARGET_MISMATCH','CURRENT_STATE_NEEDS_RUNTIME'):fail(applicability)
        old=doc['facts'].get(doc['observations'].get(criterion))
        if old and old['status']!='passed':rec['previous_failure']=old['id']
        doc['facts'][rec['id']]=rec;doc['observations'][criterion]=rec['id'];save(root,doc)
        return {'criterion':criterion,'fact':rec['id'],'kind':kind}

def active_deferrals(root,doc):
    result={}
    for cid,entries in doc.get('claim_deferrals',{}).items():
        entry=entries[-1]
        if entry['action']!='defer':continue
        c=next((c for c in doc['plan']['criteria'] if c['id']==cid),None)
        try:
            known=set(entry['failures'])
            changed_negative=any(f['status']!='passed' and f['id'] not in entry['checks']
                                 for f in doc['facts'].values() if f['kind']=='command'
                                 and any(x['id']==f['check'] and cid in x['covers'] for x in doc['plan']['checks']))
            if (c and criterion_stamp(root,doc,c)==entry['criterion_digest']
                    and artifact_ok(root,entry['handoff'])
                    and canonical(failure_handoff(doc,cid)).decode() in safe(root,entry['handoff']['path']).read_text()
                    and set(task_failures.failure_facts(doc,cid))<=known and not changed_negative):
                result[cid]=entry
        except (ValueError,OSError,KeyError,TypeError):pass
    return result


def failure_action(root,ident,failure_id,action,reason,evidence=None,conditions=None):
    if action not in ('resolve','clarify','reopen') or not text(reason):fail('FAILURE_ACTION_REQUIRED')
    with locked(root,ident):
        doc=load(root,ident);mutable(doc);task_policy.check_local(root,git)
        failure=task_failures.failure_facts(doc).get(failure_id)
        if failure is None:fail('FAILURE_REFERENCE_REQUIRED')
        cid=failure['criterion'];entry={'id':uuid.uuid4().hex,'at':now(),'action':action,'reason':reason}
        if action=='clarify':
            if evidence:fail('FAILURE_ACTION_INVALID')
            task_failures.conditions(conditions,fail,True)
            if files(root,failure['evidence'],True)!=failure['evidence']:fail('FAILURE_EVIDENCE_UNAVAILABLE')
            entry['conditions']=conditions
        elif action=='resolve':
            if conditions is not None:fail('FAILURE_ACTION_INVALID')
            c=next((c for c in doc['plan']['criteria'] if c['id']==cid),None)
            if c is None:fail('CRITERION_UNKNOWN')
            ready(root,doc,criterion=c)
            expected=task_failures.conditions(task_failures.reproduction(doc,failure_id),fail,True)
            if (not isinstance(evidence,list) or not evidence or len(evidence)>32
                    or any(not isinstance(fid,str) for fid in evidence) or len(set(evidence))!=len(evidence)):
                fail('TARGETED_RUNTIME_PROOF_REQUIRED')
            runtime=[]
            for fid in evidence:
                f=doc['facts'].get(fid)
                if not f or not fact_available(root,doc,c,f):fail('CURRENT_FACT_REQUIRED')
                if f['kind']=='runtime_observation':
                    if f['criterion']!=cid or f.get('conditions')!=expected:fail('FAILURE_CONDITIONS_MISMATCH')
                    if instant(f['observed_at'])<instant(failure['observed_at']):fail('PASS_PREDATES_FAILURE')
                    runtime.append(f)
            if not runtime:fail('TARGETED_RUNTIME_PROOF_REQUIRED')
            entry['evidence']=sorted(evidence)
        elif evidence or conditions is not None:fail('FAILURE_ACTION_INVALID')
        task_failures.append(doc['failure_actions'],failure_id,entry,fail)
        doc['assessments'].pop(cid,None);save(root,doc)
        return {'failure':failure_id,'criterion':cid,'action':action,'action_id':entry['id'],
                'boundary':'Original facts/times retained; condition declarations and authority need actual investigation.'}


def failure_handoff(doc,criterion):
    """Small durable issue context, not an everlasting copy of logs/attachments."""
    return {fid:{'actual':f['actual'],'target':f['observed_target'],'observed_at':f['observed_at'],
                 'conditions':task_failures.reproduction(doc,fid),'evidence':f['evidence']}
            for fid,f in task_failures.pending(doc,criterion).items()}


def defer_claim(root,ident,criterion,reason,authority,decision_at,handoff=None,reopen=False,exclude=False):
    if not reopen and not exclude:fail('EXPLICIT_DELIVERY_EXCLUSION_REQUIRED')
    if not text(reason) or not text(authority) or not text(decision_at):fail('PRODUCT_DECISION_REQUIRED')
    if instant(decision_at)>datetime.now(timezone.utc):fail('FUTURE_DECISION')
    with locked(root,ident):
        doc=load(root,ident);mutable(doc);task_policy.check_local(root,git)
        c=next((c for c in doc['plan']['criteria'] if c['id']==criterion),None)
        if c is None:fail('CRITERION_UNKNOWN')
        entry={'id':uuid.uuid4().hex,'at':now(),'action':'reopen' if reopen else 'defer','reason':reason,
               'authority':authority,'decision_at':decision_at}
        if not reopen:
            if not text(handoff) or handoff.startswith(('.featrace/','.agent-workflow/')):fail('DEFERRAL_HANDOFF_MUST_SURVIVE')
            path=safe(root,handoff)
            if not path.is_file() or path.stat().st_size>MAX_RECORD:fail('DEFERRAL_HANDOFF_UNAVAILABLE')
            contents=path.read_text()
            if (reason not in contents or authority not in contents or c['expected'] not in contents
                    or canonical(failure_handoff(doc,criterion)).decode() not in contents):fail('DEFERRAL_HANDOFF_INCOMPLETE')
            entry.update(handoff={'path':handoff,'sha256':file_identity(root,handoff,True)['sha256']},
                         criterion_digest=criterion_stamp(root,doc,c),
                         failures=sorted(task_failures.failure_facts(doc,criterion)),
                         checks=sorted(fid for fid,f in doc['facts'].items() if f['kind']=='command'
                                       and any(x['id']==f['check'] and criterion in x['covers'] for x in doc['plan']['checks'])))
        task_failures.append(doc['claim_deferrals'],criterion,entry,fail)
        doc['assessments'].pop(criterion,None);save(root,doc)
        return {'criterion':criterion,'disposition':entry['action'],'decision_at':decision_at,
                'boundary':'Entire named promise excluded from this delivery, never repaired or supported; an unchanged prior product decision needs no repeated approval.'}


def fact_available(root,doc,c,fact,checked=None):
    try:return _fact_available(root,doc,c,fact,checked)
    except (ValueError,OSError,KeyError,TypeError):return False


def _fact_available(root,doc,c,fact,checked=None):
    if fact['status']!='passed':return False
    if fact['kind']=='command':
        check=next((x for x in doc['plan']['checks'] if x['id']==fact['check']),None)
        if not check or c['id'] not in check['covers']:return False
        # Latest failed/unavailable command blocks closure; a retained success is not a replacement for it.
        if fact_applicability(c,fact,check['environment']) not in ('UNDECLARED','AS_OF','CURRENT'):return False
        if checked is not None and fact['id'] in checked:return checked[fact['id']]
        valid=bool(execution_profile(root,doc,check,fact) and artifact_ok(root,fact['artifact']) and timely(check,fact))
        if checked is not None:checked[fact['id']]=valid
        return valid
    if fact['input_digest']!=observation_stamp(root,c):return False
    if fact_applicability(c,fact) not in ('UNDECLARED','AS_OF','CURRENT'):return False
    if files(root,fact['evidence'],True)!=fact['evidence']:return False
    if fact.get('producer'):
        producer=doc['facts'].get(fact['producer'])
        if not producer or not fact_available(root,doc,c,producer,checked):return False
    return True


def facts(root,doc,c,checked=None):
    return sorted(fid for fid,fact in doc.get('facts',{}).items() if fact_available(root,doc,c,fact,checked))


def prune(root,ident,apply=False):
    """Explicitly forget only unreferenced passing facts, never current/negative/correction roots."""
    with locked(root,ident):
        doc=load(root,ident);mutable(doc)
        keep=set(doc['observations'].values())|set(doc['executions'].values())|set(task_failures.failure_facts(doc))
        for entries in doc['failure_actions'].values():
            for action in entries:keep.update(action.get('evidence',[]))
        for entries in doc['claim_deferrals'].values():
            for action in entries:
                keep.update(action.get('checks',[]));keep.update(action.get('failures',[]))
        for finding in doc['assessments'].values():keep.update(finding['facts'])
        for fid,fact in doc['facts'].items():
            if fact['status']!='passed' or fact.get('previous_failure'):keep.add(fid)
        for entry in doc.get('corrections',[]):
            keep.update(fid for fid in entry.get('prior_checks',{}).values() if fid)
            for claim in entry.get('prior_claims',{}).values():
                if claim.get('observation'):keep.add(claim['observation'])
                keep.update((claim.get('assessment') or {}).get('facts',[]))
        pending=list(keep)
        while pending:
            fact=doc['facts'].get(pending.pop())
            if not fact:fail('FACT_REFERENCE_MISSING')
            for key in ('producer','previous_failure','previous_result'):
                ref=fact.get(key)
                if isinstance(ref,str) and ref and ref not in keep:keep.add(ref);pending.append(ref)
        candidates=sorted(set(doc['facts'])-keep)
        used_assets={x for c in doc['plan']['criteria'] for x in c.get('source_assets',[])}|{x for c in doc['plan']['checks'] for x in c.get('input_assets',[])}
        retained_paths=set()
        for fid in keep:
            fact=doc['facts'][fid];used_assets.update(fact.get('input_assets',[]));used_assets.update(fact.get('source_assets',[]))
            retained_paths.update(fact.get('evidence',{}))
        for correction in doc.get('corrections',[]):
            for claim in correction.get('prior_claims',{}).values():used_assets.update(claim['criterion'].get('source_assets',[]))
        asset_candidates={key:a for key,a in doc.get('attachments',{}).items()
                          if a['role']=='input' and key not in used_assets and a['path'] not in retained_paths}
        for a in asset_candidates.values():
            path=safe(root,a['path'])
            if path.exists() and not artifact_ok(root,a):fail('PRUNE_CHANGED_ASSET')
        if apply:
            for fid in candidates:doc['facts'].pop(fid)
            save(root,doc)  # Retain ownership until each unreferenced copy is removed; absence is safe on retry.
            for key,a in asset_candidates.items():
                path=safe(root,a['path'])
                if path.exists():
                    if not artifact_ok(root,a):fail('PRUNE_CHANGED_ASSET')
                    path.unlink()
                doc['attachments'].pop(key)
            save(root,doc)
        return {'id':ident,'apply':apply,'removable_fact_count':len(candidates),'removable_input_assets':len(asset_candidates),
                'boundary':'Explicitly forget unreferenced passing metadata and intact unused input copies only; preserve negatives, selected/correction sources and external originals.'}


def selected_support(root,doc,c,ids,checked=None):
    if not isinstance(ids,list) or not ids or any(not isinstance(x,str) for x in ids) or len(ids)!=len(set(ids)):fail('SUPPORT_SELECTION_REQUIRED')
    chosen=[]
    for fid in ids:
        fact=doc['facts'].get(fid)
        if not fact or not fact_available(root,doc,c,fact,checked):fail('CURRENT_FACT_REQUIRED')
        chosen.append(fact)
    kinds={f['kind'] for f in chosen}
    if not any(set(group)<=kinds for group in c['proof']['any_of']):fail('PROOF_REQUIREMENTS_UNMET')
    return sorted(ids)

def assess(root,ident,criterion,verdict,reason,independent=False,provenance=None,fact_ids=None):
    if verdict not in ('supported','partial','unknown') or not text(reason):fail('ASSESSMENT_REQUIRED')
    with locked(root,ident):
        doc=load(root,ident);mutable(doc)
        c=next((c for c in doc['plan']['criteria'] if c['id']==criterion),None)
        if c is None:fail('CRITERION_UNKNOWN')
        ready(root,doc,criterion=c)
        if criterion in active_deferrals(root,doc):fail('CLAIM_DEFERRED_NOT_SUPPORTED')
        refs=selected_support(root,doc,c,fact_ids) if verdict=='supported' else sorted(fact_ids or [])
        if any(fid not in doc['facts'] for fid in refs):fail('FACT_REFERENCE_MISSING')
        proof=None
        if independent:
            if not provenance:fail('REVIEW_PROVENANCE_REQUIRED')
            p=read_json(safe(root,provenance))
            if (not isinstance(p,dict) or p.get('task')!=ident or p.get('criterion')!=criterion
                    or p.get('criterion_digest')!=criterion_stamp(root,doc,c) or p.get('facts')!=refs
                    or p.get('verdict')!=verdict or p.get('fresh_context') is not True
                    or not all(text(p.get(k)) for k in ('host','context_id','reviewer','reason'))):fail('REVIEW_PROVENANCE_INVALID')
            proof={'path':provenance,'sha256':file_identity(root,provenance,True)['sha256']}
        doc['assessments'][criterion]={'verdict':verdict,'reason':reason,'facts':refs,
            'criterion_digest':criterion_stamp(root,doc,c),'at':now(),'independent':independent,'provenance':proof}
        save(root,doc)
        return {'criterion':criterion,'verdict':verdict}

def view(root,ident,offset=0,limit=20,blocker_offset=0):
    if (type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=25
            or type(blocker_offset) is not int or blocker_offset<0):fail('PAGE_INVALID')
    doc=load(root,ident)
    if doc['state']=='complete':
        return {'id':ident,'state':'complete','as_of':{k:v for k,v in doc['receipt'].items() if k not in ('limitations','deferrals')},
                'limitation_count':len(doc['receipt']['limitations']),'deferred_count':len(doc['receipt'].get('deferrals',{})),'details':'detail --section receipt',
                'correction_count':len(doc.get('corrections',[])), 'current_revision_certified':False}
    blockers=[];rows=[];checked={};scope_readiness={'ready':True}
    deferred=active_deferrals(root,doc) if doc['plan'] else {}
    try:ready(root,doc,excluded=deferred)
    except (ValueError,OSError) as exc:
        # Only known position-free codes are public; never return arbitrary exception text.
        known={'PLAN_REQUIRED','SCOPE_REVIEW_REQUIRED','SCOPE_UNKNOWN','PROJECT_POLICY_REQUIRED',
               'APPLICABLE_RULE_CHANGED','POLICY_FIELDS_INVALID','POLICY_UNAVAILABLE','POLICY_RULE_INVALID'}
        reason=str(exc) if isinstance(exc,(TaskError,task_policy.PolicyError)) and str(exc) in known else 'SCOPE_NOT_READY'
        scope_readiness={'ready':False,'reason':reason,
                         'details':'detail --section plan' if doc['plan'] else 'detail --section request'}
        blockers.append('SCOPE_NOT_READY')
    blockers.extend('DEFERRAL_STALE:'+cid for cid,entries in doc.get('claim_deferrals',{}).items() if entries[-1]['action']=='defer' and cid not in deferred)
    blockers.extend('RUNTIME_FAILURE:'+fid for fid,f in sorted(task_failures.pending(doc).items()) if f['criterion'] not in deferred)
    if doc['plan']:
        for check in doc['plan']['checks']:
            if set(check['covers'])<=set(deferred):continue
            result=doc['facts'].get(doc['executions'].get(check['id']))
            try:current=bool(result and execution_profile(root,doc,check,result) and artifact_ok(root,result['artifact']) and timely(check,result))
            except (ValueError,OSError):current=False
            if result:checked[result['id']]=bool(current and result['status']=='passed')
            if not result or not checked[result['id']]:blockers.append('CHECK:'+check['id'])
        for c in doc['plan']['criteria']:
            if c['id'] in deferred:
                rows.append({'id':c['id'],'status':'deferred','unresolved_failure_count':len(task_failures.pending(doc,c['id']))});continue
            finding=doc['assessments'].get(c['id']);valid=False
            observation=doc['facts'].get(doc['observations'].get(c['id']))
            if (observation and observation['status']!='passed'
                    and not task_failures.resolved(doc,observation['id'])):blockers.append('OBSERVATION:'+c['id'])
            try:
                valid=bool(finding and finding['verdict']=='supported' and finding['criterion_digest']==criterion_stamp(root,doc,c)
                           and selected_support(root,doc,c,finding['facts'],checked)==finding['facts'])
                if valid and review_required(doc['plan'],c):
                    valid=bool(finding['independent'] and finding['provenance'] and artifact_ok(root,finding['provenance']))
            except (ValueError,OSError):valid=False
            rows.append({'id':c['id'],'status':'supported' if valid else 'needs_review',
                         'observation_applicability':fact_applicability(c,observation) if observation else None})
            if not valid:blockers.append('CLAIM:'+c['id'])
    outside=changes(root,doc['baseline']) if doc.get('plan') else []
    owned=set(doc['plan']['scope'])|set(doc['plan']['constraints']) if doc.get('plan') else set()
    return {'outside_scope_change_count':len(set(outside)-owned),'id':ident,'state':'ready' if not blockers else 'blocked' if doc['plan'] else 'draft',
            'scope_readiness':scope_readiness,
            'total':len(rows),'items':rows[offset:offset+limit], 'next_offset':offset+limit if offset+limit<len(rows) else None,
            'blocker_count':len(blockers),'blockers':blockers[blocker_offset:blocker_offset+25],
            'next_blocker_offset':blocker_offset+25 if blocker_offset+25<len(blockers) else None,
            'request_preview':doc['request'][:500],'request_complete':len(doc['request'])<=500,
            'limitation_count':len(doc['limitations']),'eligible':not blockers,'deferred_count':len(deferred),
            'correction':({'id':open_correction(doc)['id'],'affected_count':len(open_correction(doc)['affected']),
                           'details':'detail --section corrections'} if open_correction(doc) else None),
            'boundary':'Local structure/identity checked; semantic coverage and host independence require real review.'}

def _close(root,ident,limitations):
    if not isinstance(limitations,list) or not all(text(x) for x in limitations):fail('LIMITATIONS_INVALID')
    with locked(root,ident):
        doc=load(root,ident)
        if doc['state']=='complete':return doc['receipt']
        status=view(root,ident)
        if not status['eligible']:fail('DELIVERY_BLOCKED')
        if analysis(root,doc)[0]!=doc['analysis_digest']:fail('INPUT_MOVED')
        doc['limitations']=limitations
        doc['receipt']={'completed_at':now(),'git_head_at_close':git(root,'rev-parse','HEAD').decode().strip(),
                        'task':ident,'plan_digest':digest(doc['plan']),'input_digest':doc['analysis_digest'],
                        'retention':{k:task_policy.load(root)[k] for k in ('retention_days','timezone','cleanup','handoff')},
                        'criteria':len(doc['plan']['criteria']),
                        'supported_criteria':len(doc['plan']['criteria'])-len(active_deferrals(root,doc)),
                        'outcome':'scoped_delivery_with_deferrals' if active_deferrals(root,doc) else 'fully_supported',
                        'deferrals':{cid:{**entry,'unresolved_failures':sorted(task_failures.pending(doc,cid))}
                                     for cid,entry in active_deferrals(root,doc).items()},
                        'limitations':limitations,'evidence_retention':'task-local; no permanent replay promised'}
        correction=open_correction(doc)
        if correction:
            doc['receipt']['corrects_receipt']=correction['prior_receipt_digest']
            doc['receipt']['correction_id']=correction['id']
            correction['status']='complete';correction['completed_at']=doc['receipt']['completed_at']
            correction['replacement_receipt_digest']=digest(doc['receipt'])
        doc['state']='complete';save(root,doc)
        return doc['receipt']

def close(root,ident,limitations):
    receipt=_close(root,ident,limitations)
    try:maintain(root,automatic=True)
    except (ValueError,OSError):pass  # cleanup never weakens or blocks an otherwise valid delivery
    return receipt


def cleanup(root,ident,apply=False,timezone_name='UTC',forget=False,handoff=None):
    with locked(root,ident):
        doc=load(root,ident)
        if doc['state']!='complete':fail('CLEANUP_REQUIRES_COMPLETE')
        zone=ZoneInfo(timezone_name)
        days=(datetime.now(zone).date()-instant(doc['receipt']['completed_at']).astimezone(zone).date()).days
        if days<doc['receipt'].get('retention',{}).get('retention_days',7):fail('RETENTION_NOT_ELAPSED')
        for entry in doc['receipt'].get('deferrals',{}).values():
            if not artifact_ok(root,entry['handoff']):fail('DEFERRAL_HANDOFF_UNAVAILABLE')
        if forget and doc['receipt']['limitations']:
            if not handoff:fail('LIMITATIONS_HANDOFF_REQUIRED')
            source=safe(root,handoff)
            if not source.is_file() or source.stat().st_size>MAX_RECORD:fail('LIMITATIONS_HANDOFF_UNAVAILABLE')
            if handoff.startswith('.featrace/'):fail('LIMITATIONS_HANDOFF_MUST_SURVIVE')
            contents=source.read_text()
            if any(item not in contents for item in doc['receipt']['limitations']):fail('LIMITATIONS_HANDOFF_INCOMPLETE')
        folder=safe(root,'.featrace/artifacts/'+ident)
        candidates=[]
        assets={a['path']:a for a in doc.get('attachments',{}).values()}
        if folder.exists():
            for path in folder.iterdir():
                safe(root,path.relative_to(root).as_posix())
                if not path.is_file():fail('CLEANUP_UNKNOWN_ARTIFACT')
                rel=path.relative_to(root).as_posix()
                if rel in assets:
                    if not re.fullmatch(r'[a-f0-9]{32}\.[A-Za-z0-9]{1,10}',path.name) or file_identity(root,rel,True)['sha256']!=assets[rel]['sha256']:fail('CLEANUP_CHANGED_ATTACHMENT')
                    candidates.append(path);continue
                if not re.fullmatch(r'[a-f0-9]{32}\.log',path.name):fail('CLEANUP_UNKNOWN_ARTIFACT')
                with path.open('rb') as stream:header=stream.readline(256)
                if header!=('Featrace task '+ident+' attempt '+path.stem+'\n').encode():fail('CLEANUP_UNKNOWN_ARTIFACT')
                candidates.append(path)
        result={'id':ident,'eligible':True,'apply':apply,'forget':forget,'owned_logs':sum(p.suffix=='.log' for p in candidates),'owned_attachments':sum(p.suffix!='.log' for p in candidates),
                'boundary':'Only runner-owned logs and registered copies; originals and external evidence are not removed.'}
        if apply:
            # Keep a valid completed task if cleanup is interrupted; update receipt BEFORE deleting logs.
            receipt=dict(doc['receipt']);receipt['evidence_retention']='local logs expired by explicit cleanup'
            retained={'task_contract':doc['task_contract'],'id':ident,'state':'complete','receipt':receipt}
            if doc.get('corrections'):
                retained['corrections']=[{k:v for k,v in e.items() if k not in ('prior_claims','prior_checks')} for e in doc['corrections']]
            save(root,{**retained,'attachments':doc.get('attachments',{})})
            for path in candidates:path.unlink()
            if folder.exists():folder.rmdir()
            if forget:task_path(root,ident).unlink()
            else:save(root,retained)
        return result

def locate(root,query,offset=0,limit=20):
    if not text(query) or offset<0 or not 1<=limit<=25:fail('QUERY_INVALID')
    names=git(root,'ls-files','--cached','--others','--exclude-standard','-z')
    matches=sorted({os.fsdecode(n) for n in names.split(b'\0') if n and query.casefold() in os.fsdecode(n).casefold()
                    and not os.fsdecode(n).startswith(('.featrace/','.agent-workflow/'))})
    return {'total':len(matches),'paths':matches[offset:offset+limit],
            'next_offset':offset+limit if offset+limit<len(matches) else None,
            'boundary':'Filename candidates only, not a semantic dependency map. Inspect symbols/resources/callers with project tools; unknown links stay unknown.'}

def task_list(root,offset=0,limit=20):
    if offset<0 or not 1<=limit<=25:fail('PAGE_INVALID')
    folder=safe(root,'.featrace/tasks')
    paths=sorted(folder.glob('*.json')) if folder.exists() else []
    items=[]
    for path in paths[offset:offset+limit]:
        try:
            doc=load(root,path.stem)
            items.append({'id':doc['id'],'recorded_state':doc['state']})
        except (ValueError,OSError,TypeError,KeyError):items.append({'id':path.stem,'recorded_state':'unavailable'})
    return {'total':len(paths),'items':items,'next_offset':offset+limit if offset+limit<len(paths) else None,
            'boundary':'Recorded state only; inspect the selected task for current scope/evidence. No tests executed.'}


def storage(root,offset=0,limit=20):
    """Read-only accounting, including abandoned tasks; never delete to meet a quota."""
    if offset<0 or not 1<=limit<=25:fail('PAGE_INVALID')
    policy=task_policy.load(root);base=safe(root,'.featrace')
    usage={'entries':0,'regular_bytes':0,'links':0,'complete':True}
    if base.exists():
        # Bound traversal as well as output. An incomplete scan is not a total-size claim.
        stack=[base]
        while stack and usage['complete']:
            folder=stack.pop()
            with os.scandir(folder) as entries:
                for entry in entries:
                    usage['entries']+=1
                    if usage['entries']>100000:usage['complete']=False;break
                    if entry.is_symlink():usage['links']+=1
                    elif entry.is_dir(follow_symlinks=False):stack.append(Path(entry.path))
                    elif entry.is_file(follow_symlinks=False):usage['regular_bytes']+=entry.stat(follow_symlinks=False).st_size
    folder=safe(root,'.featrace/tasks');paths=sorted(folder.glob('*.json')) if folder.exists() else []
    items=[];counts={'complete':0,'incomplete':0,'unavailable':0,'stale_incomplete':0,'pending_runtime_failure':0}
    selected=set(paths[offset:offset+limit])
    for path in paths[offset:offset+limit]:
        try:
            doc=load(root,path.stem);completed=doc['state']=='complete'
            counts['complete' if completed else 'incomplete']+=1
            age=max(0,(datetime.now(timezone.utc)-instant(doc.get('updated_at') or doc.get('created_at') or (doc.get('receipt') or {}).get('completed_at'))).days)
            stale=not completed and age>=policy['retention_days']
            pending=(len(task_failures.pending(doc)) if 'facts' in doc else
                     len({fid for e in doc['receipt'].get('deferrals',{}).values() for fid in e['unresolved_failures']}))
            counts['stale_incomplete']+=int(stale);counts['pending_runtime_failure']+=pending
            if path in selected:items.append({'id':path.stem,'state':doc['state'],'record_bytes':path.stat().st_size,
                'inactive_days':age,'stale_incomplete':stale,'pending_runtime_failures':pending})
        except (ValueError,OSError,KeyError,TypeError):
            counts['unavailable']+=1
            if path in selected:items.append({'id':path.stem,'state':'unavailable'})
    return {'usage':usage,'task_count':len(paths),'counts_scope':'selected_page','counts':counts,'items':items,
            'next_offset':offset+limit if offset+limit<len(paths) else None,
            'warnings':(['STALE_INCOMPLETE_TASKS_RETAINED'] if counts['stale_incomplete'] else [])+
                       (['UNRECOGNIZED_OR_UNREADABLE_DATA'] if counts['unavailable'] or usage['links'] else [])+
                       ([] if usage['complete'] else ['USAGE_SCAN_LIMIT_PARTIAL']),
            'boundary':'Read-only. Byte count includes owned and unrecognized local data, not external caches/originals. No unfinished task is expired or deleted.'}


def maintain(root,automatic=False,limit=25):
    policy=task_policy.load(root)
    if not 1<=limit<=100:fail('PAGE_INVALID')
    if automatic and policy['cleanup']=='manual':return {'processed':0,'retained':0,'manual_policy':True}
    with locked(root,'maintenance',control=True):
        folder=safe(root,'.featrace/tasks');paths=sorted(folder.glob('*.json')) if folder.exists() else []
        cursor_path=safe(root,'.featrace/maintenance.json')
        cursor=read_json(cursor_path).get('after','') if cursor_path.exists() else ''
        selected=[p for p in paths if p.stem>cursor][:limit]
        if not selected:selected=paths[:limit]
        done=0;retained=0;retained_items=[]
        for path in selected:
            try:
                doc=load(root,path.stem)
                if doc['state']!='complete':continue
                retention=doc['receipt'].get('retention',policy)
                if retention['cleanup']=='manual':continue
                cleanup(root,path.stem,True,retention['timezone'],retention['cleanup']=='forget',retention['handoff'])
                done+=1
            except (ValueError,OSError,KeyError) as exc:
                code=str(exc) if isinstance(exc,TaskError) else 'CLEANUP_UNAVAILABLE'
                if code!='RETENTION_NOT_ELAPSED':
                    retained+=1
                    if len(retained_items)<25:retained_items.append({'id':path.stem,'reason':code})
        # A single small cursor prevents old active tasks starving later completed tasks.
        cursor_path.parent.mkdir(parents=True,exist_ok=True)
        task_policy.write(cursor_path,canonical({'after':selected[-1].stem if selected else ''}))
        return {'processed':len(selected),'cleaned':done,'retained':retained,'retained_items':retained_items,'next_cursor':selected[-1].stem if selected else None,
                'boundary':'Only complete, expired, runner-owned local data; blocked cleanup retains facts. No scheduler installed.'}


def detail(root,ident,section,criterion=None,offset=0,limit=4000):
    if offset<0 or not 1<=limit<=8000:fail('PAGE_INVALID')
    doc=load(root,ident)
    if section in ('criterion','facts'):
        if not doc.get('plan'):fail('PLAN_REQUIRED')
        c=next((c for c in doc['plan']['criteria'] if c['id']==criterion),None)
        if c is None:fail('CRITERION_UNKNOWN')
        value=c if section=='criterion' else {'observation':doc['facts'].get(doc['observations'].get(criterion)),'assessment':doc['assessments'].get(criterion),
                  'observation_applicability':fact_applicability(c,doc['facts'][doc['observations'][criterion]]) if criterion in doc['observations'] else None,
                  'runtime_failures':task_failures.pending(doc,criterion),
                  'failure_actions':{fid:actions for fid,actions in doc.get('failure_actions',{}).items() if fid in task_failures.failure_facts(doc,criterion)},
                  'claim_deferrals':doc.get('claim_deferrals',{}).get(criterion,[]),
                  'facts':{fid:f for fid,f in doc['facts'].items() if f.get('criterion')==criterion or (f['kind']=='command' and f['check'] in [x['id'] for x in doc['plan']['checks'] if criterion in x['covers']])}}
    elif section=='failure-handoff':
        if not doc.get('plan') or criterion not in {c['id'] for c in doc['plan']['criteria']}:fail('CRITERION_UNKNOWN')
        value=failure_handoff(doc,criterion)
    elif section=='fact':
        value=doc.get('facts',{}).get(criterion)
        if value is None:fail('FACT_REFERENCE_MISSING')
    elif section in ('request','plan','receipt','limitations','corrections','authorizations','attachments'):value=doc.get(section)
    else:fail('DETAIL_SECTION_INVALID')
    body=canonical(value).decode() if section=='failure-handoff' else json.dumps(value,ensure_ascii=False,sort_keys=True)
    # UTF-8 bytes are bounded even for four-byte codepoints.
    chunk=body[offset:offset+min(limit,2000)];end=offset+len(chunk)
    return {'id':ident,'section':section,'total_characters':len(body),'offset':offset,'text':chunk,
            'next_offset':end if end<len(body) else None,'complete':offset==0 and end==len(body)}


def review_input(root,ident,criterion):
    doc=load(root,ident)
    c=next((x for x in doc['plan']['criteria'] if x['id']==criterion),None)
    if c is None:fail('CRITERION_UNKNOWN')
    ready(root,doc,criterion=c)
    obs=doc['facts'].get(doc['observations'].get(criterion))
    return {'task':ident,'criterion':criterion,'criterion_digest':criterion_stamp(root,doc,c),'facts':facts(root,doc,c),
            'selected_facts':doc['assessments'].get(criterion,{}).get('facts',[]),'proof':c['proof'],
            'expected_preview':c['expected'][:500],'expected_complete':len(c['expected'])<=500,'kind':c['kind'],
            'input_count':len(c['inputs']),'inputs_preview':[p[:160] for p in c['inputs'][:10]],'inputs_complete':len(c['inputs'])<=10 and all(len(p)<=160 for p in c['inputs']), 'observation_kind':obs.get('kind') if obs else None,
            'validity_mode':c.get('validity',{}).get('mode','undeclared'),
            'observation_applicability':fact_applicability(c,obs) if obs else None,
            'runtime_failures':[{'id':fid,'observed_at':f['observed_at'],'details':'detail --section facts --criterion '+criterion}
                                for fid,f in list(task_failures.pending(doc,criterion).items())[:10]],
            'runtime_failure_count':len(task_failures.pending(doc,criterion)),
            'review':{'independent':review_required(doc['plan'],c),'reason_preview':doc['plan']['review']['reason'][:500],'reason_complete':len(doc['plan']['review']['reason'])<=500},'details':'detail --section criterion|facts --criterion '+criterion,
            'boundary':'Review actual scoped code/claims/assertions. Host supplies genuine provenance; this is not an independent review.'}


def code_query(root,query,offset=0,limit=20):
    if not text(query) or offset<0 or not 1<=limit<=25:fail('QUERY_INVALID')
    # git grep is literal, scoped to the CURRENT tracked working files, and never scans old feature records.
    process=subprocess.Popen(['git','-C',str(root),'grep','--no-ext-grep','-n','-I','-F','-z','-e',query,'--',
                              ':(exclude).featrace/**',':(exclude).agent-workflow/**'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    items=[];count=0;truncated=False
    try:
        while True:
            raw=process.stdout.readline(8192)
            if not raw:break
            more=not raw.endswith(b'\n')
            if more:
                while True:
                    tail=process.stdout.readline(8192)
                    if not tail or tail.endswith(b'\n'):break
            parts=raw.split(b'\0',2)
            if len(parts)!=3:continue
            if count>=offset and len(items)<limit:
                items.append({'path':os.fsdecode(parts[0]),'line':int(parts[1]),'preview':parts[2].decode('utf-8','replace').rstrip()[:300]})
            count+=1
            if count>=offset+limit+1:truncated=True;break
    finally:
        process.stdout.close()
        if truncated:process.terminate()
        code=process.wait()
    if not truncated and code not in (0,1):fail('CODE_QUERY_UNAVAILABLE')
    return {'items':items,'next_offset':offset+limit if truncated else None,'exhausted':not truncated,
            'boundary':'Literal current tracked-code matches, not a complete semantic graph; inspect callers/resources/dynamic links as needed.'}


def main():
    parser=Parser(description=__doc__)
    parser.add_argument('action',choices=['begin','plan','run','observe','assess','status','close','correct','prune','cleanup','locate','list','policy','maintain','detail','review-input','code','attach','storage','failure','defer','reopen-claim','authorize'])
    parser.add_argument('root');parser.add_argument('id',nargs='?')
    parser.add_argument('--json');parser.add_argument('--request');parser.add_argument('--check');parser.add_argument('--criterion')
    parser.add_argument('--kind');parser.add_argument('--observed-at');parser.add_argument('--actual')
    parser.add_argument('--investigate',action='store_true');parser.add_argument('--target');parser.add_argument('--section');parser.add_argument('--file')
    parser.add_argument('--status',choices=['passed','failed','unavailable'],default='passed')
    parser.add_argument('--evidence',action='append',default=[]);parser.add_argument('--verdict');parser.add_argument('--reason')
    parser.add_argument('--independent',action='store_true');parser.add_argument('--provenance')
    parser.add_argument('--limitation',action='append',default=[]);parser.add_argument('--offset',type=int,default=0);parser.add_argument('--limit',type=int,default=20)
    parser.add_argument('--blocker-offset',type=int,default=0);parser.add_argument('--apply',action='store_true');parser.add_argument('--timezone',default='UTC')
    parser.add_argument('--forget',action='store_true');parser.add_argument('--handoff')
    parser.add_argument('--fact',action='append',default=[]);parser.add_argument('--producer')
    parser.add_argument('--affected',action='append',default=[]);parser.add_argument('--authority')
    parser.add_argument('--failure');parser.add_argument('--disposition',choices=['resolve','clarify','reopen'])
    parser.add_argument('--conditions-json');parser.add_argument('--decision-at')
    parser.add_argument('--exclude-from-delivery',action='store_true')
    parser.add_argument('--mode',choices=['once','task']);parser.add_argument('--expires-at')
    parser.add_argument('--role',choices=['input','evidence'],default='evidence')
    a=parser.parse_args();root=project(a.root)
    if a.action=='policy':out=task_policy.prepare(root,read_json(Path(a.json)),git)
    elif a.action=='storage':out=storage(root,a.offset,a.limit)
    elif a.action=='maintain':out=maintain(root,limit=a.limit)
    elif a.action=='detail':out=detail(root,a.id,a.section,a.criterion,a.offset,min(a.limit,8000))
    elif a.action=='review-input':out=review_input(root,a.id,a.criterion)
    elif a.action=='code':out=code_query(root,a.id,a.offset,a.limit)
    elif a.action=='begin':out=begin(root,a.id,a.request)
    elif a.action=='plan':out=set_plan(root,a.id,read_json(Path(a.json)))
    elif a.action=='authorize':out=authorize(root,a.id,a.check,a.mode,a.authority,a.decision_at,a.expires_at,a.reason)
    elif a.action=='run':out=run_check(root,a.id,a.check,a.investigate)
    elif a.action=='attach':out=attach(root,a.id,a.file,a.role)
    elif a.action=='observe':out=observe(root,a.id,a.criterion,a.kind,a.observed_at,a.actual,a.evidence,a.status,a.target,a.producer,read_json(Path(a.conditions_json)) if a.conditions_json else None)
    elif a.action=='failure':out=failure_action(root,a.id,a.failure,a.disposition,a.reason,a.fact,read_json(Path(a.conditions_json)) if a.conditions_json else None)
    elif a.action in ('defer','reopen-claim'):out=defer_claim(root,a.id,a.criterion,a.reason,a.authority,a.decision_at,a.handoff,a.action=='reopen-claim',a.exclude_from_delivery)
    elif a.action=='assess':out=assess(root,a.id,a.criterion,a.verdict,a.reason,a.independent,a.provenance,a.fact)
    elif a.action=='correct':out=correct(root,a.id,a.affected,a.reason,a.authority)
    elif a.action=='prune':out=prune(root,a.id,a.apply)
    elif a.action=='status':out=view(root,a.id,a.offset,a.limit,a.blocker_offset)
    elif a.action=='close':
        receipt=close(root,a.id,a.limitation);out={'id':a.id,'state':'complete','completed_at':receipt['completed_at'],'limitation_count':len(receipt['limitations']),'outcome':receipt['outcome'],'deferred_count':len(receipt.get('deferrals',{})),'details':'detail --section receipt'}
    elif a.action=='cleanup':out=cleanup(root,a.id,a.apply,a.timezone,a.forget,a.handoff)
    elif a.action=='list':out=task_list(root,a.offset,a.limit)
    else:out=locate(root,a.id,a.offset,a.limit)
    output=json.dumps(out,ensure_ascii=False,indent=2)
    if len(output.encode())>MAX_OUTPUT:fail('OUTPUT_LIMIT_USE_PAGED_DETAIL')
    print(output)
    return 2 if (a.action=='status' and out.get('state') in ('blocked','draft')) or out.get('status') in ('failed','unavailable') else 0

if __name__=='__main__':
    try:sys.exit(main())
    except (TaskError,task_policy.PolicyError) as exc:
        print(json.dumps({'state':'unavailable','reason':str(exc)}));sys.exit(2)
    except (ValueError,OSError,KeyError,TypeError,AttributeError):
        print(json.dumps({'state':'unavailable','reason':'TASK_OPERATION_REFUSED; inspect selected inputs privately'}));sys.exit(2)
