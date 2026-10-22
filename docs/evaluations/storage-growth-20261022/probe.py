"""Isolated architecture experiment; NOT a FeatraceDev implementation/validator."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
SOURCE = Path('/Users/mac/Entrepôt/featrace-dev/skills/dev/core/scripts/acceptance_storage.py')
spec = importlib.util.spec_from_file_location('actual_storage', SOURCE)
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)

def raw(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()

def sha(v):
    return hashlib.sha256(v).hexdigest()

class Store:
    """In-memory Merkle bucket sketch, used only for size/access experiments."""
    def __init__(self, objects=None):
        self.objects = objects or {}
        self.reads = set()
    def put(self, v):
        data = raw(v); key = sha(data)
        self.objects.setdefault(key, data)
        return key
    def get(self, key):
        data = self.objects[key]
        if sha(data) != key:
            raise ValueError('corrupt object')
        self.reads.add(key)
        return json.loads(data)
    def tree(self, files):
        buckets = [{} for _ in range(64)]
        for path, ident in files.items():
            buckets[int(sha(path.encode())[:8], 16) % 64][path] = ident
        return self.put({'kind':'manifest', 'buckets':[self.put(b) for b in buckets]})
    def lookup(self, root, path):
        header = self.get(root)
        bucket = int(sha(path.encode())[:8], 16) % 64
        return self.get(header['buckets'][bucket])[path]
    def restore(self, root):
        value = {}
        for bucket in self.get(root)['buckets']:
            value.update(self.get(bucket))
        return value

def timed(fn):
    start = time.perf_counter(); result = fn()
    return result, time.perf_counter() - start

def growth(mode, count):
    base = {f'module/{i:05}/Source.kt':sha(f'content:{i}'.encode()) for i in range(1024)}
    worlds = []; store = Store(); roots = []
    for i in range(count):
        files = base.copy()
        if mode == 'changed':
            files['module/00000/Source.kt'] = sha(f'revision:{i}'.encode())
        manifest = {'files':files, 'schema':2}
        worlds.append({'business':manifest, 'execution':{'project_snapshot':manifest}, 'sequence':i})
        roots.append(store.tree(files))
    doc = {'schema_version':8, 'storage':{'profile':7}, 'worlds':worlds}
    plain_bytes = len(raw(doc))
    encoded, pack_seconds = timed(lambda:storage.pack(doc))
    restored, decode_seconds = timed(lambda:storage.unpack(encoded))
    assert restored == doc
    assert store.restore(roots[-1]) == worlds[-1]['business']['files']
    index = {'world_roots':roots}
    return {'scenario':mode, 'rounds':count, 'logical_bytes':plain_bytes,
            'schema8_bytes':len(raw(encoded)), 'schema8_objects':len(encoded['objects']),
            'schema8_pack_seconds':pack_seconds, 'schema8_decode_seconds':decode_seconds,
            'candidate_manifest_bytes':sum(map(len, store.objects.values()))+len(raw(index)),
            'candidate_objects':len(store.objects),
            'candidate_scope':'manifest/history root portion only; NOT an acceptance contract',
            'roundtrip_equal':True}

def projected(head, claims, offset=0, limit=25):
    if limit < 1 or limit > 25: raise ValueError('invalid page')
    blockers = [c for c in claims if c['state'] != 'supported']
    return {'head':head, 'total_claims':len(claims), 'blocker_count':len(blockers),
            'blockers':blockers[offset:offset+limit],
            'next_offset':offset+limit if offset+limit<len(blockers) else None,
            'history_validated':False, 'delivery_eligible':False,
            'limitations':['synthetic device only; full-history audit not performed']}

def resume(path):
    state = json.loads(Path(path).read_text())
    checkpoint = state['checkpoint']; head = state['head']
    if checkpoint['head'] != head:
        raise ValueError('stale checkpoint; refresh before continuing')
    all_blockers = []; offset = 0
    while True:
        page = projected(head, state['claims'], offset)
        all_blockers += page['blockers']
        if page['next_offset'] is None: break
        offset = page['next_offset']
    return {'head':head, 'blocker_ids':[c['id'] for c in all_blockers],
            'history_validated':False, 'delivery_eligible':False,
            'used_conversation_memory':False}

def counterexamples():
    results = []
    def case(name, fn):
        fn(); results.append({'name':name,'result':'passed'})
    def refuses(fn):
        try: fn()
        except (ValueError,KeyError): return
        raise AssertionError('expected refusal')
    store = Store(); files = {'a':sha(b'a'),'b':sha(b'b')}; root = store.tree(files)
    case('manifest roundtrip', lambda:assert_equal(store.restore(root), files))
    store.reads.clear(); assert store.lookup(root,'a') == files['a']
    case('point query reads root and one bucket only',lambda:assert_equal(len(store.reads),2))
    old = copy.deepcopy(store.objects); bucket=store.get(root)['buckets'][0]
    store.objects[bucket]=b'{"tampered":true}'
    case('corrupt referenced bucket refuses full restore',lambda:refuses(lambda:store.restore(root)))
    store.objects = copy.deepcopy(old); del store.objects[bucket]
    case('missing shared object refuses full restore',lambda:refuses(lambda:store.restore(root)))
    store.objects = copy.deepcopy(old)
    claims = [{'id':f'C{i:04}', 'state':'supported'} for i in range(1000)]
    for i in range(940,1000): claims[i]['state']='observed_failure' if i==999 else 'evidence_gap'
    page=projected('head-1',claims)
    case('first page cannot hide tail failure or imply eligibility',lambda:assert_equal(
        (page['total_claims'],page['blocker_count'],len(page['blockers']),page['next_offset'],page['delivery_eligible']),
        (1000,60,25,25,False)))
    checkpoint={'head':'head-1'}
    state={'head':'head-1','checkpoint':checkpoint,'claims':claims}
    path=HERE/'resume-input.json';path.write_text(json.dumps(state))
    external=json.loads(subprocess.check_output([sys.executable,str(Path(__file__).resolve()),'resume',str(path)]))
    case('fresh process recovers all blockers including final observed failure',lambda:assert_equal(
        external['blocker_ids'],[c['id'] for c in claims if c['state']!='supported']))
    state['head']='head-2';path.write_text(json.dumps(state))
    case('stale checkpoint refuses rather than reusing old conclusion',lambda:refuses(lambda:resume(path)))
    # Publication sketch: objects written first, expected-head comparison before atomic root switch.
    current={'head':'head-1'}; store.put({'unpublished':'candidate'})
    case('MODELED unpublished write leaves selected head unchanged',lambda:assert_equal(current['head'],'head-1'))
    def publish(expected, new):
        if current['head'] != expected: raise ValueError('concurrent root moved')
        current['head']=new
    publish('head-1','head-2')
    case('MODELED concurrent publication with stale expected head refuses',lambda:refuses(lambda:publish('head-1','head-3')))
    case('no final acceptance invented from partial query',lambda:assert_equal(
        (external['history_validated'],external['delivery_eligible']),(False,False)))
    page_sizes=[]
    for n in (100,1000,10000):
        xs=[{'id':f'C{i:05}','state':'evidence_gap'} for i in range(n)]
        page_sizes.append({'claims':n,'output_bytes':len(raw(projected('head',xs)))})
    return results,page_sizes

def assert_equal(a,b):
    assert a == b, (a,b)

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='resume':
        print(json.dumps(resume(sys.argv[2])));sys.exit()
    started=time.time()
    rows=[]
    for mode in ('unchanged','changed'):
        for n in (1,8,32,128):
            row=growth(mode,n);rows.append(row)
            print(json.dumps(row),flush=True)
    cases,pages=counterexamples()
    result={'source':str(SOURCE),'source_sha256':sha(SOURCE.read_bytes()),
            'synthetic_only':True,'growth':rows,'counterexamples':cases,
            'page_output_sizes':pages,'elapsed_seconds':time.time()-started,
            'limits':['no production writer or real acceptance resolver in candidate',
                      'no actual Agent compaction or semantic correctness tested',
                      'no peak memory or fee measurement',
                      'candidate and schema8 bytes have different scopes; no percentage comparison']}
    (HERE/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'counterexamples':len(cases),'elapsed_seconds':result['elapsed_seconds']}))
