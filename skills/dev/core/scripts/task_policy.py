"""One scoped project policy; no feature contracts, migrations or history ledger."""
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import tempfile
from zoneinfo import ZoneInfo

NAME='.featrace-policy.json'
START='# Featrace local working data (managed)'
END='# End Featrace local working data'
BLOCK=START+'\n/.featrace/\n'+END+'\n'
MAX=256*1024


class PolicyError(ValueError):
    """A known, position-free policy diagnostic safe for the CLI to return."""


def fail(code):raise PolicyError(code)


def path(root,name):
    p=Path(name)
    if not isinstance(name,str) or not name or p.is_absolute() or p.as_posix()!=name or any(x in ('..','.git') for x in p.parts):fail('POLICY_PATH_INVALID')
    out=Path(root)
    for part in p.parts:
        out/=part
        if out.is_symlink():fail('POLICY_LINK_REFUSED')
    return out


def read(p):
    if p.is_symlink() or p.stat().st_size>MAX:fail('POLICY_UNAVAILABLE')
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:fail('DUPLICATE_POLICY_KEY')
            out[k]=v
        return out
    return json.loads(p.read_text(),object_pairs_hook=pairs)


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def validate(root,p):
    if not isinstance(p,dict) or set(p)!={'policy_contract','authority','timezone','retention_days','cleanup','handoff','rules'} or p['policy_contract']!=1:fail('POLICY_FIELDS_INVALID')
    if not isinstance(p['authority'],str) or not p['authority'].strip():fail('POLICY_AUTHORITY_REQUIRED')
    ZoneInfo(p['timezone'])
    if type(p['retention_days']) is not int or not 1<=p['retention_days']<=90:fail('RETENTION_POLICY_INVALID')
    if p['cleanup'] not in ('manual','compact','forget'):fail('CLEANUP_POLICY_INVALID')
    if p['handoff'] is not None:
        path(root,p['handoff'])
        if p['handoff'].startswith('.featrace/'):fail('LIMITATIONS_HANDOFF_MUST_SURVIVE')
    if not isinstance(p['rules'],list) or len(p['rules'])>64:fail('POLICY_RULES_INVALID')
    for r in p['rules']:
        if (not isinstance(r,dict) or set(r)!={'source','sha256','paths','operations','environment','decision','permission','authority'}
            or not all(isinstance(r[k],str) and r[k].strip() for k in ('source','decision','authority','sha256'))
            or not isinstance(r['paths'],list) or not r['paths'] or not all(isinstance(x,str) and x for x in r['paths'])
            or not isinstance(r['operations'],list) or not r['operations'] or set(r['operations'])-{'build','test','device','commit','review','configure'}
            or r['environment'] not in ('any','test','local','production') or r['permission'] not in ('allowed','denied','ask','not_applicable')):fail('POLICY_RULE_INVALID')
        path(root,r['source'])
    return p


def load(root):
    p=path(root,NAME)
    if not p.exists():fail('PROJECT_POLICY_REQUIRED')
    return validate(root,read(p))


def write(p,data):
    if len(data)>MAX:fail('POLICY_SIZE_LIMIT')
    fd,name=tempfile.mkstemp(prefix='.featrace-policy-',dir=p.parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(name,p)
    finally:
        if os.path.exists(name):os.unlink(name)


def prepare(root,config,git):
    """Explicit user-scoped setup/update, not an automatic authorization grant."""
    p=json.loads(json.dumps(config))
    for r in p.get('rules',[]):
        source=path(root,r['source'])
        if not source.is_file() or source.stat().st_size>MAX:fail('POLICY_SOURCE_UNAVAILABLE')
        r['sha256']=sha(source)
    validate(root,p)
    if git(root,'ls-files','-z','--','.featrace').strip(b'\0'):fail('LOCAL_TASK_DATA_TRACKED')
    dest=path(root,NAME);ignore=path(root,'.gitignore')
    if dest.exists():validate(root,read(dest))
    original=ignore.read_text() if ignore.exists() else ''
    if START in original or END in original:
        if original.count(BLOCK)!=1 or original.count(START)!=1 or original.count(END)!=1:fail('CUSTOM_IGNORE_BLOCK_CONFLICT')
        changed=original
    else:changed=original+('' if not original or original.endswith('\n') else '\n')+BLOCK
    # Test effective ignore rules including later negations BEFORE publishing policy.
    previous=ignore.read_bytes() if ignore.exists() else None
    try:
        write(ignore,changed.encode())
        import subprocess
        for name in ('.featrace/tasks/probe.json','.featrace/artifacts/probe.log','.featrace/locks/0','.featrace/maintenance.json','.featrace/scratch/probe'):
            probe=subprocess.run(['git','-C',str(root),'check-ignore','--no-index','-q',name])
            if probe.returncode:fail('LOCAL_IGNORE_CONFLICT')
        write(dest,(json.dumps(p,ensure_ascii=False,indent=2)+'\n').encode())
    except BaseException:
        if previous is None:ignore.unlink(missing_ok=True)
        else:write(ignore,previous)
        raise
    return {'policy_contract':1,'local_data_ignored':True,'cleanup':p['cleanup'],'retention_days':p['retention_days'],
            'boundary':'Actual scope/authority supplied by caller; no host permissions or hooks changed.'}


def execution_names(root,sets):
    """Transient actual repository input members for permissions; no manifest or byte reads."""
    import task_inputs
    task_inputs.validate_sets(sets)
    root=Path(root).resolve();seen=set();names=set()
    git_names=task_inputs.git_paths(root) if any(x['kind']=='git_tree' for x in sets) else []
    def include(candidate):
        try:rel=candidate.relative_to(root).as_posix()
        except ValueError:return  # The execution fingerprint independently refuses outside repository links.
        if rel in seen:return
        seen.add(rel)
        if len(seen)>task_inputs.MAX_FILES:fail('EXECUTION_INPUT_COUNT_LIMIT')
        names.add(rel)
        if candidate.is_symlink():
            try:target=candidate.resolve()
            except (OSError,RuntimeError):fail('EXECUTION_LINK_CYCLE')
            try:target.relative_to(root)
            except ValueError:return
            include(target)
        elif candidate.is_dir():
            for child in candidate.iterdir():
                if child.name=='.git' or task_inputs.control(root,child):continue
                include(child)
    for item in sets:
        if item['kind']=='git_tree':
            for name in git_names:
                if task_inputs.within(name,item['path']):
                    candidate=root/name
                    if candidate.is_symlink():include(candidate)
                    else:
                        names.add(name)
                        if len(names)>task_inputs.MAX_FILES:fail('EXECUTION_INPUT_COUNT_LIMIT')
        else:include(root/item['path'])
    return names


def effective(root,scope,operation='all',environment='local',enforce=False,input_sets=()):
    p=load(root);rules=[]
    actual_scope=set(scope)
    selected_sets=list(input_sets)+[{'kind':'tree','path':name} for name in actual_scope if (Path(root)/name).is_dir()]
    if selected_sets:actual_scope.update(execution_names(root,selected_sets))
    for r in p['rules']:
        if operation!='all' and operation not in r['operations']:continue
        if environment!='any' and r['environment'] not in ('any',environment):continue
        if not any(fnmatch.fnmatchcase(name,pattern) for name in actual_scope for pattern in r['paths']):continue
        if sha(path(root,r['source']))!=r['sha256']:fail('APPLICABLE_RULE_CHANGED')
        if enforce and r['permission'] in ('denied','ask'):fail('OPERATION_POLICY_'+r['permission'].upper())
        rules.append(r)
    return rules


def check_local(root,git):
    if git(root,'ls-files','-z','--','.featrace').strip(b'\0'):fail('LOCAL_TASK_DATA_TRACKED')
    import subprocess
    for name in ('.featrace/tasks/probe.json','.featrace/artifacts/probe.log','.featrace/locks/0','.featrace/maintenance.json','.featrace/scratch/probe'):
        r=subprocess.run(['git','-C',str(root),'check-ignore','--no-index','-q',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if r.returncode:fail('LOCAL_IGNORE_CONFLICT')
