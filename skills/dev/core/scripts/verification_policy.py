#!/usr/bin/env python3
"""Bounded change intake and executable verification-scope/policy checks.

Evidence strings are review attestations, never proof of semantic completeness.
No test execution, automatic approvals, implicit migration or historical passes.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
from pathlib import Path
import re
import sys

from check_runs import safe, read
from impact import digest, git, path_name, snapshot


def need(condition, message):
    if not condition:
        raise ValueError('VERIFICATION_POLICY: ' + message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value, *, nonempty=False):
    return (isinstance(value, list) and (bool(value) or not nonempty)
            and all(text(x) for x in value) and len(value) == len(set(value)))


def full_revision(root, value):
    need(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', value), 'full commit required')
    need(git(root, 'rev-parse', value + '^{commit}').decode().strip() == value, 'commit identity mismatch')
    git(root, 'merge-base', '--is-ancestor', value, 'HEAD')
    return value


def project_changes(root, base, target='HEAD'):
    raw = git(root, 'diff', '--name-only', '--no-renames', '-z', base, target, '--')
    return sorted(p for p in raw.decode().split('\0') if p and not p.startswith('.agent-workflow/'))



def parent_findings(root, parent_id, record_revision, *, match_worktree=False):
    """Carry visible negatives as review obligations, not as copied observations."""
    result = []
    for name in ('verification.json','fixes.json','claim-review.json'):
        rel = '.agent-workflow/features/' + parent_id + '/' + name
        exists = bool(git(root,'ls-tree',record_revision,'--',rel))
        path = safe(root,rel)
        if not exists:
            need(not (match_worktree and path.exists()), 'commit parent findings before follow-up')
            continue
        raw = git(root,'show',record_revision+':'+rel)
        if match_worktree: need(path.is_file() and path.read_bytes()==raw, 'commit parent findings before follow-up')
        doc = json.loads(raw); found = []
        if name == 'verification.json':
            for section in ('items','retired'):
                for i,row in enumerate(doc.get(section,[])):
                    history=row.get('history',[])
                    if history and history[-1].get('status') in ('failed','unavailable'):
                        found.append(('/'+section+'/'+str(i)+'/history/'+str(len(history)-1),history[-1]['status']))
            if doc.get('acceptance_contract') is not None:
                from acceptance_contract import validate_document, _judgments, retired_blockers
                validate_document(doc)
                for key,judgment in _judgments(doc).items():
                    if judgment.get('verdict') not in ('supported','approved_waiver'):
                        found.append(('claim:'+key,judgment.get('verdict','unknown')))
                for key in retired_blockers(doc): found.append(('retired-barrier:'+str(key),'unknown'))
        elif name == 'fixes.json':
            for i,fix in enumerate(doc.get('fixes',[])):
                if fix.get('status') not in ('verified','closed'): found.append(('/fixes/'+str(i),fix.get('status','unknown')))
        else:
            for i,finding in enumerate(doc.get('findings',[])):
                if finding.get('verdict') not in ('supported','approved_waiver'):
                    found.append(('/findings/'+str(i),finding.get('verdict','unknown')))
        for locator,status in found:
            result.append(dict(id=rel+'#'+locator,status=status,record_sha256=hashlib.sha256(raw).hexdigest()))
    return result


def followup_context(root, parent_id, delivered, evidence):
    """Capture a committed complete parent without copying its acceptance matrix."""
    need(isinstance(parent_id, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', parent_id), 'parent ID required')
    need(text(evidence), 'delivered-revision evidence required; HEAD is not a delivery inference')
    delivered = full_revision(root, delivered)
    path = safe(root, '.agent-workflow/features/' + parent_id + '/spec/requirements.json')
    doc = read(root, path)
    need(doc.get('feature', {}).get('id') == parent_id and doc['feature'].get('status') == 'complete', 'parent must have a complete delivery')
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    rel = path.relative_to(Path(root).resolve()).as_posix()
    try: raw = git(root, 'show', head + ':' + rel)
    except ValueError: raise ValueError('VERIFICATION_POLICY: commit the parent delivery record before follow-up')
    need(raw == path.read_bytes(), 'commit the parent delivery record before follow-up')
    deliveries = doc['feature'].get('baseline', {}).get('deliveries', [])
    if deliveries:
        need(deliveries[-1].get('code_revision') == delivered, 'use the latest registered parent delivery')
    return dict(schema_version=1, parent_id=parent_id, parent_record_revision=head,
                parent_record_path=rel, parent_record_sha256=hashlib.sha256(raw).hexdigest(),
                delivered_revision=delivered, delivery_evidence=evidence,
                scope_base_revision=head, background_paths=project_changes(root, delivered, head),
                parent_findings=parent_findings(root,parent_id,head,match_worktree=True))


def validate_followup(root, context):
    fields = {'schema_version','parent_id','parent_record_revision','parent_record_path','parent_record_sha256',
              'delivered_revision','delivery_evidence','scope_base_revision','background_paths','parent_findings'}
    need(isinstance(context, dict) and set(context) == fields and type(context['schema_version']) is int and context['schema_version'] == 1, 'unsupported follow-up context')
    for name in ('parent_record_revision','delivered_revision','scope_base_revision'):
        full_revision(root, context[name])
    need(context['scope_base_revision'] == context['parent_record_revision'], 'follow-up baseline differs from captured parent context')
    expected = '.agent-workflow/features/' + context['parent_id'] + '/spec/requirements.json'
    need(context['parent_record_path'] == expected and text(context['delivery_evidence']), 'invalid parent locator')
    safe(root, expected)
    raw = git(root, 'show', context['parent_record_revision'] + ':' + expected)
    parent = json.loads(raw)
    need(hashlib.sha256(raw).hexdigest() == context['parent_record_sha256'] and parent['feature']['status'] == 'complete', 'parent original changed or not complete')
    need(parent['feature']['id'] == context['parent_id'], 'parent identity mismatch')
    need(context['parent_findings'] == parent_findings(root,context['parent_id'],context['parent_record_revision']), 'parent negative inventory changed')
    need(context['background_paths'] == project_changes(root, context['delivered_revision'], context['scope_base_revision']), 'background inventory changed')


def applicable(rule, paths, operation, environment):
    scope = rule['scope']
    return (operation in scope['operations'] and scope['environment'] in ('any', environment)
            and any(fnmatch.fnmatchcase(p, pattern) for p in paths for pattern in scope['paths']))


def policy_view(root, paths, operation='test', environment='test', catalog=None):
    """Read only applicable policy rows in the existing candidate catalog.

    Source files and enforced resolutions are attestations inspected by the Agent;
    a resolution never disables hooks or grants host permissions.
    """
    file = safe(root, '.agent-workflow/project-baseline/quality-candidates.json')
    if catalog is None: catalog = read(root, file) if file.exists() else {}
    contract = catalog.get('policy_contract')
    if contract is None:
        return dict(state='unprepared', rules=[], digest=None, blockers=[])
    need(isinstance(contract, dict) and set(contract) == {'schema_version','rules'} and type(contract['schema_version']) is int and contract['schema_version'] == 1, 'unsupported project policy')
    need(isinstance(contract['rules'], list), 'rules must be a list')
    ids = set(); active = []; blockers = []
    for rule in contract['rules']:
        required = {'id','source','scope','kind','disposition','reason','authority','enforced','reconciled','gate_names','permission'}
        need(isinstance(rule, dict) and set(rule) == required, 'unknown policy fields')
        need(text(rule['id']) and rule['id'] not in ids, 'duplicate policy rule'); ids.add(rule['id'])
        scope = rule['scope']
        need(isinstance(scope, dict) and set(scope) == {'paths','operations','environment'} and strings(scope['paths'], nonempty=True) and strings(scope['operations'], nonempty=True) and scope['environment'] in ('any','test','production','local'), 'invalid rule scope')
        need(set(scope['operations']) <= {'test','build','commit','device','configure'}, 'unknown rule operation')
        for pattern in scope['paths']:
            need(not pattern.startswith('/') and '..' not in Path(pattern).parts and '\\' not in pattern, 'unsafe rule scope')
        need(rule['kind'] in ('standard','workflow','execution','gate') and rule['disposition'] in ('follow','merge','replace','not_applicable','pending'), 'invalid policy disposition')
        need(text(rule['reason']) and type(rule['enforced']) is bool and type(rule['reconciled']) is bool and strings(rule['gate_names']), 'invalid policy explanation')
        need(rule['permission'] in ('allowed','denied','ask','not_applicable'), 'invalid operation permission')
        source = rule['source']
        need(isinstance(source, dict) and set(source) == {'path','sha256'} and isinstance(source['sha256'], str) and re.fullmatch('[a-f0-9]{64}', source['sha256']), 'rule source hash required')
        source_path = safe(root, source['path'])
        if not applicable(rule, paths, operation, environment):
            continue
        if not source_path.is_file() or hashlib.sha256(source_path.read_bytes()).hexdigest() != source['sha256']:
            blockers.append(rule['id'] + ': source changed/unavailable; review this rule')
        if rule['disposition'] == 'pending': blockers.append(rule['id'] + ': unresolved policy')
        if rule['disposition'] != 'follow' and not text(rule['authority']): blockers.append(rule['id'] + ': resolution authority required')
        if rule['enforced'] and rule['disposition'] in ('merge','replace','not_applicable') and not rule['reconciled']:
            blockers.append(rule['id'] + ': enforced constraint not reconciled')
        if rule['permission'] in ('denied','ask') and rule['disposition'] == 'follow':
            blockers.append(rule['id'] + ': operation permission ' + rule['permission'])
        active.append(deepcopy(rule))
    return dict(state='reviewed' if not blockers else 'blocked', rules=active, digest=digest(active), blockers=blockers)


def combined_policy(root, paths, operations, environment):
    need(strings(operations, nonempty=True) and set(operations) <= {'test','build','commit','device','configure'}, 'explicit execution operations required')
    views = {op: policy_view(root,paths,op,environment) for op in sorted(operations)}
    rules = {r['id']: r for v in views.values() for r in v['rules']}
    return dict(state='unprepared' if any(v['state']=='unprepared' for v in views.values()) else 'reviewed',
                rules=list(rules.values()), blockers=[b for v in views.values() for b in v['blockers']],
                digest=digest({op: v['digest'] for op,v in views.items()}))


def validate_plan(root, folder, req, impact, config=None, stage='check'):
    """Validate declared scope/coverage; cannot prove dependency completeness."""
    marker = req.get('feature', {}).get('verification_policy')
    plan = impact.get('verification_plan')
    if marker is None and plan is None:
        return None
    need(type(marker) is int and marker in (1, 2), 'explicit supported verification_policy required')
    # Mode 2 only changes planning/route selection, never legacy evidence rules.
    verification_file = folder / 'verification.json'
    if marker == 2 and verification_file.exists():
        existing = read(root, verification_file)
        need(existing.get('schema_version', 1) not in (6, 7) and existing.get('acceptance_contract') is None,
             'legacy planning cannot downgrade an acceptance contract')
    fields = {'schema_version','environment','operations','units','checks','interactions','background','prior_findings','gate_map','overlap_reasons','policy_digest'}
    need(isinstance(plan, dict) and set(plan) == fields and type(plan['schema_version']) is int and plan['schema_version'] == 1, 'verification plan missing/unsupported')
    need(plan['environment'] in ('test','local','production'), 'explicit verification environment required')
    need(isinstance(plan['units'], list) and plan['units'] and isinstance(plan['checks'], list), 'units and checks required')
    claims = {r['id'] + ':' + str(i + 1) for r in req.get('requirements', []) if r.get('status') != 'deprecated' for i, _ in enumerate(r.get('acceptance_criteria', []))}
    claims |= {b['id'] for b in impact.get('behaviors', [])}
    units = {}; unit_paths = set(); unresolved = []
    for u in plan['units']:
        need(isinstance(u, dict) and set(u) == {'id','category','paths','claims','sharing','effects','reason','evidence','tags'}, 'invalid unit fields')
        need(text(u['id']) and u['id'] not in units and u['category'] in ('A','B','C','D','E','U'), 'invalid unit identity/category')
        for name in ('paths','claims','effects','tags'):
            need(strings(u[name], nonempty=name in ('paths','claims')), 'invalid unit ' + name)
        need(set(u['claims']) <= claims, 'unit references unknown claim')
        for p in u['paths']: path_name(p)
        need(u['sharing'] in ('local','shared','unknown') and text(u['reason']) and text(u['evidence']), 'classification evidence and sharing required')
        effects = set(u['effects'])
        need(effects <= {'presentation','interaction','state','data','navigation','shared_behavior','contract','build','acceptance'}, 'unknown effect')
        need(set(u['tags']) <= {'funds','security','permission','privacy','language','font','accessibility','device','compatibility','migration'}, 'unknown risk tag')
        if u['category'] == 'A': need(not effects, 'non-runtime unit has runtime/acceptance effects')
        if u['category'] in ('B','C'): need(effects == {'presentation'}, 'presentation category cannot hide behavioral effects')
        if u['category'] == 'B': need(u['sharing'] == 'local', 'local display cannot hide shared/unknown use')
        if u['category'] == 'C': need(u['sharing'] == 'shared', 'shared display needs shared-use evidence')
        if u['category'] == 'D': need(not effects & {'shared_behavior','contract'} and u['sharing'] == 'local', 'cross-boundary behavior requires E')
        if u['category'] == 'U' or u['sharing'] == 'unknown': unresolved.append(u['id'])
        units[u['id']] = u; unit_paths.update(u['paths'])
    need(strings(plan['operations'], nonempty=True), 'execution operations required')
    checks = {}
    kinds = {'static','resource','build','display','behavior','integration','accessibility','compatibility'}
    for c in plan['checks']:
        need(isinstance(c, dict) and set(c) == {'id','units','claims','kind','reason','source'}, 'invalid check fields')
        need(text(c['id']) and c['id'] not in checks and strings(c['units'], nonempty=True) and set(c['units']) <= set(units), 'duplicate/unknown check units')
        need(strings(c['claims'], nonempty=True) and set(c['claims']) <= set().union(*(set(units[u]['claims']) for u in c['units'])), 'check claims outside declared units')
        need(c['kind'] in kinds and text(c['reason']) and text(c['source']), 'check needs kind, causal reason and source')
        if c['kind'] in ('behavior','integration') and all(units[u]['category'] in ('A','B','C') for u in c['units']):
            need(c['source'].startswith('policy:'), 'pure presentation business check needs an applicable project-rule basis or a behavior unit')
        if c['kind'] == 'build': need('build' in plan['operations'], 'build check cannot omit build operation constraints')
        checks[c['id']] = c
    for u in units.values():
        linked = [c for c in checks.values() if u['id'] in c['units']]
        need(linked or u['category'] == 'U', 'unit lacks targeted checks: ' + u['id'])
        kinds_for = {c['kind'] for c in linked}
        if u['category'] in ('B','C'): need('display' in kinds_for, 'display change needs target display verification')
        if u['category'] in ('D','E'): need(bool(kinds_for & {'behavior','integration'}), 'behavior change needs behavior verification')
        if u['category'] != 'U': need(set(u['claims']) <= set().union(*(set(c['claims']) for c in linked)), 'unit claim omitted from checks')
    need(isinstance(plan['interactions'], list), 'interactions must be a list')
    pairs = set()
    for relation in plan['interactions']:
        need(isinstance(relation, dict) and set(relation) == {'units','effect','check_ids','evidence'}, 'invalid interaction')
        ids = relation['units']
        need(strings(ids, nonempty=True) and len(ids) == 2 and set(ids) <= set(units), 'interaction needs two known units')
        pair = tuple(sorted(ids)); need(pair not in pairs, 'duplicate interaction'); pairs.add(pair)
        need(relation['effect'] in ('independent','interacting','unknown') and text(relation['evidence']) and strings(relation['check_ids']) and set(relation['check_ids']) <= set(checks), 'invalid interaction evidence')
        if relation['effect'] == 'unknown': unresolved.append('interaction:' + '/'.join(ids))
        if relation['effect'] == 'interacting':
            need(any(set(ids) <= set(checks[c]['units']) for c in relation['check_ids']), 'interaction lacks a combined check')
    ordered = list(units.values())
    for i, u in enumerate(ordered):
        for other in ordered[i + 1:]:
            if set(u['paths']) & set(other['paths']) or set(u['claims']) & set(other['claims']):
                need(tuple(sorted((u['id'],other['id']))) in pairs, 'overlapping units need interaction assessment')
    context = req['feature'].get('change_context')
    background_paths = set()
    if context:
        validate_followup(root, context); background_paths = set(context['background_paths'])
        need(impact.get('base_revision') == context['scope_base_revision'], 'separate new work from historical merge baseline')
    need(isinstance(plan['background'], list), 'background must be a list')
    classified = set()
    for group in plan['background']:
        need(isinstance(group, dict) and set(group) == {'paths','effect','claims','evidence'}, 'invalid background group')
        need(strings(group['paths'], nonempty=True) and set(group['paths']) <= background_paths and not classified & set(group['paths']), 'background paths duplicated or unknown')
        need(group['effect'] in ('unaffected','affected','unknown') and strings(group['claims']) and set(group['claims']) <= claims and text(group['evidence']), 'background review evidence required')
        if group['effect'] == 'affected': need(group['claims'] and set(group['claims']) <= set().union(*(set(u['claims']) for u in units.values())), 'affected background needs current regression claims')
        if group['effect'] == 'unknown': unresolved.append('background:' + group['paths'][0])
        classified.update(group['paths'])
    need(classified == background_paths, 'classify all background changes once, separately from new work')
    need(isinstance(plan['prior_findings'],list), 'prior finding review must be explicit')
    known_findings = {x['id'] for x in context.get('parent_findings',[])} if context else set()
    handled = set()
    for finding in plan['prior_findings']:
        need(isinstance(finding,dict) and set(finding)=={'id','effect','claims','evidence'}, 'invalid prior finding review')
        need(finding['id'] in known_findings and finding['id'] not in handled and finding['effect'] in ('unaffected','covered','unknown') and strings(finding['claims']) and set(finding['claims']) <= claims and text(finding['evidence']), 'invalid/duplicate prior finding')
        if finding['effect']=='covered': need(finding['claims'] and set(finding['claims']) <= set().union(*(set(u['claims']) for u in units.values())), 'related prior negative requires current regression claims')
        if finding['effect']=='unknown': unresolved.append('prior finding:'+finding['id'])
        handled.add(finding['id'])
    need(handled==known_findings, 'do not escape prior failures or open fixes through a new work ID')

    current = snapshot(root, impact)
    excluded = set(impact.get('excluded_changes', {}))
    need(set(current['changed_paths']) <= unit_paths | excluded, 'new changed path has no classified unit')
    policy = combined_policy(root, sorted(unit_paths), plan['operations'], plan['environment'])
    need(policy['state'] != 'unprepared' and plan['policy_digest'] == policy['digest'], 'project constraints unreviewed/stale for this scope')
    need(not policy['blockers'], '; '.join(policy['blockers']))
    for check in checks.values():
        if check['source'].startswith('policy:'):
            rule_id = check['source'][len('policy:'):]
            need(any(r['id']==rule_id and r['disposition'] in ('follow','merge') for r in policy['rules']), 'check cites no applicable effective rule')
    if stage != 'draft': need(not unresolved, 'unknown impact requires investigation: ' + ', '.join(unresolved))
    need(isinstance(plan['gate_map'], dict) and isinstance(plan['overlap_reasons'], dict), 'gate mapping required')
    for name, ids in plan['gate_map'].items(): need(text(name) and strings(ids, nonempty=True) and set(ids) <= set(checks), 'gate maps unknown check')
    for name, reason in plan['overlap_reasons'].items(): need(text(name) and text(reason), 'overlap reason required')
    if config is not None:
        gates = config['gates']; names = {g['name'] for g in gates}
        need(set(plan['gate_map']) == names, 'map exactly selected gates; do not inherit an unrelated suite')
        mandatory = set()
        for rule in policy['rules']:
            if rule['disposition'] in ('follow','merge'):
                mandatory.update(rule['gate_names'])
                need(set(rule['gate_names']) <= names, 'mandatory project gate missing: ' + rule['id'])
        for i, gate in enumerate(gates):
            for other in gates[i + 1:]:
                overlap = set(plan['gate_map'][gate['name']]) & set(plan['gate_map'][other['name']])
                same = (gate['command'],gate.get('cwd','.')) == (other['command'],other.get('cwd','.'))
                key = '|'.join(sorted((gate['name'], other['name'])))
                need(not same, 'duplicate physical command must be executed once: ' + key)
                if overlap:
                    need({gate['name'],other['name']} <= mandatory and text(plan['overlap_reasons'].get(key)), 'duplicate/bundled checks need an unavoidable project obligation: ' + key)
    return dict(categories=sorted({u['category'] for u in units.values()}), units=len(units), checks=len(checks),
                background_paths=len(background_paths), unresolved=unresolved, policy_digest=policy['digest'],
                complete_claim_review='all active claims partitioned; deep assessment only for affected/unknown/new claims; reuse requires evidence')


def enforce_selection(root, feature_id, config):
    folder = safe(root, '.agent-workflow/features/' + feature_id)
    path = folder / 'spec/requirements.json'
    if not path.exists(): return  # Legacy configuration-only checks have no feature contract.
    req = read(root, path)
    if req['feature'].get('verification_policy') is None:
        return
    impact = read(root, folder / 'impact.json')
    validate_plan(root, folder, req, impact, config)


def delivery_readiness(root, feature_id, requested_route=None, parent_id=None):
    """Read-only structural readiness, never approval or semantic certification.

    Supports prospective intake without creating a feature. This inventories the
    project-wide switch rather than promising a feature-local migration.
    """
    need(isinstance(feature_id,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*',feature_id), 'valid feature ID required')
    need(requested_route in (None, 'legacy', 'scoped'), 'unknown requested verification route')
    root = Path(root).resolve()
    folder = safe(root, '.agent-workflow/features/' + feature_id)
    req_path = folder / 'spec/requirements.json'
    req = read(root, req_path) if req_path.exists() else {'feature': {}}
    feature = req['feature']; marker = feature.get('verification_policy')
    need(marker is None or type(marker) is int and marker in (1,2), 'unsupported verification policy')
    path = folder / 'verification.json'; doc = read(root,path) if path.exists() else {}
    schema = doc.get('schema_version',1)
    existing_route = 'scoped' if marker == 1 or schema == 7 else ('acceptance_v1' if schema == 6 else 'legacy')
    if req_path.exists() and requested_route is not None:
        need(requested_route == existing_route, 'existing route cannot be changed by readiness inspection')
    route = existing_route if req_path.exists() else requested_route
    base = root / '.agent-workflow/project-baseline'
    config_path = base / 'quality-gates.json'
    config = read(root,config_path) if config_path.exists() else {}
    from check_runs import enabled as execution_enabled
    execution = 2 if config_path.exists() and execution_enabled(root) else 1
    participants = []
    feature_root = folder.parent
    inventory_needed = route == 'scoped' and (schema != 7 or doc.get('acceptance_contract') != 1)
    if inventory_needed and feature_root.exists():
        for candidate in sorted(feature_root.iterdir()):
            path = candidate / 'spec/requirements.json'
            if path.is_file() and read(root,path)['feature'].get('status') != 'complete':
                participants.append(candidate.name)
    missing = []; unknown = []; originals = []
    ready = route is not None
    if route is None: missing.append('explicit_route_selection'); ready = False
    if not config_path.exists(): missing.append('check_definitions'); ready = False
    if execution == 2 and req_path.exists() and not (folder/'check-selection.json').exists():
        missing.append('feature_check_selection'); ready = False
    if route == 'scoped':
        if execution != 2: missing.append('project_execution_contract2'); ready = False
        if schema != 7 or doc.get('acceptance_contract') != 1:
            missing.append('explicit_schema7_preparation'); ready = False
            # Preparation uses committed originals. Do not silently commit them.
            for name in ('verification.json','claim-review.json'):
                path = folder / name
                if not path.exists(): continue
                try:
                    raw = git(root,'show','HEAD:'+path.relative_to(root).as_posix())
                    state = 'committed' if raw == path.read_bytes() else 'uncommitted'
                except ValueError: state = 'uncommitted'
                originals.append(dict(path=name,state=state))
                if state != 'committed': missing.append('commit_original:'+name)
            if any(row.get('manual_scope_ref') or (row.get('history') and
                    (row['history'][-1].get('status') == 'retained' or
                     any(k in row['history'][-1] for k in ('retention_kind','scope_ref')))) for row in doc.get('items',[])):
                missing.append('unsupported_composite_originals')
            unknown.extend(['participating_host_capabilities','preparation_authority'])
    if schema in (6,7):
        from acceptance_contract import validate_document
        try: validate_document(doc)
        except (ValueError,KeyError,TypeError) as exc:
            missing.append('invalid_acceptance_document:'+str(exc)); ready = False
    if route == 'legacy' and schema in (6,7):
        missing.append('existing_acceptance_contract_no_downgrade'); ready = False
    if req_path.exists() and route is not None:
        from check_runs import selection
        try: selection(root,feature_id)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            missing.append('selection_or_effect_plan:'+str(exc)); ready = False
    pending_switch = route == 'scoped' and execution != 2
    return dict(route=route, relationship='linked' if feature.get('change_context') or parent_id else 'standalone',
                feature_exists=req_path.exists(),
                state=('route_available_for_intake' if not req_path.exists() else 'structurally_ready') if ready and not unknown else 'preparation_required',
                verification_schema=schema, execution_contract=execution,
                missing=missing, unknown=unknown, original_records=originals,
                project_switch=dict(required=pending_switch, scope='project-wide' if pending_switch else 'none',
                    inventory_state='inspected' if inventory_needed else 'not_applicable_to_current_route',
                    active_features=participants,
                    missing_selections=[x for x in participants if not (feature_root/x/'check-selection.json').exists()] if route == 'scoped' else []),
                execution_entry='verification.py run <PROJECT> <ID>',
                direct_check_result='diagnostic_only_no_legacy_adoption' if execution == 1 else 'recorded_attempt_requires_claim_mapping',
                limitation='Legacy routes keep global stamps/full current-work review; no schema7 reuse promise.' if route == 'legacy' else ('Existing schema6 acceptance remains on its own contract; inspection does not migrate it.' if route == 'acceptance_v1' else 'Schema7 requires explicit project/host preparation; no legacy final-pass fallback.'),
                automatic_preparation=False, semantic_acceptance=False)


def require_execution_route(root, feature_id):
    """Refuse known unprepared scoped final-gate runs before side effects.

    Focused development diagnostics remain possible through project tools; they
    are not promised acceptance credit. No migration or approval is performed.
    """
    folder = safe(root, '.agent-workflow/features/' + feature_id)
    path = folder/'spec/requirements.json'
    if not path.exists(): return
    feature = read(root,path)['feature']
    if feature.get('verification_policy') != 1: return
    plan_path = folder/'verification.json'
    doc = read(root,plan_path) if plan_path.exists() else {}
    from check_runs import enabled as execution_enabled
    need(doc.get('schema_version') == 7 and doc.get('acceptance_contract') == 1 and execution_enabled(root),
         'DELIVERY_PREPARE_REQUIRED: explicit schema7 scoped route is not prepared; inspect readiness before final-gate execution; diagnostics grant no acceptance credit')
    from acceptance_contract import validate_document
    validate_document(doc)
    need(doc.get('feature_id') == feature_id, 'prepared contract belongs to another feature')


def entry_status(root, feature_id):
    folder = safe(root, '.agent-workflow/features/' + feature_id)
    req = read(root, folder / 'spec/requirements.json'); plan_path = folder / 'verification.json'
    plan = read(root, plan_path) if plan_path.exists() else {}
    schema = plan.get('schema_version', 1)
    if req['feature'].get('status') == 'complete': route = 'historical_delivery_or_explicit_followup'
    elif schema in (6,7): route = 'acceptance_v1_scoped' if schema == 7 else 'acceptance_v1'
    elif req['feature'].get('verification_policy') == 2: route = 'legacy_effect_planning_no_scoped_acceptance'
    elif any(r.get('manual_scope_ref') or (r.get('history') and r['history'][-1].get('status') == 'retained') for r in plan.get('items',[])): route = 'legacy_composite_sources_need_review_not_force_migration'
    else: route = 'evaluate_acceptance_v1_prerequisites_before_offering_legacy_batch'
    return dict(readiness=delivery_readiness(root, feature_id), feature_id=feature_id, installed_version_is_not_contract=True, verification_schema=schema,
                execution_contract=read(root, '.agent-workflow/project-baseline/quality-gates.json').get('execution_contract',1),
                route=route, manual_scope_contract=plan.get('manual_scope_contract'), verification_policy=req['feature'].get('verification_policy'), automatic_preparation=False)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('root', type=Path); p.add_argument('feature_id')
    p.add_argument('--inspect-route', choices=('legacy','scoped'), help='Read-only prospective or existing route inspection')
    p.add_argument('--parent', help='Prospective parent trace only; does not enable a contract')
    p.add_argument('--operation', choices=('test','build','commit','device','configure'))
    p.add_argument('--path', action='append', default=[])
    p.add_argument('--environment', choices=('test','local','production'), default='test')
    args = p.parse_args(); root = args.root.resolve()
    if args.inspect_route:
        print(json.dumps(delivery_readiness(root,args.feature_id,args.inspect_route,args.parent), ensure_ascii=False, indent=2)); return 0
    result = entry_status(root,args.feature_id)
    if args.operation:
        need(bool(args.path), 'operation inspection needs explicit paths')
        for path in args.path: path_name(path)
        result['operation_policy'] = policy_view(root,args.path,args.operation,args.environment)
    folder = safe(root,'.agent-workflow/features/' + args.feature_id)
    impact = folder/'impact.json'
    if impact.exists():
        result['scope'] = validate_plan(root,folder,read(root,folder/'spec/requirements.json'),read(root,impact),stage='draft')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    try: sys.exit(main())
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(str(exc),file=sys.stderr);sys.exit(2)
