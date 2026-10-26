"""Selected immutable task inputs; no control-file or path-spelling exception."""
import hashlib
from pathlib import Path
import re
import task_inputs


def validate(doc,fail):
    for key,a in doc.get('attachments',{}).items():
        if (not isinstance(a,dict) or set(a)!={'path','sha256','bytes','captured_at','role','origin'}
                or not re.fullmatch('[a-f0-9]{32}',key) or not re.fullmatch('[a-f0-9]{64}',a.get('sha256',''))
                or type(a.get('bytes')) is not int or not 0<=a['bytes']<=16*1024*1024
                or not isinstance(a.get('captured_at'),str) or a.get('role') not in ('input','evidence')
                or not isinstance(a.get('origin'),str) or not a['origin']
                or not re.fullmatch(r'\.featrace/artifacts/'+re.escape(doc['id'])+'/'+key+r'\.[A-Za-z0-9]{1,10}',a.get('path',''))):fail('ASSET_INVALID')


def source(root,ident,name,role,fail):
    if role not in ('input','evidence') or not isinstance(name,str) or not name:fail('ASSET_SOURCE_REQUIRED')
    p=Path(name)
    if not p.is_absolute():
        if '..' in p.parts or '.git' in p.parts:fail('UNSAFE_PATH')
        p=root/p
    if p.is_symlink():fail('SYMLINK_INPUT')
    resolved=p.resolve()
    try:rel=resolved.relative_to(root).as_posix()
    except ValueError:rel=None
    if rel and (rel=='.git' or rel.startswith('.git/')):fail('ASSET_CONTROL_SOURCE')
    if role=='input' and rel and task_inputs.control(root,resolved):
        if not rel.startswith('.featrace/scratch/'+ident+'/'):fail('ASSET_CONTROL_SOURCE')
    if not resolved.is_file():fail('ATTACHMENT_SOURCE_REQUIRED')
    return resolved


def refs(root,doc,ids,fail):
    if (not isinstance(ids,list) or len(ids)>32 or any(not isinstance(x,str) for x in ids)
            or len(set(ids))!=len(ids)):fail('ASSET_SELECTION_INVALID')
    result={}
    for key in ids:
        a=doc.get('attachments',{}).get(key)
        if not a or a.get('role')!='input':fail('INPUT_ASSET_REQUIRED')
        p=root/a['path']
        if p.is_symlink() or p.resolve()!=p or not p.is_file() or p.stat().st_size!=a['bytes']:fail('INPUT_ASSET_CHANGED')
        if hashlib.sha256(p.read_bytes()).hexdigest()!=a['sha256']:fail('INPUT_ASSET_CHANGED')
        result[key]={'path':a['path'],'sha256':a['sha256'],'bytes':a['bytes']}
    return result


def script_argument(argv):
    exe=Path(argv[0]).name
    if not (exe.startswith('python') or exe in ('sh','bash','zsh')):return None
    i=1
    while i<len(argv):
        arg=argv[i]
        if arg in ('-c','-m','--help','--version'):return None  # Inline/module forms need declared imports; not a dynamic parser.
        if arg=='--':return argv[i+1] if i+1<len(argv) else None
        if (exe.startswith('python') and arg in ('-W','-X','--check-hash-based-pycs')) or (not exe.startswith('python') and arg in ('-o','-O','--rcfile','--init-file')):i+=2;continue
        if arg.startswith('-'):i+=1;continue
        return arg
    return None


def command(root,doc,check,fail):
    selected=refs(root,doc,check.get('input_assets',[]),fail)
    owned={(root/a['path']).resolve() for a in selected.values()}
    for arg in check['argv']:
        p=Path(arg);p=p if p.is_absolute() else root/p
        if p.exists() and task_inputs.control(root,p.resolve()) and p.resolve() not in owned:fail('UNDECLARED_CONTROL_COMMAND_INPUT')
    # Exact ordinary script forms only; not a shell parser or dynamic read-set proof.
    script=script_argument(check['argv'])
    if script is not None:
        p=Path(script);p=(p if p.is_absolute() else root/p).resolve()
        if p in owned:return
        try:rel=p.relative_to(root).as_posix()
        except ValueError:rel=None
        if rel and task_inputs.covers(rel,check['inputs'],check.get('input_sets',[])):return
        for ext in check.get('external_inputs',[]):
            base=Path(ext['path']).resolve()
            if p==base or (ext['kind']=='tree' and base in p.parents):return
        fail('COMMAND_SCRIPT_INPUT_REQUIRED')
