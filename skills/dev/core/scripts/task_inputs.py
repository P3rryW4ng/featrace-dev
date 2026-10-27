"""Transient execution fingerprints; never store a repository manifest."""
import hashlib
import json
import os
import re
from pathlib import Path
import stat
import subprocess

MAX_FILES = 250000
MAX_BYTES = 32 * 1024**3
DEFAULT_ENV = ('PATH','JAVA_HOME','ANDROID_HOME','ANDROID_SDK_ROOT','GRADLE_USER_HOME',
               'LANG','LC_ALL','TZ','PYTHONPATH','NODE_OPTIONS','CI')
CONTROL = ('.featrace/', '.agent-workflow/')


def reject(code):
    raise ValueError(code)


def control(root,path):
    try:rel=(path.resolve() if path.is_symlink() else path).relative_to(Path(root)).as_posix()
    except (ValueError,OSError,RuntimeError):return False
    return rel=='.featrace-policy.json' or rel in ('.featrace','.agent-workflow') or rel.startswith(CONTROL)


def relative(name):
    p = Path(name)
    if not isinstance(name,str) or not name or p.is_absolute() or p.as_posix()!=name or any(x in ('.git','..') for x in p.parts):
        reject('INPUT_PATH_INVALID')
    return p


def git_paths(root):
    r = subprocess.run(['git','--literal-pathspecs','-C',str(root),'ls-files','--cached','--others','--exclude-standard','-z'],capture_output=True)
    if r.returncode:reject('INPUT_GIT_UNAVAILABLE')
    return sorted({os.fsdecode(p) for p in r.stdout.split(b'\0') if p and not os.fsdecode(p).startswith(CONTROL) and os.fsdecode(p)!='.featrace-policy.json'})


def within(name, prefix):
    return prefix=='.' or name==prefix or name.startswith(prefix.rstrip('/')+'/')


def validate_sets(sets, external=False):
    if not isinstance(sets,list) or len(sets)>64:reject('INPUT_SETS_INVALID')
    for item in sets:
        if not isinstance(item,dict) or set(item)!={'kind','path'} or item['kind'] not in (('file','tree') if external else ('file','tree','git_tree')):
            reject('INPUT_SET_INVALID')
        name=item['path']
        if not isinstance(name,str):reject('INPUT_PATH_INVALID')
        if external:
            if not Path(name).is_absolute():reject('EXTERNAL_ABSOLUTE_REQUIRED')
        else:
            relative(name)
            if name.startswith(CONTROL) or name in ('.featrace','.agent-workflow'):reject('GENERATED_SCOPE_INPUT')


def covers(name, paths, sets):
    return name in paths or any((item['kind'] in ('tree','git_tree') and within(name,item['path'])) or item['path']==name for item in sets)


def execution_environment(check):
    """Capture once in memory. Never serialize inherited values into task records."""
    config=check.get('execution_env',{'mode':'inherit'})
    if not isinstance(config,dict):reject('EXECUTION_ENV_INVALID')
    mode=config.get('mode')
    if mode=='inherit':
        if set(config)!={'mode'}:reject('EXECUTION_ENV_INVALID')
        return {'mode':mode,'env':dict(os.environ)}
    if mode!='controlled' or set(config)!={'mode','inherit_keys','search_path'}:reject('EXECUTION_ENV_INVALID')
    keys=config['inherit_keys'];paths=config['search_path']
    if (not isinstance(keys,list) or len(keys)>64
            or any(not isinstance(k,str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',k) for k in keys)
            or len(set(keys))!=len(keys) or 'PATH' in keys):reject('EXECUTION_ENV_KEYS_INVALID')
    if (not isinstance(paths,list) or not 1<=len(paths)<=32
            or any(not isinstance(p,str) or not p or not Path(p).is_absolute()
                   or '..' in Path(p).parts or os.pathsep in p or '\x00' in p for p in paths)
            or len(set(paths))!=len(paths)):reject('EXECUTION_SEARCH_PATH_INVALID')
    if check.get('env_keys'):reject('EXECUTION_ENV_KEYS_CONFLICT')
    env={k:os.environ[k] for k in keys if k in os.environ}
    env['PATH']=os.pathsep.join(paths)
    return {'mode':mode,'env':env}


def signature(root, paths, sets, external, env_keys, diagnostics=None, execution_env=None):
    """Hash selected current bytes and membership, with bounded transient enumeration."""
    validate_sets(sets);validate_sets(external,True)
    if not isinstance(env_keys,list) or len(env_keys)>64 or any(not isinstance(k,str) or not k for k in env_keys):reject('ENV_KEYS_INVALID')
    root=Path(root).resolve(); names=git_paths(root) if any(x['kind']=='git_tree' for x in sets) else []
    tracked=set()
    if names:
        result=subprocess.run(['git','-C',str(root),'ls-files','--cached','-z'],capture_output=True)
        if result.returncode:reject('INPUT_GIT_UNAVAILABLE')
        tracked={os.fsdecode(n) for n in result.stdout.split(b'\0') if n}
    aggregate=hashlib.sha256(); count=0; total=0; visited=set()

    def emit(value):
        aggregate.update(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()+b'\n')

    def include(path, label, ancestors=(), external_root=None):
        nonlocal count,total
        key=(str(path),label)
        if key in visited:return
        visited.add(key);count+=1
        if count>MAX_FILES:reject('EXECUTION_INPUT_COUNT_LIMIT')
        # Refuse special nodes and ancestor links; explicit external roots may resolve their root only.
        base=root if not label.startswith('external:') else Path(path.anchor)
        for part in path.relative_to(base).parts[:-1]:
            base/=part
            if base.is_symlink():reject('EXECUTION_ANCESTOR_LINK')
        if control(root,path):reject('GENERATED_SCOPE_INPUT')
        try:before=path.lstat()
        except FileNotFoundError:
            emit([label,'missing']);return
        if stat.S_ISLNK(before.st_mode):
            target=os.readlink(path)
            try:resolved=path.resolve()
            except (OSError,RuntimeError):reject('EXECUTION_LINK_CYCLE')
            if external_root is not None:
                try:rel=resolved.relative_to(external_root).as_posix()
                except ValueError:reject('EXTERNAL_LINK_OUTSIDE')
                if not resolved.exists():reject('EXECUTION_LINK_DANGLING')
                if str(resolved) in ancestors:reject('EXECUTION_LINK_CYCLE')
                emit([label,'external_link',target,rel])
                include(resolved,label+'->'+rel,ancestors,external_root)
                if path.lstat()!=before:reject('EXECUTION_INPUT_MOVED')
                return
            if Path(target).is_absolute():reject('EXECUTION_LINK_OUTSIDE')
            resolved=path.resolve()
            try:rel=resolved.relative_to(root).as_posix()
            except ValueError:reject('EXECUTION_LINK_OUTSIDE')
            if not resolved.exists():reject('EXECUTION_LINK_DANGLING')
            if str(resolved) in ancestors:reject('EXECUTION_LINK_CYCLE')
            members=sorted(n for n in tracked if within(n,rel))
            if not members:reject('EXECUTION_LINK_UNMANAGED')
            emit([label,'managed_link',target])
            for n in members:include(root/n,label+'->'+n,ancestors+(str(resolved),))
            if path.lstat()!=before:reject('EXECUTION_INPUT_MOVED')
            return
        if stat.S_ISDIR(before.st_mode):
            emit([label,'directory'])
            for child in sorted(path.iterdir()):
                if child.name=='.git' or control(root,child):continue
                include(child,label+'/'+child.name,ancestors+(str(path),),external_root)
        elif stat.S_ISREG(before.st_mode):
            total+=before.st_size
            if total>MAX_BYTES:reject('EXECUTION_INPUT_BYTES_LIMIT')
            h=hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
            emit([label,'file',h.hexdigest(),bool(before.st_mode&0o111)])
        else:reject('EXECUTION_SPECIAL_INPUT')
        after=path.lstat()
        if (before.st_ino,before.st_size,before.st_mtime_ns,before.st_mode)!=(after.st_ino,after.st_size,after.st_mtime_ns,after.st_mode):reject('EXECUTION_INPUT_MOVED')

    for name in sorted(set(paths)):
        if not (root/relative(name)).exists():reject('EXECUTION_INPUT_MISSING')
        include(root/relative(name),'file:'+name)
    for item in sets:
        name=item['path'];path=root/relative(name)
        if not path.exists():reject('EXECUTION_SET_MISSING')
        if item['kind']=='git_tree':
            members=[n for n in names if within(n,name)]
            if not members:reject('EXECUTION_SET_EMPTY')
            emit(['git_tree',name,len(members)])
            for n in members:include(root/n,'git:'+n)
        else:
            if item['kind']=='file' and not path.is_file():reject('REGULAR_FILE_REQUIRED')
            include(path,item['kind']+':'+name)
    for item in external:
        path=Path(item['path']);resolved=path.resolve()
        if not resolved.exists():reject('EXTERNAL_INPUT_MISSING')
        if item['kind']=='file' and not resolved.is_file():reject('REGULAR_FILE_REQUIRED')
        emit(['external_resolution',str(path),str(resolved)])
        include(resolved,'external:'+str(resolved),external_root=resolved if resolved.is_dir() else resolved.parent)
    if names and git_paths(root)!=names:reject('EXECUTION_MEMBERSHIP_MOVED')
    # Persist the digest only: environment values may contain credentials.
    snapshot=execution_env or {'mode':'inherit','env':dict(os.environ)}
    keys=sorted(snapshot['env']) if snapshot['mode']=='controlled' else sorted(set(DEFAULT_ENV)|set(env_keys))
    environment=['environment',snapshot['mode'],[(k,snapshot['env'].get(k)) for k in keys]]
    if diagnostics is not None:
        diagnostics.update({'selected_inputs':aggregate.hexdigest(),
                            'environment':hashlib.sha256(json.dumps(environment,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()})
    emit(environment)
    return {'sha256':aggregate.hexdigest(),'entries':count,'bytes':total}
