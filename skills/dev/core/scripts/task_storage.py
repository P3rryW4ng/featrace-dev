"""Bounded contract-9 index and immutable task-local metadata objects.

No authority/evidence decisions. Metadata is distinct from user evidence assets.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

VERSION = 2
MAX_EXPANDED = 2 * 1024 * 1024
MAX_OBJECTS = 512
MAX_OBJECT = 256 * 1024
MAX_STORED = 4 * 1024 * 1024
OBJECT_MIN = 1024
KEY = '$object'
HASH = re.compile(r'[a-f0-9]{64}\Z')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def prepare(doc, fail):
    if len(canonical(doc)) > MAX_EXPANDED: fail('TASK_SIZE_LIMIT_EXPANDED')
    objects = {}
    def pack(value, depth=0):
        if isinstance(value, dict):
            if set(value) == {KEY}: fail('TASK_STORAGE_RESERVED_KEY')
            packed = {k: pack(v, depth+1) for k,v in value.items()}
        elif isinstance(value, list): packed = [pack(v, depth+1) for v in value]
        else: return value
        data = canonical(packed)
        if depth and len(data) >= OBJECT_MIN:
            if len(data) > MAX_OBJECT: fail('TASK_SIZE_LIMIT_OBJECT')
            key = hashlib.sha256(data).hexdigest()
            objects[key] = data
            return {KEY:key}
        return packed
    packed = pack(doc)
    if len(objects) > MAX_OBJECTS: fail('TASK_STORAGE_OBJECT_LIMIT')
    envelope = {'task_contract':doc['task_contract'], 'storage_version':VERSION,
                'task':packed, 'objects':{k:len(v) for k,v in sorted(objects.items())}}
    sealed={**envelope,'storage_checksum':digest(envelope)}
    data = canonical(sealed) + b'\n'
    decode(sealed,fail,lambda key,size:objects[key])
    return data, objects


def encode(doc, fail):
    return prepare(doc, fail)[0]


def directory(index, fail):
    folder = index.parent.parent / 'objects' / index.stem
    for p in (folder.parent, folder):
        if p.is_symlink(): fail('TASK_STORAGE_UNSAFE_PATH')
    return folder


def read_object(folder, key, size, fail):
    if not HASH.fullmatch(key): fail('TASK_STORAGE_INVALID')
    p = folder / (key+'.json')
    if p.is_symlink() or not p.is_file() or p.stat().st_size != size: fail('TASK_STORAGE_OBJECT_UNAVAILABLE')
    with p.open('rb') as stream: data = stream.read(MAX_OBJECT+1)
    if len(data)!=size or hashlib.sha256(data).hexdigest()!=key: fail('TASK_STORAGE_OBJECT_CHANGED')
    return data


def decode(envelope, fail, reader=None):
    required={'task_contract','storage_version','task','objects','storage_checksum'}
    if set(envelope)!=required or envelope['storage_version']!=VERSION: fail('TASK_CHANGED')
    if envelope['storage_checksum']!=digest({k:v for k,v in envelope.items() if k!='storage_checksum'}): fail('TASK_CHANGED')
    specs=envelope['objects']
    if not isinstance(specs,dict) or len(specs)>MAX_OBJECTS: fail('TASK_STORAGE_INVALID')
    if any(not HASH.fullmatch(k) or type(n) is not int or not 0<n<=MAX_OBJECT for k,n in specs.items()): fail('TASK_STORAGE_INVALID')
    if sum(specs.values())>MAX_EXPANDED: fail('TASK_SIZE_LIMIT_EXPANDED')
    used=set(); active=set(); expanded=0
    def unpack(value):
        nonlocal expanded
        if isinstance(value,dict) and set(value)=={KEY}:
            key=value[KEY]
            if not isinstance(key,str) or key not in specs or key in active or reader is None: fail('TASK_STORAGE_INVALID')
            raw=reader(key,specs[key])
            if len(raw)!=specs[key] or hashlib.sha256(raw).hexdigest()!=key: fail('TASK_STORAGE_OBJECT_CHANGED')
            expanded+=len(raw)
            if expanded>MAX_EXPANDED: fail('TASK_SIZE_LIMIT_EXPANDED')
            try: obj=json.loads(raw)
            except (ValueError,RecursionError): fail('TASK_STORAGE_INVALID')
            if not isinstance(obj,(dict,list)) or canonical(obj)!=raw: fail('TASK_STORAGE_INVALID')
            used.add(key);active.add(key)
            result=unpack(obj);active.remove(key)
            return result
        if isinstance(value,dict): return {k:unpack(v) for k,v in value.items()}
        if isinstance(value,list): return [unpack(v) for v in value]
        return value
    doc=unpack(envelope['task'])
    if used!=set(specs) or not isinstance(doc,dict): fail('TASK_STORAGE_INVALID')
    if len(canonical(doc))>MAX_EXPANDED: fail('TASK_SIZE_LIMIT_EXPANDED')
    return doc


def read(index, envelope, fail):
    folder=directory(index,fail)
    return decode(envelope,fail,lambda key,size:read_object(folder,key,size,fail))


def inventory(folder, fail):
    total=0; count=0
    if folder.exists():
        for p in folder.iterdir():
            count+=1
            if p.is_symlink() or not p.is_file(): fail('TASK_STORAGE_UNKNOWN_OBJECT')
            total+=p.stat().st_size
            if count>MAX_OBJECTS*2 or total>MAX_STORED: fail('TASK_STORAGE_DISK_LIMIT')
    return count,total


def preflight(index, objects, fail, reserve_bytes=0, reserve_objects=0):
    folder=directory(index,fail); count,total=inventory(folder,fail)
    for key,data in objects.items():
        p=folder/(key+'.json')
        if p.exists() or p.is_symlink(): read_object(folder,key,len(data),fail)
        else: count+=1;total+=len(data)
    if count+reserve_objects>MAX_OBJECTS*2 or total+reserve_bytes>MAX_STORED: fail('TASK_STORAGE_DISK_LIMIT')
    return folder


def publish(index, data, objects, fail):
    folder=preflight(index,objects,fail)
    old={}
    if index.exists():
        previous=json.loads(index.read_bytes())
        # Validate the previously published graph before any replacement or deletion.
        read(index,previous,fail)
        old=previous['objects']
    if objects: folder.mkdir(parents=True,exist_ok=True)
    for key,content in objects.items():
        p=folder/(key+'.json')
        if not p.exists(): write(p,content)
        read_object(folder,key,len(content),fail)
    write(index,data)  # Commit point; interruption before here leaves the old graph valid.
    # Only objects named by the old verified index may be collected automatically.
    for key,size in old.items():
        if key not in objects:
            read_object(folder,key,size,fail)
            (folder/(key+'.json')).unlink()
    if folder.exists() and not any(folder.iterdir()): folder.rmdir()


def forget(index, fail):
    envelope=json.loads(index.read_bytes());read(index,envelope,fail)
    folder=directory(index,fail)
    # Unknown/unpublished objects survive; never infer ownership from a hash filename.
    index.unlink()
    for key,size in envelope['objects'].items():
        read_object(folder,key,size,fail);(folder/(key+'.json')).unlink()
    if folder.exists() and not any(folder.iterdir()): folder.rmdir()


def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.write-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)
