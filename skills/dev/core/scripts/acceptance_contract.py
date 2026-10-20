"""Opt-in acceptance v1: immutable facts, reviewed applicability, one resolver.

No implicit migration, command execution or old-green fallback. Review evidence
is checked for provenance and scope, not certified as semantically true by hashes.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid


class ContractError(ValueError):
    def __init__(self, code, detail):
        self.code = code
        super().__init__(code + ': ' + detail)


def fail(code, detail):
    raise ContractError(code, detail)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def stamp(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def byte_hash(value):
    return hashlib.sha256(value).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def text(value):
    return isinstance(value, str) and bool(value.strip())


def exact(value, keys, code='CONTRACT_UNSUPPORTED'):
    if not isinstance(value, dict) or set(value) != set(keys):
        fail(code, 'invalid fields: ' + str(sorted(value) if isinstance(value, dict) else type(value).__name__))


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result: fail('CONTRACT_UNSUPPORTED', 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def parse(raw):
    return json.loads(raw, object_pairs_hook=_pairs, parse_constant=lambda s: fail('CONTRACT_UNSUPPORTED', 'invalid JSON constant'))


def read(path):
    if path.is_symlink(): fail('WORLD_UNKNOWN', 'symlink record: ' + str(path))
    return parse(path.read_bytes())


def enabled(doc):
    return isinstance(doc,dict) and (doc.get('schema_version') == 6 or 'acceptance_contract' in doc)


def git(root, *args):
    from check_identity import git as run
    return run(root, *args)


def safe(root, path):
    from check_runs import safe as checked
    return checked(root, path)


def pointer(doc, path):
    if not isinstance(path, str) or not path.startswith('/'):
        fail('ORIGIN_UNAVAILABLE', 'invalid JSON Pointer')
    try:
        for token in path.split('/')[1:]:
            token = token.replace('~1', '/').replace('~0', '~')
            doc = doc[int(token)] if isinstance(doc, list) else doc[token]
        return doc
    except (ValueError, KeyError, IndexError, TypeError):
        fail('ORIGIN_UNAVAILABLE', 'original JSON Pointer unavailable')


def original(root, ref):
    exact(ref, ['commit', 'path', 'blob_oid', 'sha256'], 'ORIGIN_UNAVAILABLE')
    if not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', str(ref['commit'])):
        fail('ORIGIN_UNAVAILABLE', 'full original commit required')
    safe(root, ref['path'])
    try:
        git(root, 'merge-base', '--is-ancestor', ref['commit'], 'HEAD')
        resolved = git(root, 'rev-parse', ref['commit'] + ':' + ref['path']).decode().strip()
        kind = git(root, 'cat-file', '-t', resolved).decode().strip()
        raw = git(root, 'cat-file', 'blob', resolved)
    except ValueError as exc: fail('ORIGIN_UNAVAILABLE', str(exc))
    if kind != 'blob' or resolved != ref['blob_oid'] or byte_hash(raw) != ref['sha256']:
        fail('ORIGIN_UNAVAILABLE', 'original object identity mismatch')
    return parse(raw)


def validate_document(doc):
    exact(doc, ['schema_version', 'feature_id', 'items', 'retired', 'acceptance_contract', 'acceptance'])
    if type(doc['schema_version']) is not int or type(doc['acceptance_contract']) is not int or doc['schema_version'] != 6 or doc['acceptance_contract'] != 1 or not text(doc['feature_id']):
        fail('CONTRACT_UNSUPPORTED', 'unsupported acceptance format')
    a = doc['acceptance']
    exact(a, ['contract_id', 'generation', 'origins', 'worlds', 'events'])
    try: uuid.UUID(a['contract_id'])
    except (ValueError, TypeError, AttributeError): fail('CONTRACT_UNSUPPORTED', 'invalid contract UUID')
    if (not isinstance(a['events'], list) or type(a['generation']) is not int or a['generation'] != len(a['events'])
            or not isinstance(a['worlds'], dict) or not isinstance(a['origins'], list)):
        fail('CONTRACT_UNSUPPORTED', 'invalid event generation or inventory')
    for ident, world in a['worlds'].items():
        exact(world, ['business', 'authority', 'facts', 'claims', 'execution', 'environment'])
        if stamp(world) != ident: fail('CONTRACT_UNSUPPORTED', 'world digest mismatch')
    previous = None; registered=set()
    for i, event in enumerate(a['events']):
        exact(event, ['seq', 'previous', 'kind', 'payload', 'at', 'actor', 'id'])
        if (type(event['seq']) is not int or event['seq'] != i or event['previous'] != previous or event['kind'] not in ('init', 'reconcile', 'fact', 'assessment')
                or stamp({k:v for k,v in event.items() if k != 'id'}) != event['id']
                or not text(event['at']) or not text(event['actor'])):
            fail('CONTRACT_UNSUPPORTED', 'broken event chain')
        if (i == 0) != (event['kind'] == 'init'): fail('CONTRACT_UNSUPPORTED', 'exactly one initial event required')
        payload_fields={'init':['claims','approval','initial_world_digest'],'reconcile':['claims','prior_keys','resolutions'],'fact':['ref','source'],'assessment':['request','review']}
        exact(event['payload'],payload_fields[event['kind']])
        if event['kind'] in ('init', 'reconcile'):
            for claim in event['payload']['claims']:
                exact(claim, ['claim_key', 'version_digest', 'locator', 'kind', 'criterion', 'parent_context', 'authority_refs', 'execution_mapping', 'predecessors'])
                if stamp({k:v for k,v in claim.items() if k not in ('version_digest', 'locator')}) != claim['version_digest']:
                    fail('CONTRACT_UNSUPPORTED', 'claim version mismatch')
        if event['kind'] == 'fact':
            ref = event['payload']['ref']
            exact(ref,['row_id','history_index','pointer','sha256'])
            marker=(ref['row_id'],ref['history_index'])
            if marker in registered: fail('CONTRACT_UNSUPPORTED','fact registered twice')
            registered.add(marker)
            rows = [r for r in doc['items'] + doc['retired'] if r['id'] == ref['row_id']]
            if type(ref['history_index']) is not int or ref['history_index']<0 or (rows and ref['history_index']>=len(rows[0]['history'])):
                fail('CONTRACT_UNSUPPORTED','invalid fact history index')
            if len(rows) != 1: fail('CONTRACT_UNSUPPORTED', 'fact row missing')
            fact = rows[0]['history'][ref['history_index']]
            if stamp(fact) != ref['sha256']: fail('CONTRACT_UNSUPPORTED', 'fact modified after registration')
        if event['kind'] == 'assessment':
            request = event['payload']['request']
            prior_assessment=latest_event({'acceptance':{'events':a['events'][:i]}},'assessment')
            if request['from_event'] != (prior_assessment['id'] if prior_assessment else None):
                fail('CONTRACT_UNSUPPORTED','assessment must follow latest judgment')
            exact(request,['contract_id','generation','from_event','world_digest','active_versions','deltas','fact_refs','plan_digest','request_digest'])
            if stamp({k:v for k,v in request.items() if k!='request_digest'}) != request['request_digest']:
                fail('CONTRACT_UNSUPPORTED','request digest mismatch')
            if request['world_digest'] not in a['worlds'] or type(request['generation']) is not int or request['generation'] != i:
                fail('CONTRACT_UNSUPPORTED', 'invalid assessment world or order')
            frozen=a['worlds'][request['world_digest']]
            if request['active_versions']!=frozen['claims'] or request['fact_refs']!=frozen['facts'] or request['contract_id']!=a['contract_id']:
                fail('CONTRACT_UNSUPPORTED','request differs from frozen world')
        previous = event['id']
    if not a['events']: fail('CONTRACT_UNSUPPORTED', 'missing initial event')
    ids = set()
    for row in doc['items'] + doc['retired']:
        if not isinstance(row, dict) or not text(row.get('id')) or row['id'] in ids or not isinstance(row.get('history'), list):
            fail('CONTRACT_UNSUPPORTED', 'invalid row inventory')
        ids.add(row['id'])
        allowed={'id','source','expected','mode','gates','coverage','history','acceptance_contract','test_ids','dependencies','scope_reason'}
        if set(row)-allowed or row.get('acceptance_contract') != 1:
            fail('CONTRACT_UNSUPPORTED', 'unknown row fields or missing contract marker')
        if row.get('mode') not in ('manual', 'automatic') or not isinstance(row.get('gates'), list):
            fail('CONTRACT_UNSUPPORTED', 'invalid execution mapping')
        if (row['mode']=='manual' and row['gates']) or (row['mode']=='automatic' and (not row['gates'] or not text(row.get('coverage')))):
            fail('CONTRACT_UNSUPPORTED','invalid manual/automatic mapping')
        for index,fact in enumerate(row['history']):
            if (row['id'],index) not in registered: fail('CONTRACT_UNSUPPORTED','unregistered fact added to history')
            if set(fact)-{'status','digest','tested_revision','actual','evidence','at','method','observed_at'}:
                fail('CONTRACT_UNSUPPORTED','unknown new fact field')
            if fact.get('status') not in ('passed', 'failed', 'unavailable', 'waived'):
                fail('CONTRACT_UNSUPPORTED', 'only direct new facts supported')
            if any(not text(fact.get(k)) for k in ('digest', 'tested_revision', 'actual', 'evidence', 'at', 'method')):
                fail('CONTRACT_UNSUPPORTED', 'incomplete direct fact')
    for index,event in enumerate(a['events']):
        if event['kind'] != 'assessment': continue
        prefix=deepcopy(doc); prefix['acceptance']['events']=a['events'][:index]; prefix['acceptance']['generation']=index
        request=event['payload']['request']; current=a['worlds'][request['world_digest']]
        _validate_review(prefix,request,event['payload']['review'],current)
    return doc


def load(folder):
    doc = validate_document(read(folder / 'verification.json'))
    if doc['feature_id'] != folder.name: fail('CONTRACT_UNSUPPORTED', 'feature mismatch')
    return doc


def latest_event(doc, kind):
    return next((e for e in reversed(doc['acceptance']['events']) if e['kind'] == kind), None)


def active_claims(doc):
    return next(e['payload']['claims'] for e in reversed(doc['acceptance']['events']) if e['kind'] in ('init', 'reconcile'))


def append(doc, kind, payload, actor):
    a = doc['acceptance']
    event = dict(seq=len(a['events']), previous=a['events'][-1]['id'] if a['events'] else None,
                 kind=kind, payload=payload, at=now(), actor=actor)
    event['id'] = stamp(event); a['events'].append(event); a['generation'] = len(a['events'])
    return event


def refuse_legacy(doc):
    if enabled(doc): fail('LEGACY_WRITER_DISABLED', 'use acceptance reconciliation, new direct facts or assessment')


@contextmanager
def mutation(root, folder):
    if safe(root,folder) != Path(root).resolve()/'.agent-workflow/features'/folder.name:
        fail('WORLD_UNKNOWN','feature folder outside canonical workspace')
    from check_runs import execution_lock, no_unfinished
    manager=execution_lock(root)
    try:
        manager.__enter__()
    except ValueError as exc:
        fail('WORKSPACE_BUSY',str(exc))
    try:
        from feature_lifecycle import require_active
        require_active(read(folder/'spec/requirements.json')['feature'])
        try: no_unfinished(root)
        except ValueError as exc: fail('WORKSPACE_BUSY',str(exc))
        import fcntl
        p=safe(root,'.agent-workflow/scratch/verification-'+folder.name+'.lock')
        p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('a') as stream:
            try: fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError: fail('WORKSPACE_BUSY','verification writer active')
            yield
    finally:
        manager.__exit__(None,None,None)


def write(root, folder, doc, before):
    from check_runs import save
    path=folder/'verification.json'
    if (read(path) if path.exists() else None) != before: fail('INPUTS_MOVED', 'plan changed before commit')
    validate_document(doc)
    save(root, folder / 'verification.json', doc)


def _sources(root, folder):
    # sources() validates impact and calls impact_results only for check, not develop.
    from verification import sources, candidates
    req, config, impact = sources(root, folder)
    return req, config, impact, candidates(req, config, impact)


def build_claims(req, impact, rows, prior=(), resolutions=None, decisions=None):
    resolutions = resolutions or {}
    old = {c['locator']: c for c in prior}
    claims = []
    requirements = {r['id']:r for r in req['requirements']}
    behaviors = {b['id']:b for b in impact['behaviors']}
    for row in rows:
        loc = row['source']
        if not loc.startswith(('requirement:', 'impact:')): continue
        kind, ident, *_ = loc.split(':')
        parent = deepcopy(requirements[ident] if kind == 'requirement' else behaviors[ident])
        # Explicit source basis and local context; siblings excluded from versions.
        bases=parent.pop('acceptance_basis',[])
        basis=[x for x in bases if isinstance(x,dict) and x.get('index')==int(loc.split(':')[2])-1] if kind=='requirement' else parent.get('basis',[])
        refs={'sources':deepcopy(parent.get('sources',[])),'basis':deepcopy(basis)}
        mentioned=set(re.findall(r'\bD-[A-Za-z0-9_-]+',json.dumps(refs,ensure_ascii=False)))
        refs['decisions']=[deepcopy(d) for d in (decisions or {}).get('decisions',[]) if d.get('id') in mentioned]
        parent={k:parent.get(k) for k in (('statement','status','assumptions') if kind=='requirement' else ('statement','kind'))}
        prior_claim = old.get(loc)
        resolution = resolutions.get(loc)
        if prior_claim and prior_claim['criterion'] != row['expected'] and not resolution:
            fail('PLAN_RECONCILIATION_REQUIRED', 'changed criterion needs exact source alignment: ' + loc)
        if resolution and not text(resolution.get('authority_evidence')):
            fail('PLAN_RECONCILIATION_REQUIRED', 'source alignment requires authority evidence')
        key = (resolution or {}).get('claim_key') or (prior_claim or {}).get('claim_key') or str(uuid.uuid4())
        try: uuid.UUID(key)
        except (TypeError,ValueError): fail('PLAN_RECONCILIATION_REQUIRED', 'invalid claim UUID')
        if prior_claim and resolution and key != prior_claim['claim_key']:
            predecessors = sorted(set(resolution.get('predecessors', []) + prior_claim['predecessors'] + [prior_claim['claim_key']]))
        else: predecessors = (resolution or {}).get('predecessors', (prior_claim or {}).get('predecessors', []))
        claim = dict(claim_key=key, locator=loc, kind=kind, criterion=row['expected'], parent_context=parent,
                     authority_refs=refs,
                     execution_mapping={k:deepcopy(row[k]) for k in ('mode', 'gates', 'coverage', 'test_ids','dependencies','scope_reason') if k in row},
                     predecessors=predecessors)
        claim['version_digest'] = stamp({k:v for k,v in claim.items() if k != 'locator'})
        claims.append(claim)
    if len({c['claim_key'] for c in claims}) != len(claims): fail('PLAN_RECONCILIATION_REQUIRED', 'duplicate key')
    return claims


def _origin_rows(root, doc):
    rows = []
    for ref in doc['acceptance']['origins']:
        origin = original(root, ref)
        if Path(ref['path']).name == 'verification.json':
            for section in ('items', 'retired'):
                for i, row in enumerate(origin[section]):
                    rows.append((row, ref, '/' + section + '/' + str(i)))
    return rows


def fact_summary(entry):
    return {k:entry[k] for k in ('status','tested_revision','at','method')}


def fact_inventory(root, doc):
    facts = {}
    for row, origin, path in _origin_rows(root, doc):
        # Preserve the full chronological negative inventory, not just the green candidate.
        for i, entry in enumerate(row.get('history', [])):
            ref = dict(container='origin_git', origin=origin, pointer=path + '/history/' + str(i), sha256=stamp(entry),
                       tested_revision=entry['tested_revision'], registered_at=entry['at'], method=entry['method'])
            if 'observed_at' in entry: ref['observed_at'] = entry['observed_at']
            facts[stamp(ref)] = dict(ref=ref, fact=fact_summary(entry), source=row['source'], row_id=row['id'], order=i)
    for section in ('items', 'retired'):
        for i, row in enumerate(doc[section]):
            for j, entry in enumerate(row['history']):
                ref = dict(container='current_history', pointer='/' + section + '/' + str(i) + '/history/' + str(j), sha256=stamp(entry),
                           tested_revision=entry['tested_revision'], registered_at=entry['at'], method=entry['method'])
                if 'observed_at' in entry: ref['observed_at'] = entry['observed_at']
                ident=stamp({'container':'current_history','row_id':row['id'],'history_index':j,'sha256':stamp(entry)})
                facts[ident] = dict(ref=ref, fact=fact_summary(entry), source=row['source'], row_id=row['id'], order=j)
    return facts


def _authority(folder):
    result = {}
    # Scan the actual feature record/source/evidence inventory, not a fixed allowlist
    # that could silently omit a newly introduced authority field or document.
    excluded = {'verification.json', 'verification.md', 'claim-review.json', 'delivery-report.md'}
    for path in sorted(folder.rglob('*')):
        if path.is_symlink(): fail('WORLD_UNKNOWN', 'symlink feature input')
        if not path.is_file(): continue
        rel = path.relative_to(folder).as_posix()
        if rel in excluded or rel.startswith(('check-runs/', 'check-head.json')): continue
        generated={'tasks.md','decisions.md','impact.md','traceability.md','fixes.md','regression-review.md','spec/requirements.md','spec/spec.md','spec/prd-analysis.md','task-review.md','revisions.md'}
        if rel in generated: continue  # exact generated views only
        if path.suffix == '.json' and not rel.startswith(('sources/', 'evidence/')):
            value = read(path)
            if rel == 'spec/requirements.json':
                value = deepcopy(value); feature=value.get('feature',{});feature.pop('status',None)
                # Delivery registrations are validated control outputs, not new product meaning.
                if isinstance(feature.get('baseline'),dict): feature['baseline'].pop('deliveries',None)
            if rel == 'tasks.json':
                value = deepcopy(value)
                for task in value.get('tasks', []): task.pop('status', None)
            result[rel] = value
        else: result[rel] = {'sha256':byte_hash(path.read_bytes())}
    return result


def world(root, folder, doc, *, locked=False):
    if safe(root,folder) != Path(root).resolve()/'.agent-workflow/features'/folder.name:
        fail('WORLD_UNKNOWN','feature folder outside canonical workspace')
    from check_runs import enabled as attempts_enabled, view, _current
    from check_identity import capture
    if not attempts_enabled(root): fail('PREPARE_REQUIRED', 'project execution contract2 required')
    ident = capture(root)
    if ident.get('state') != 'identified': fail('WORLD_UNKNOWN', str(ident))
    # Workflow-only commits do not change business inputs.
    business = {k:v for k,v in ident.items() if k != 'head'}
    if locked:
        try:
            report = _current(root, folder.name)
            execution = {'state':'current', 'attempt_id':report['attempt_id'], 'digest':report['attempt_digest'], 'report':report}
        except (ValueError, OSError, KeyError, TypeError) as exc: execution = {'state':'unavailable', 'reason':str(exc)}
    else: execution = view(root, folder.name)
    execution = {k:v for k,v in execution.items() if k != 'report_ref'}
    facts = fact_inventory(root, doc)
    if execution['state']=='current':
        report=execution['report']
        ref=dict(container='check_attempt',attempt_id=report['attempt_id'],attempt_digest=report['attempt_digest'],pointer='result.json',sha256=report['attempt_digest'],tested_revision=report['project_snapshot']['git_head'],registered_at=report['tested_at'],method='automatic')
        facts[stamp(ref)]=dict(ref=ref,fact=dict(status='passed',tested_revision=ref['tested_revision'],at=ref['registered_at'],method='automatic'),source='execution:current',row_id='execution:current',order=0)
    authority=_authority(folder)
    authority['_project_check_config']=read(safe(root,'.agent-workflow/project-baseline/quality-gates.json'))
    return dict(business=business, authority=authority, facts=facts,
                claims=active_claims(doc), execution=execution,
                environment={'scope':'fact-recorded environments only; unknown external targets not certified'})


def delta(before, after, path=''):
    result = []
    if before == after: return result
    if isinstance(before, dict) and isinstance(after, dict):
        for k in sorted(set(before) | set(after)):
            p = path + '/' + k.replace('~','~0').replace('/','~1')
            if k not in before or k not in after:
                result.append({'path':p, 'before':before.get(k), 'after':after.get(k), 'operation':'add' if k not in before else 'remove'})
            else: result.extend(delta(before[k], after[k], p))
    else: result.append({'path':path, 'before':before, 'after':after, 'operation':'replace'})
    for change in result:
        change['id'] = stamp({k:v for k,v in change.items() if k != 'id'})
    return result


def _aligned(root, folder, doc):
    req, config, impact, generated = _sources(root, folder)
    rows = {r['source']:r for r in doc['items']}
    if set(rows) != {r['source'] for r in generated}:
        fail('PLAN_RECONCILIATION_REQUIRED', 'source inventory changed; sync first')
    current = []
    for row in generated:
        old = rows[row['source']]
        if old['expected'] != row['expected']: fail('PLAN_RECONCILIATION_REQUIRED', 'criterion changed; sync with explicit alignment')
        current.append({**row, **{k:old[k] for k in ('mode','gates','coverage','test_ids','dependencies','scope_reason') if k in old}})
    rebuilt = build_claims(req, impact, current, active_claims(doc),decisions=read(folder/'decisions.json'))
    if rebuilt != active_claims(doc): fail('PLAN_RECONCILIATION_REQUIRED', 'claim context or mapping changed; sync first')
    return config


def inspect_contract(root, folder):
    doc = load(folder); _aligned(root, folder, doc)
    return {'contract':1, 'contract_id':doc['acceptance']['contract_id'], 'generation':doc['acceptance']['generation']}


def capture_assessment(root, folder, *, doc=None, locked=False):
    doc = doc or load(folder); _aligned(root, folder, doc)
    current = world(root, folder, doc, locked=locked)
    last = latest_event(doc, 'assessment')
    before = doc['acceptance']['worlds'][last['payload']['request']['world_digest']] if last else {}
    request = dict(contract_id=doc['acceptance']['contract_id'], generation=doc['acceptance']['generation'],
                   from_event=last['id'] if last else None, world_digest=stamp(current), active_versions=active_claims(doc),
                   deltas=delta(before, current), fact_refs=current['facts'], plan_digest=stamp(doc))
    request['request_digest'] = stamp(request)
    return request, current


def _latest_facts(current, source):
    return sorted(((k,v) for k,v in current['facts'].items() if v['source'] == source), key=lambda x:(x[1]['fact']['at'],x[1]['ref']['container']=='current_history',x[1]['order']))


def reuse_actions(review):
    expanded=[]
    for action in review['reuse']:
        if 'targets' not in action: expanded.append(action);continue
        exact(action,['targets','evidence','semantic_equivalence'],'REVIEW_INCOMPLETE')
        for target in action['targets']:
            exact(target,['claim_key','from_key'],'REVIEW_INCOMPLETE')
            expanded.append(dict(target,evidence=action['evidence'],semantic_equivalence=action['semantic_equivalence']))
    return expanded


def _judgments(doc):
    judgments={}
    for event in doc['acceptance']['events']:
        if event['kind']!='assessment':continue
        request=event['payload']['request'];review=event['payload']['review'];prior=judgments;judgments={}
        versions={c['claim_key']:c['version_digest'] for c in request['active_versions']}
        for action in review['assess']:
            judgments[action['claim_key']]=dict(action,version=versions[action['claim_key']])
        for action in reuse_actions(review):
            old=deepcopy(prior[action['from_key']]);old['version']=versions[action['claim_key']];judgments[action['claim_key']]=old
        for action in review['pending']:
            judgments[action['claim_key']]={'verdict':'unknown','version':versions[action['claim_key']],'fact_refs':[],'reason':action['reason']}
    return judgments


def retired_claims(doc):
    known={c['claim_key']:c for e in doc['acceptance']['events'] if e['kind'] in ('init','reconcile') for c in e['payload']['claims']}
    live={c['claim_key'] for c in active_claims(doc)}|{k for c in active_claims(doc) for k in c['predecessors']}
    return {k:c for k,c in known.items() if k not in live}


def retired_blockers(doc):
    last=latest_event(doc,'assessment')
    disposed={r['barrier_id'] for r in last['payload']['review']['barrier_resolutions']} if last else set()
    # Valid earlier dispositions remain valid only until the world changes and
    # a new reviewed complete delta confirms them; capture still includes removal.
    for e in doc['acceptance']['events']:
        if e['kind']=='assessment': disposed.update(r['barrier_id'] for r in e['payload']['review']['barrier_resolutions'])
    return [{'code':'NEGATIVE_UNRESOLVED','detail':'retire:'+k} for k in retired_claims(doc) if 'retire:'+k not in disposed]


def resolve_claims(root, folder, snapshot=None):
    doc = load(folder); req, current = snapshot or capture_assessment(root, folder, doc=doc)
    last = latest_event(doc, 'assessment'); judgments = _judgments(doc)
    applies = bool(last and last['payload']['request']['world_digest'] == req['world_digest'])
    items = []
    for row in doc['items']:
        facts = _latest_facts(current, row['source']); latest = facts[-1][1]['fact'] if facts else None
        if row['source'].startswith('gate:'):
            outcome = 'passed' if current['execution']['state'] == 'current' else 'unavailable'
            verdict = None
        elif row['source']=='system:no-gates':
            outcome='unavailable';verdict=None
        else:
            claim = next(c for c in active_claims(doc) if c['locator'] == row['source'])
            finding = judgments.get(claim['claim_key'])
            verdict = finding['verdict'] if finding and applies else None
            outcome = 'waived' if verdict == 'approved_waiver' else 'passed' if verdict == 'supported' else 'stale' if latest or finding else 'not_run'
            if latest and latest['status'] in ('failed','unavailable') and outcome != 'passed': outcome = latest['status']
        items.append({'id':row['id'], 'mode':row['mode'], 'expected':row['expected'], 'status':outcome,
                      'fact_status':latest['status'] if latest else 'not_run', 'result':latest,
                      'applicability':'current' if applies else 'needs_review', 'coverage_verdict':verdict})
    blockers = [dict(code='ASSESSMENT_REQUIRED', item=x['id'], status=x['status']) for x in items if x['status'] not in ('passed','waived')]
    blockers.extend(retired_blockers(doc))
    if current['execution']['state'] != 'current': blockers.append({'code':'EXECUTION_UNAVAILABLE', 'detail':current['execution'].get('reason','')})
    return dict(contract=1, digest=req['world_digest'], tested_revision=git(root,'rev-parse','HEAD').decode().strip(),
                contract_id=req['contract_id'], generation=req['generation'], items=items, blockers=blockers,
                acceptance_eligible=not blockers, delivery_eligible=False, delivery_guards='not_evaluated', world=current)


def _proof(folder, request, review):
    ref = review.get('reviewer_evidence_ref')
    if not isinstance(ref, dict) or set(ref) != {'path','sha256'}: fail('REVIEW_NOT_INDEPENDENT', 'host review provenance required')
    root = folder.parents[2]; path = safe(root, ref['path'])
    base = root / '.agent-workflow/scratch/acceptance-reviews' / folder.name
    if not path.is_relative_to(base): fail('REVIEW_NOT_INDEPENDENT', 'host review provenance must use isolated acceptance-reviews scratch')
    raw = path.read_bytes()
    if byte_hash(raw) != ref['sha256']: fail('REVIEW_NOT_INDEPENDENT', 'review provenance hash mismatch')
    proof = parse(raw)
    if (proof.get('request_digest') != request['request_digest'] or proof.get('fresh_context') is not True
            or not text(proof.get('host')) or not text(proof.get('context_id')) or proof.get('reviewer') != review['reviewer']):
        fail('REVIEW_NOT_INDEPENDENT', 'actual fresh host context evidence required; a label alone is insufficient')


def _validate_review(doc, request, review, current):
    exact(review, ['request_digest','reviewer','reviewer_evidence_ref','change_findings','assess','reuse','pending','barrier_resolutions'], 'REVIEW_INCOMPLETE')
    if review['request_digest'] != request['request_digest'] or not text(review['reviewer']): fail('REVIEW_INCOMPLETE', 'review/request mismatch')
    if any(not isinstance(review[k],list) for k in ('change_findings','assess','reuse','pending','barrier_resolutions')):
        fail('REVIEW_INCOMPLETE','review collections must be arrays')
    changes = {d['id']:d for d in request['deltas']}
    findings = review['change_findings']
    if len(findings) != len(changes) or {x.get('id') for x in findings} != set(changes): fail('REVIEW_INCOMPLETE', 'cover every delta once')
    unknown = set(); affected=set()
    keys = {c['claim_key']:c for c in request['active_versions']}
    for finding in findings:
        exact(finding, ['id','classification','targets','evidence'], 'REVIEW_INCOMPLETE')
        if (finding['classification'] not in ('affected','unaffected_with_evidence','unknown') or not text(finding['evidence'])
                or not isinstance(finding['targets'], list) or not set(finding['targets']) <= set(keys)):
            fail('REVIEW_INCOMPLETE', 'invalid change classification')
        if finding['classification'] == 'affected': affected.update(finding['targets'])
        if finding['classification'] == 'unknown': unknown.update(finding['targets'] or keys)
    reuse=reuse_actions(review)
    actions = review['assess'] + reuse + review['pending']
    if len(actions) != len(keys) or {x.get('claim_key') for x in actions} != set(keys): fail('REVIEW_INCOMPLETE', 'partition complete active set exactly once')
    prior = _judgments(doc); judgments = {}
    resolutions = {r['barrier_id']:r for r in review['barrier_resolutions']}
    for ident,resolution in resolutions.items():
        if ident.startswith('retire:'):
            key=ident[7:]
            if key not in retired_claims(doc) or any(not text(resolution.get(k)) for k in ('authority_evidence','addresses','evidence')):
                fail('NEGATIVE_UNRESOLVED','retirement requires explicit reviewed scope and authority')
    if len(resolutions)!=len(review['barrier_resolutions']): fail('REVIEW_INCOMPLETE','duplicate barrier resolution')
    for action in actions:
        key = action['claim_key']; claim = keys[key]
        if action in review['pending']:
            exact(action, ['claim_key','reason'], 'REVIEW_INCOMPLETE')
            if not text(action['reason']): fail('REVIEW_INCOMPLETE', 'pending reason required')
            judgments[key] = {'verdict':'unknown', 'version':claim['version_digest'], 'fact_refs':[], 'reason':action['reason']}
            continue
        if key in unknown: fail('WORLD_UNKNOWN', 'unknown change cannot support or reuse target')
        if action in reuse:
            if key in affected: fail('REVIEW_INCOMPLETE','affected target requires fresh assessment, not reuse')
            exact(action, ['claim_key','from_key','evidence','semantic_equivalence'], 'REVIEW_INCOMPLETE')
            old = prior.get(action['from_key'])
            if action['from_key'] != key: fail('REVIEW_INCOMPLETE','new/split keys require fresh assessment, not inherited support')
            if (not old or old['verdict'] not in ('supported','approved_waiver') or not text(action['evidence'])
                    or not text(action['semantic_equivalence'])):
                fail('REVIEW_INCOMPLETE', 'reuse requires latest supported judgment and explicit equivalence')
            finding = deepcopy(old); finding['version'] = claim['version_digest']
        else:
            exact(action, ['claim_key','verdict','source_basis','required_scope','observed_scope','evidence_ref','counterexample_check','fact_refs'], 'REVIEW_INCOMPLETE')
            if action['verdict'] not in ('supported','partial','unknown','approved_waiver'):
                fail('REVIEW_INCOMPLETE', 'invalid verdict')
            if any(not text(action[k]) for k in ('source_basis','required_scope','observed_scope','evidence_ref','counterexample_check')):
                fail('REVIEW_INCOMPLETE', 'precise coverage and contrary evidence required')
            finding = deepcopy(action); finding['version'] = claim['version_digest']
        refs = finding['fact_refs']
        allowed = set(current['facts'])
        attempt_refs={k for k,v in current['facts'].items() if v['ref']['container']=='check_attempt' and current['execution']['state']=='current' and v['ref']['attempt_id']==current['execution'].get('attempt_id')}
        if not isinstance(refs, list) or len(refs) != len(set(refs)) or not set(refs) <= allowed: fail('REVIEW_INCOMPLETE', 'invalid fact refs')
        positive = finding['verdict'] in ('supported','approved_waiver')
        candidates = _latest_facts(current, claim['locator'])
        latest = candidates[-1] if candidates else None
        if positive:
            if finding['verdict']=='supported' and claim['execution_mapping']['mode']=='automatic' and not claim['execution_mapping'].get('gates'):
                fail('EXECUTION_UNAVAILABLE','automatic claim requires mapped gates')
            if not refs: fail('REVIEW_INCOMPLETE', 'support without facts')
            if finding['verdict'] == 'approved_waiver':
                if not any(r in current['facts'] and current['facts'][r]['fact']['status'] == 'waived' for r in refs):
                    fail('REVIEW_INCOMPLETE', 'waiver requires original authority')
            elif claim['execution_mapping']['mode'] == 'automatic':
                if not set(refs)&attempt_refs or current['execution']['state'] != 'current': fail('EXECUTION_UNAVAILABLE', 'current complete attempt required')
                report = current['execution']['report']; executed = {g['name']:g for g in report['results']}
                test_ids=claim['execution_mapping'].get('test_ids',[])
                if not test_ids or not set(test_ids) <= {t for g in claim['execution_mapping']['gates'] for t in executed.get(g,{}).get('test_ids',[])}:
                    fail('EXECUTION_UNAVAILABLE','actual executed assertion IDs required for automatic business claim')
                if any(g not in executed or executed[g]['status'] != 'passed' for g in claim['execution_mapping']['gates']):
                    fail('EXECUTION_UNAVAILABLE', 'mapped required gate absent')
            elif not any(r in current['facts'] and current['facts'][r]['source'] == claim['locator'] and current['facts'][r]['fact']['status'] == 'passed' for r in refs):
                fail('REVIEW_INCOMPLETE', 'manual support needs matching direct passed observation')
        resolved_prior={r['barrier_id'] for e in doc['acceptance']['events'] if e['kind']=='assessment' for r in e['payload']['review']['barrier_resolutions']}
        barriers = []
        # Persist old negatives even when the world/key changes. Resolution must
        # target a new relevant fact or changed authority, not an unrelated delta.
        for event in doc['acceptance']['events']:
            if event['kind'] != 'assessment': continue
            index=event['seq'];prefix=deepcopy(doc);prefix['acceptance']['events']=doc['acceptance']['events'][:index+1]
            for oldkey, old in _judgments(prefix).items():
                if oldkey in [key] + claim['predecessors'] and old['verdict'] in ('partial','unknown'):
                    barriers.append((event['id'] + ':' + oldkey, dict(old,at=event['at'])))
        for fact_id, item in candidates:
            if item['fact']['status'] in ('failed','unavailable'):
                barriers.append((fact_id, {'fact_refs':[fact_id], 'version':claim['version_digest'], 'at':item['fact']['at']}))
        for barrier_id, old in barriers:
            if barrier_id in resolved_prior: continue
            if not positive: continue
            resolution = resolutions.get(barrier_id)
            if not resolution or not text(resolution.get('evidence')):
                fail('NEGATIVE_UNRESOLVED', 'explicit resolution required: ' + barrier_id)
            new_refs = {r for r in set(refs)-set(old.get('fact_refs', [])) if r in current['facts']
                        and current['facts'][r]['source']==claim['locator']
                        and current['facts'][r]['fact']['status']=='passed'
                        and current['facts'][r]['fact']['at'] > old.get('at', '0000')}
            new_authority = old.get('version') != claim['version_digest'] and text(resolution.get('authority_evidence'))
            if not isinstance(resolution.get('addresses'),str) or not resolution['addresses'].strip():
                fail('NEGATIVE_UNRESOLVED','resolution must address the original counterexample')
            if not new_refs and not new_authority: fail('NEGATIVE_UNRESOLVED', 'new targeted evidence/authority required')
        judgments[key] = finding
    return judgments


def apply_assessment(root, folder, request, review):
    with mutation(root, folder):
        before = load(folder)
        last = latest_event(before, 'assessment')
        if last and last['payload']['request'] == request and last['payload']['review'] == review:
            # Still verify live inputs before idempotent readback.
            live = world(root, folder, before, locked=True)
            if stamp(live) != request['world_digest']: fail('INPUTS_MOVED', 'inputs moved after original apply')
            return before
        actual, current = capture_assessment(root, folder, doc=before, locked=True)
        if actual != request: fail('INPUTS_MOVED', 'frozen request changed')
        _proof(folder, request, review)
        judgments = _validate_review(before, request, review, current)
        # Host return is judgment provenance, not an input it recursively hashes.
        _proof(folder, request, review)
        if world(root, folder, before, locked=True) != current: fail('INPUTS_MOVED', 'world moved during review validation')
        doc = deepcopy(before); doc['acceptance']['worlds'][request['world_digest']] = current
        append(doc, 'assessment', {'request':request, 'review':review}, review['reviewer'])
        write(root, folder, doc, before)
    return doc


def reconcile_claims(root, folder, resolutions=None):
    with mutation(root, folder):
        before = load(folder)
        req, _, impact, generated = _sources(root, folder)
        from feature_lifecycle import require_active
        require_active(req['feature'])
        oldrows = {r['source']:r for r in before['items']}
        rows = []
        for row in generated:
            old = oldrows.get(row['source'])
            if old is None:
                old=next((r for r in before['retired'] if r['id']==row['id'] and r['source']==row['source']),None)
            if old and old['expected'] == row['expected']: rows.append(deepcopy(old))
            else:
                if old:
                    row.update({k:deepcopy(old[k]) for k in ('mode','gates','coverage','test_ids','dependencies','scope_reason') if k in old})
                row['acceptance_contract']=1
                rows.append(row)
        for prior in active_claims(before):
            if prior['locator'] not in {r['source'] for r in rows}:
                resolution=(resolutions or {}).get(prior['locator'], {})
                if resolution.get('retire') is not True or not text(resolution.get('authority_evidence')):
                    fail('PLAN_RECONCILIATION_REQUIRED','retirement needs explicit product authority and negative disposition')
        history_by_locator={c['locator']:c for e in before['acceptance']['events'] if e['kind'] in ('init','reconcile') for c in e['payload']['claims']}
        claims = build_claims(req, impact, rows, list(history_by_locator.values()), resolutions,decisions=read(folder/'decisions.json'))
        if rows == before['items'] and claims == active_claims(before): return before
        doc = deepcopy(before); oldids = {r['id'] for r in rows}
        doc['retired'] = [r for r in before['retired'] if r['id'] not in oldids] + [r for r in before['items'] if r['id'] not in oldids]
        doc['items'] = rows
        append(doc, 'reconcile', {'claims':claims, 'prior_keys':[c['claim_key'] for c in active_claims(before)], 'resolutions':resolutions or {}}, 'verification sync')
        write(root, folder, doc, before)
    return doc


def record_fact(root, folder, item_id, status, frozen, tested, actual, evidence):
    with mutation(root, folder):
        before = load(folder); request, current = capture_assessment(root, folder, doc=before, locked=True)
        if frozen != request['world_digest'] or tested != git(root, 'rev-parse','HEAD').decode().strip(): fail('INPUTS_MOVED', 'new observation identity changed')
        if status not in ('passed','failed','unavailable','waived') or not text(actual) or not text(evidence): fail('REVIEW_INCOMPLETE', 'direct complete observation required')
        doc = deepcopy(before)
        index = next((i for i,r in enumerate(doc['items']) if r['id'] == item_id and r['mode'] == 'manual'), None)
        if index is None: fail('REVIEW_INCOMPLETE', 'manual target required')
        row = doc['items'][index]
        fact = dict(status=status,digest=frozen,tested_revision=tested,actual=actual,evidence=evidence,at=now(),method='manual')
        row['history'].append(fact)
        ref = dict(row_id=row['id'],history_index=len(row['history'])-1,pointer='/items/' + str(index) + '/history/' + str(len(row['history'])-1),sha256=stamp(fact))
        append(doc,'fact',{'ref':ref,'source':row['source']},'verification record')
        if world(root,folder,before,locked=True) != current: fail('INPUTS_MOVED','inputs moved before fact commit')
        write(root,folder,doc,before)
    return doc


def prepare(root, folder, approval):
    from verification import load_plan, candidates, sources
    from check_runs import enabled as attempt_enabled
    with mutation(root,folder):
        exists=(folder/'verification.json').exists()
        before = load_plan(folder) if exists else None
        if before is not None and enabled(before): return before
        req, config, impact = sources(root,folder)
        if req['feature'].get('status') == 'complete': fail('PREPARE_REQUIRED','completed features are not migration targets')
        if not attempt_enabled(root): fail('PREPARE_REQUIRED','project execution contract2 must be prepared explicitly first')
        participants = sorted(f.name for f in folder.parent.iterdir() if (f/'spec/requirements.json').is_file() and read(f/'spec/requirements.json')['feature'].get('status') != 'complete')
        if (not isinstance(approval,dict) or approval.get('active_features') != participants or not text(approval.get('evidence'))
                or not approval.get('hosts') or any(not isinstance(h,dict) or h.get('schema6_capable') is not True or not text(h.get('name')) for h in approval['hosts'])):
            fail('PREPARE_REQUIRED','explicit participant and capable-host inventory required')
        if before is None:
            before_rows=candidates(req,config,impact)
        else: before_rows=before['items']
        origins = []
        commit = git(root,'rev-parse','HEAD').decode().strip()
        for name in ('verification.json','claim-review.json'):
            path = folder/name
            if not path.exists(): continue
            rel = path.relative_to(root).as_posix()
            try: oid = git(root,'rev-parse',commit+':'+rel).decode().strip(); raw = git(root,'cat-file','blob',oid)
            except ValueError: fail('PREPARE_REQUIRED','commit original records before explicit prepare')
            if raw != path.read_bytes(): fail('PREPARE_REQUIRED','uncommitted original record: '+name)
            origins.append(dict(commit=commit,path=rel,blob_oid=oid,sha256=byte_hash(raw)))
        for row in before_rows:
            last = row['history'][-1] if row['history'] else None
            if last and (last.get('status') == 'retained' or any(k in last for k in ('retention_kind','scope_ref')) or row.get('manual_scope_ref')):
                fail('SOURCE_UNSUPPORTED','active composite source: '+row['id'])
        rows = deepcopy(before_rows)
        for row in rows:
            row['history'] = []
            row['acceptance_contract']=1
        doc = dict(schema_version=6,feature_id=folder.name,items=rows,retired=[],acceptance_contract=1,
                   acceptance=dict(contract_id=str(uuid.uuid4()),generation=0,origins=origins,worlds={},events=[]))
        expected=candidates(req,config,impact)
        if {(x['source'],x['expected']) for x in rows} != {(x['source'],x['expected']) for x in expected}:
            fail('PLAN_RECONCILIATION_REQUIRED','sync original rows before prepare')
        claims = build_claims(req,impact,rows,decisions=read(folder/'decisions.json'))
        append(doc,'init',{'claims':claims,'approval':approval,'initial_world_digest':None},'explicit prepare')
        frozen = world(root,folder,doc,locked=True)
        if world(root,folder,doc,locked=True) != frozen: fail('INPUTS_MOVED','prepare inputs moved')
        ident=stamp(frozen);doc['acceptance']['worlds'][ident]=frozen
        event=doc['acceptance']['events'][0];event['payload']['initial_world_digest']=ident
        event['id']=stamp({k:v for k,v in event.items() if k!='id'})
        write(root,folder,doc,before)
    return doc


def compose_delivery(root,folder):
    view = resolve_claims(root,folder)
    guards=[]
    for name,args in [('validate-feature.py',['--stage','check',str(root),folder.name]),('audit-delivery.py',[str(root),folder.name])]:
        run=subprocess.run([sys.executable,str(Path(__file__).with_name(name)),*args],capture_output=True,text=True)
        guards.append(dict(name=name,passed=run.returncode==0,output=run.stdout+run.stderr))
    after=resolve_claims(root,folder)
    if after != view: fail('INPUTS_MOVED','delivery inputs moved during guard checks')
    last=latest_event(load(folder),'assessment')
    manifest=dict(schema_version=2,kind='acceptance_delivery_manifest',feature_id=folder.name,contract_id=view['contract_id'],generation=view['generation'],
                  world_digest=view['digest'],active_claims=active_claims(load(folder)),judgment_refs=[last['id']] if last else [],
                  required_gate_refs=view['world']['execution'],guard_results=guards,blockers=view['blockers'],
                  delivery_eligible=view['acceptance_eligible'] and all(g['passed'] for g in guards))
    manifest['blockers'] += [{'code':'REVIEW_INCOMPLETE','guard':g['name']} for g in guards if not g['passed']]
    manifest['manifest_digest']=stamp(manifest)
    return manifest


def latest_result(root, folder, row, *, doc=None, inventory=None, cache=None):
    doc = doc or load(folder)
    inventory = fact_inventory(root, doc) if inventory is None else inventory
    cache = {} if cache is None else cache
    if row['mode']=='automatic':
        from check_runs import view
        checked=view(root,folder.name)
        if checked['state']!='current': return {}
        report=checked['report']
        return {'status':'passed','tested_revision':report['project_snapshot']['git_head'],'at':report['tested_at'],'method':'automatic check attempt','actual':json.dumps(report['results'],ensure_ascii=False),'evidence':checked['report_ref']}
    entries = _latest_facts({'facts':inventory}, row['source'])
    if not entries: return {}
    ref = entries[-1][1]['ref']
    if ref['container'] == 'origin_git':
        ident=stamp(ref['origin'])
        if ident not in cache: cache[ident]=original(root,ref['origin'])
        return pointer(cache[ident],ref['pointer'])
    return pointer(doc,ref['pointer'])


def negative_for_test(root, folder, test_id):
    # A shared FIX writer may already own the execution lock. This adapter reads
    # immutable facts and latest judgments without recursively acquiring it, and
    # does not erase a negative merely because applicability needs review.
    doc=load(folder);inventory=fact_inventory(root,doc);judgments=_judgments(doc)
    locators={r['source'] for r in doc['items'] if test_id in r.get('test_ids',[])}
    for locator in locators:
        entries=_latest_facts({'facts':inventory},locator)
        if entries and entries[-1][1]['fact']['status'] in ('failed','unavailable'):return True
    return any(c['locator'] in locators and judgments.get(c['claim_key'],{}).get('verdict') in ('partial','unknown') for c in active_claims(doc))


def project_views(root,folder):
    """Optional rebuildable projections; failure never re-executes checks."""
    from check_runs import save
    view = resolve_claims(root,folder); doc=load(folder)
    public={k:v for k,v in view.items() if k!='world'}
    public.update(schema_version=2,kind='acceptance_review_projection')
    try: save(root,folder/'claim-review.json',public)
    except OSError as exc: fail('PROJECTION_STALE',str(exc))
    lines=['# Verification checklist','','Generated acceptance v1 projection; original facts are unchanged.','']
    for row in view['items']:
        lines += ['## '+row['id'],'','```json',json.dumps(row,ensure_ascii=False,indent=2),'```','']
    try: safe(root,folder/'verification.md').write_text('\n'.join(lines))
    except OSError as exc: fail('PROJECTION_STALE',str(exc))
    return public



def restore_unstarted(root,folder,reason):
    """Explicit pre-use rollback only; never discard new facts/judgments."""
    if not text(reason): fail('DOWNGRADE_UNSAFE','explicit restoration reason required')
    with mutation(root,folder):
        doc=load(folder);events=doc['acceptance']['events']
        if len(events)!=1 or events[0]['kind']!='init': fail('DOWNGRADE_UNSAFE','new events exist; no automatic downgrade')
        if read(folder/'spec/requirements.json')['feature'].get('status')=='complete': fail('DOWNGRADE_UNSAFE','completed delivery cannot be rolled back here')
        initial=events[0]['payload']['initial_world_digest']
        if stamp(world(root,folder,doc,locked=True))!=initial: fail('DOWNGRADE_UNSAFE','controlled inputs moved')
        origins=[x for x in doc['acceptance']['origins'] if Path(x['path']).name=='verification.json']
        if len(origins)!=1: fail('DOWNGRADE_UNSAFE','no single original plan; keep pending contract')
        original(root,origins[0]);raw=git(root,'cat-file','blob',origins[0]['blob_oid'])
        import os,tempfile
        path=safe(root,folder/'verification.json')
        with tempfile.NamedTemporaryFile('wb',dir=folder,delete=False) as stream:
            name=stream.name;stream.write(raw);stream.flush();os.fsync(stream.fileno())
        try:
            if read(path)!=doc: fail('INPUTS_MOVED','plan moved before restoration')
            os.replace(name,path)
        finally:
            if Path(name).exists(): Path(name).unlink()
    return parse(raw)
