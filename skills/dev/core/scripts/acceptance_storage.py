"""Single-file content-addressed encoding; no evidence or event transformation."""
from copy import deepcopy
import hashlib
import json

THRESHOLD = 4096
MAX_BYTES = 256 * 1024 * 1024
MAX_DEPTH = 128
MAX_VISITS = 2000000


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def pack(document):
    if document.get('schema_version') != 8:
        return document
    objects = {}
    def node(value, depth=0):
        if depth > MAX_DEPTH:
            raise ValueError('STORAGE_INVALID: excessive depth')
        if not isinstance(value, (dict, list)) or len(canonical(value)) < THRESHOLD:
            return ['literal', deepcopy(value)]
        encoded = (['dict', {k: node(v, depth+1) for k, v in value.items()}]
                   if isinstance(value, dict) else ['list', [node(v, depth+1) for v in value]])
        ident = digest(encoded)
        objects[ident] = encoded
        return ['ref', ident]
    root = node(document)
    result = dict(schema_version=8, storage_contract=1, root=root, objects=objects)
    # Enforce the exact same safety limits for writers and readers.
    if unpack(result) != document:
        raise ValueError('STORAGE_INVALID: round trip differs')
    return result


def unpack(envelope):
    if envelope.get('schema_version') != 8:
        return envelope
    if 'storage_contract' not in envelope:
        raise ValueError('STORAGE_INVALID: schema8 envelope required')
    if set(envelope) != {'schema_version','storage_contract','root','objects'} or type(envelope['storage_contract']) is not int or envelope['storage_contract'] != 1 or not isinstance(envelope['objects'], dict):
        raise ValueError('STORAGE_INVALID: unsupported envelope')
    objects = envelope['objects']; used = set(); budget = [0, 0]
    def visit(encoded, stack=(), depth=0):
        budget[1] += 1
        if depth > MAX_DEPTH or budget[1] > MAX_VISITS:
            raise ValueError('STORAGE_INVALID: expansion limit')
        if not isinstance(encoded,list) or len(encoded)!=2:
            raise ValueError('STORAGE_INVALID: malformed node')
        tag, value = encoded
        if tag == 'literal':
            budget[0] += len(canonical(value))
            if budget[0] > MAX_BYTES:
                raise ValueError('STORAGE_INVALID: expansion bytes exceeded')
            return deepcopy(value)
        if tag == 'ref':
            if not isinstance(value,str) or value in stack or value not in objects:
                raise ValueError('STORAGE_INVALID: missing or cyclic object')
            item = objects[value]
            if digest(item) != value:
                raise ValueError('STORAGE_INVALID: object hash mismatch')
            used.add(value)
            return visit(item, stack+(value,), depth+1)
        if tag == 'dict' and isinstance(value,dict):
            budget[0] += len(canonical(list(value))) + 2
            result = {k: visit(v, stack, depth+1) for k,v in value.items()}
        elif tag == 'list' and isinstance(value,list):
            budget[0] += len(value) + 2
            result = [visit(v, stack, depth+1) for v in value]
        else:
            raise ValueError('STORAGE_INVALID: unknown node')
        if budget[0] > MAX_BYTES:
            raise ValueError('STORAGE_INVALID: expansion bytes exceeded')
        return result
    result = visit(envelope['root'])
    if used != set(objects) or not isinstance(result,dict) or result.get('schema_version') != 8 or 'storage_contract' in result:
        raise ValueError('STORAGE_INVALID: unreachable objects or invalid payload')
    return result
