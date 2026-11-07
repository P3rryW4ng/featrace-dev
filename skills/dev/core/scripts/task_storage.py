"""Bounded task representation; no authority, execution or evidence decisions."""
from collections import Counter
import hashlib
import json
import os
import re
import tempfile

VERSION = 1
MAX_EXPANDED = 2 * 1024 * 1024
MAX_BLOCKS = 128
BLOCK_MIN = 1024
KEY = "$block"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def slot(path):
    return ((len(path)==3 and path[0]=='facts' and path[2] in
             ('source_inputs','execution_definition','producer','identity_components'))
            or (len(path)==3 and path[0]=='corrections' and path[2]=='prior_receipt')
            or (len(path)==5 and path[0]=='corrections' and path[2]=='prior_claims' and path[4]=='criterion')
            or (len(path)==4 and path[0]=='walkthroughs' and path[2]=='origin' and path[3]=='source_inputs'))


def transform(value, visit, path=()):
    if isinstance(value,dict):
        return {k:visit(v,path+(k,)) for k,v in value.items()}
    if isinstance(value,list):
        return [visit(v,path+(i,)) for i,v in enumerate(value)]
    return value


def encode(doc, fail):
    if len(canonical(doc))>MAX_EXPANDED:fail('TASK_SIZE_LIMIT_EXPANDED')
    counts=Counter()
    def scan(value,path):
        if slot(path) and isinstance(value,dict) and len(canonical(value))>=BLOCK_MIN:
            counts[digest(value)]+=1
            return
        transform(value,scan,path)
    scan(doc,())
    chosen=set(sorted(k for k,n in counts.items() if n>1)[:MAX_BLOCKS])
    blocks={}
    def pack(value,path):
        if slot(path) and isinstance(value,dict):
            if set(value)=={KEY} and isinstance(value[KEY],str):fail('TASK_STORAGE_INVALID')
            key=digest(value)
            if key in chosen:
                blocks[key]=value
                return {KEY:key}
        return transform(value,pack,path)
    packed=pack(doc,())
    envelope={'task_contract':doc['task_contract'],'storage_version':VERSION,'task':packed,'blocks':blocks}
    return canonical({**envelope,'storage_checksum':digest(envelope)})+b'\n'


def decode(envelope,fail):
    required={'task_contract','storage_version','task','blocks','storage_checksum'}
    if set(envelope)!=required or envelope['storage_version']!=VERSION:fail('TASK_CHANGED')
    if envelope['storage_checksum']!=digest({k:v for k,v in envelope.items() if k!='storage_checksum'}):fail('TASK_CHANGED')
    blocks=envelope['blocks'];packed=envelope['task']
    if not isinstance(blocks,dict) or len(blocks)>MAX_BLOCKS or not isinstance(packed,dict):fail('TASK_STORAGE_INVALID')
    sizes={}
    def no_refs(value,path):
        if isinstance(value,dict) and set(value)=={KEY} and isinstance(value[KEY],str):fail('TASK_STORAGE_INVALID')
        transform(value,no_refs,path)
    for key,value in blocks.items():
        if not re.fullmatch('[a-f0-9]{64}',key) or not isinstance(value,dict) or digest(value)!=key:fail('TASK_STORAGE_INVALID')
        no_refs(value,())
        sizes[key]=len(canonical(value))
    used=Counter();size=len(canonical(packed))
    def unpack(value,path):
        nonlocal size
        if isinstance(value,dict) and set(value)=={KEY} and isinstance(value[KEY],str):
            key=value[KEY]
            if not slot(path) or not isinstance(key,str) or key not in blocks:fail('TASK_STORAGE_INVALID')
            used[key]+=1
            size+=sizes[key]-len(canonical(value))
            if size>MAX_EXPANDED:fail('TASK_SIZE_LIMIT_EXPANDED')
            return blocks[key]
        return transform(value,unpack,path)
    doc=unpack(packed,())
    if set(used)!=set(blocks) or any(n<2 for n in used.values()) or len(canonical(doc))>MAX_EXPANDED:fail('TASK_STORAGE_INVALID')
    # Decode independently mutable copies; pooled identities must never alias in memory.
    return json.loads(canonical(doc))


def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.write-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)
