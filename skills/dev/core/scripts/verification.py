#!/usr/bin/env python3
"""Generate acceptance rows, run configured checks, and retain revision-bound results."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import os
import hashlib
from functools import wraps

from impact import digest, git, snapshot as impact_snapshot, validate_impact
from project import validate_gates


def read(path):
    from acceptance_contract import parse
    return parse(path.read_bytes())


def save(path, doc):
    if path.is_symlink():
        raise ValueError('refusing symlink record')
    with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False) as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(f.name, path)


def plan_mutation(function):
    """Serialize helper-authored result mutations; refuse rather than wait on a busy plan."""
    @wraps(function)
    def wrapped(root, folder, *args, **kwargs):
        path = folder / 'verification.json'
        if path.exists():
            from acceptance_contract import enabled
            if enabled(read(path)):
                if function.__module__ == __name__ and function.__name__ in ('sync','run','record','retain'):
                    return function(root, folder, *args, **kwargs)  # explicit new routes own locks
                from acceptance_contract import mutation
                with mutation(root,folder):
                    return function(root,folder,*args,**kwargs)
        scratch = root / '.agent-workflow/scratch'
        if scratch.is_symlink() or (root / '.agent-workflow').is_symlink():
            raise ValueError('unsafe verification lock location')
        scratch.mkdir(exist_ok=True)
        lock = scratch / ('verification-' + folder.name + '.lock')
        if lock.is_symlink():
            raise ValueError('unsafe verification lock')
        with lock.open('a') as stream:
            try:
                if os.name == 'nt':
                    import msvcrt
                    stream.seek(0); stream.write('0'); stream.flush(); stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise ValueError('verification plan busy; preserve input and retry after active operation') from exc
            return function(root, folder, *args, **kwargs)
    return wrapped


def sources(root, folder):
    req = read(folder / 'spec/requirements.json')
    config_path = root / '.agent-workflow/project-baseline/quality-gates.json'
    config = read(config_path) if config_path.exists() else {'gates': []}
    from check_runs import enabled, selection
    if config_path.exists() and enabled(root): config = selection(root, folder.name)
    validate_gates(root.resolve(), config)
    if config['gates'] and config.get('selection_feature_id') != folder.name:
        raise ValueError('quality gate selection belongs to another feature or is unbound; select gates for ' + folder.name + ' before verification')
    impact = read(folder / 'impact.json')
    errors, _ = validate_impact(root, folder, req, 'develop')
    if errors:
        raise ValueError('; '.join(errors))
    return req, config, impact


def candidates(req, config, impact):
    rows = []
    def add(source, expected, mode, gates):
        rows.append({'id': source + ':' + digest(expected)[:12], 'source': source,
                     'expected': expected, 'mode': mode, 'gates': gates,
                     'coverage': 'configured command result only' if mode == 'automatic' else '',
                     'history': []})
    for r in req['requirements']:
        if r.get('status') != 'deprecated':
            for index, ac in enumerate(r.get('acceptance_criteria', [])):
                add('requirement:' + r['id'] + ':' + str(index + 1), ac, 'manual', [])
    for b in impact['behaviors']:
        add('impact:' + b['id'], b['statement'], 'manual', [])
    for gate in config['gates']:
        add('gate:' + gate['name'], gate.get('purpose') or ('Command succeeds: ' + gate['name']), 'automatic', [gate['name']])
    if not config['gates']:
        add('system:no-gates', 'Select applicable quality checks; no commands configured', 'manual', [])
    return rows


def load_plan(folder):
    doc = read(folder / 'verification.json')
    from acceptance_contract import enabled, validate_document
    if enabled(doc):
        validate_document(doc)
        if doc['feature_id'] != folder.name: raise ValueError('CONTRACT_UNSUPPORTED: feature mismatch')
        return doc
    if not isinstance(doc, dict) or doc.get('schema_version') not in (1, 2, 3, 4, 5) or doc.get('feature_id') != folder.name or not isinstance(doc.get('items'), list) or not isinstance(doc.get('retired'), list):
        raise ValueError('invalid verification identity/schema')
    if doc.get('schema_version') == 4 and doc.get('execution_contract') != 2:
        raise ValueError('schema 4 requires explicit check attempts')
    if doc.get('schema_version') == 5:
        from manual_scope import validate_document
        validate_document(doc)
    elif 'manual_scope_contract' in doc or 'manual_scope_reviews' in doc or any('manual_scope_ref' in r for r in doc['items'] + doc['retired']):
        raise ValueError('manual scope fields require schema 5 readers')
    if 'annotation_reviews' in doc:
        from evidence_annotations import validated_reviews
        validated_reviews(doc)
    ids = set()
    for item in doc['items']:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or item['id'] in ids:
            raise ValueError('invalid/duplicate verification ID')
        ids.add(item['id'])
        if item.get('mode') not in ('manual', 'automatic') or not isinstance(item.get('gates'), list) or not all(isinstance(g, str) and g for g in item['gates']) or not isinstance(item.get('history'), list):
            raise ValueError('invalid verification item')
        if item['mode'] == 'automatic' and (not item['gates'] or not isinstance(item.get('coverage'), str) or not item['coverage'].strip()):
            raise ValueError('automatic mapping requires gates and coverage rationale')
        if item['mode'] == 'manual' and item['gates']:
            raise ValueError('manual items cannot declare automatic gates')
        if 'dependencies' in item:
            from impact import path_name
            paths = item['dependencies']
            if not isinstance(paths, list) or not paths or len(paths) != len(set(paths)):
                raise ValueError('scoped evidence requires distinct dependency paths')
            for name in paths:
                path_name(name)
            if not isinstance(item.get('scope_reason'), str) or not item['scope_reason'].strip():
                raise ValueError('scoped dependencies require investigation rationale')
        for index, result in enumerate(item['history']):
            if not isinstance(result, dict) or result.get('status') not in ('passed', 'failed', 'unavailable', 'waived', 'retained'):
                raise ValueError('invalid verification result')
            if any(not isinstance(result.get(k), str) or not result[k].strip() for k in ('digest', 'tested_revision', 'actual', 'evidence', 'at', 'method')):
                raise ValueError('verification result lacks evidence or tested identity')
            if 'evidence_digest' in result and (not isinstance(result['evidence_digest'], str) or not result['evidence_digest']):
                raise ValueError('invalid manual evidence digest')
            if 'check_attempt' in result:
                ref = result['check_attempt']
                if (doc.get('schema_version') not in (4, 5) or doc.get('execution_contract') != 2 or item['mode'] != 'automatic'
                        or not isinstance(ref, dict) or set(ref) != {'id', 'digest'}
                        or not re.fullmatch('[0-9a-f]{32}', str(ref.get('id')))
                        or not re.fullmatch('[0-9a-f]{64}', str(ref.get('digest')))):
                    raise ValueError('invalid explicit check execution reference')
                if not item['source'].startswith('gate:') and not isinstance(result.get('mapping_review'), dict):
                    raise ValueError('automatic claim requires inspected mapping review')
            if result.get('retention_kind') == 'interpretation_adoption':
                from evidence_adoption import validate_receipt
                validate_receipt(doc, item, result)
                continue
            if result.get('retention_kind') == 'annotation_amend':
                from evidence_annotations import validate_receipt
                if result['status'] != 'retained' or item['mode'] != 'manual':
                    raise ValueError('annotation only applies to retained manual evidence')
                validate_receipt(result, item['history'][index - 1] if index else None, item, doc)
                continue
            if result.get('retention_kind') == 'reviewed_carry':
                from evidence_carry import validate_receipt
                if result['status'] != 'retained' or item['mode'] != 'manual':
                    raise ValueError('carry receipt only belongs to retained manual evidence')
                validate_receipt(result, item['history'][index - 1] if index else None, item)
                continue
            if result['status'] == 'retained' and (not isinstance(result.get('scope_files'), dict) or not isinstance(result.get('changed_paths'), list)
                                                   or not result['changed_paths'] or not all(isinstance(result.get(k), str) and result[k].strip() for k in ('reviewed_revision', 'reason', 'source_result_digest', 'semantic_digest'))):
                raise ValueError('retained evidence lacks reviewed scope and prior identity')
            if result['status'] == 'retained':
                previous = item['history'][index - 1] if index else None
                if previous is None or previous['status'] not in ('passed', 'retained') or result['source_result_digest'] != previous['digest'] or result['tested_revision'] != previous['tested_revision']:
                    raise ValueError('retained evidence lacks a matching prior pass')
    if doc.get('schema_version') == 2 and not doc.get('result_correction_reviews'):
        raise ValueError('schema 2 requires result corrections')
    if 'result_correction_reviews' in doc:
        if doc.get('schema_version') not in (2, 3, 4, 5):
            raise ValueError('result corrections require schema 2 readers')
        from result_corrections import validate_events
        validate_events(doc)
    if doc.get('schema_version') == 3 or 'adoption_reviews' in doc:
        from evidence_adoption import validate_events
        validate_events(doc)
    return doc


class PlanSyncRequired(ValueError):
    """The derived row list must be synchronized before applicability is assessed."""


def context(root, folder, doc):
    from acceptance_contract import enabled, capture_assessment
    if enabled(doc):
        request, _ = capture_assessment(root, folder, doc=doc)
        return request['world_digest'], git(root, 'rev-parse', 'HEAD').decode().strip()
    req, config, impact = sources(root, folder)
    expected = {r['id']: r for r in candidates(req, config, impact)}
    actual = {r['id']: r for r in doc['items']}
    if actual.keys() != expected.keys() or any(actual[k].get('source') != v['source'] or actual[k].get('expected') != v['expected'] for k, v in expected.items()):
        raise PlanSyncRequired('verification list is stale; run sync')
    names = {g['name'] for g in config['gates']}
    for row in doc['items']:
        if any(g not in names for g in row['gates']):
            raise ValueError('unknown mapped gate: ' + row['id'])
        if row['source'].startswith('gate:') and (row['mode'] != 'automatic' or row['gates'] != expected[row['id']]['gates']):
            raise ValueError('generated gate rows must retain their command mapping')
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    contract = [{k: v for k, v in row.items() if k not in ('history', 'manual_scope_ref')} for row in doc['items']]
    # Ignore requirement workflow status/task progress; retain semantic requirements and decisions.
    decisions_path = folder / 'decisions.json'
    stamp = digest({'requirements': req['requirements'], 'decisions': read(decisions_path),
                    'impact': impact_snapshot(root, impact)['digest'], 'config': config, 'items': contract})
    return stamp, head


def semantic_stamp(root, folder, row):
    """Meaning and execution contract, excluding mutable project file contents."""
    req, _, impact = sources(root, folder)
    contract = {k: v for k, v in row.items() if k not in ('history', 'retention', 'manual_scope_ref')}
    impact_contract = {k: v for k, v in impact.items() if k != 'behaviors'}
    impact_contract['behaviors'] = [{k: v for k, v in b.items() if k != 'verification'} for b in impact['behaviors']]
    return digest({'requirements': req['requirements'], 'decisions': read(folder / 'decisions.json'),
                   'impact_contract': impact_contract, 'item': contract})


def legacy_semantic_stamp(root, folder, row):
    """Accept existing scoped observations only against their original config."""
    req, config, impact = sources(root, folder)
    contract = {k: v for k, v in row.items() if k not in ('history', 'retention', 'manual_scope_ref')}
    impact_contract = {k: v for k, v in impact.items() if k != 'behaviors'}
    impact_contract['behaviors'] = [{k: v for k, v in b.items() if k != 'verification'} for b in impact['behaviors']]
    return digest({'requirements': req['requirements'], 'decisions': read(folder / 'decisions.json'),
                   'config': config, 'impact_contract': impact_contract, 'item': contract})


def manual_evidence_stamp(root, folder, row, *, carry_sources=None):
    """Bind a manual observation to its meaning and project scope, not gate prose."""
    req, _, impact = sources(root, folder)
    contract = {k: v for k, v in row.items() if k not in ('history', 'retention', 'manual_scope_ref')}
    content = {'requirements': req['requirements'], 'decisions': read(folder / 'decisions.json'),
               'impact': impact_snapshot(root, impact)['digest'], 'item': contract}
    if row.get('history') and row['history'][-1].get('retention_kind') in ('reviewed_carry', 'annotation_amend', 'interpretation_adoption'):
        from evidence_carry import project_files, source_identity, UncommittedBusinessChanges
        try:
            content['carry_project'] = project_files(root)
        except UncommittedBusinessChanges as exc:
            # A dirty tree cannot match a clean retained receipt, but must not
            # prevent status, ordinary checks or recording fresh test evidence.
            content['carry_project'] = {'uncommitted_business_paths': exc.paths}
        content['carry_sources'] = source_identity(root, folder) if carry_sources is None else carry_sources
        content['carry_authority'] = {name: read(folder / name) for name in ('traceability.json', 'spec/prd-intake.json')}
        if row['history'][-1].get('retention_kind') == 'interpretation_adoption':
            content['adoption_receipt'] = row['history'][-1]['adoption_receipt']
            plan = read(folder / 'verification.json')
            # During apply the event is not saved yet; the source reference is
            # supplied below through the staged row, never by loading recursively.
            ref = row['history'][-1]['adoption_source']
            content['adoption_origin_history'] = [
                [e for e in r['history'] if e.get('retention_kind') != 'interpretation_adoption']
                for r in plan['items'] + plan['retired'] if r['id'] == ref['item_id']]
    return digest(content)


def row_evidence_stamp(root, folder, row, check_view=None):
    from acceptance_contract import enabled, resolve_claims
    if check_view and '_acceptance' in check_view:
        return next(x for x in check_view['_acceptance']['items'] if x['id'] == row['id'])
    if row.get('acceptance_contract') == 1:
        return next(x for x in resolve_claims(root, folder)['items'] if x['id'] == row['id'])
    if row['mode'] == 'manual':
        if row.get('manual_scope_ref'):
            from manual_scope import view
            scoped = check_view.get('_manual_scope') if isinstance(check_view, dict) and '_manual_scope' in check_view else view(root, folder)
            item = scoped.get('items', {}).get(row['id'], {}) if scoped else {}
            return 'manual-scope:' + ('current' if item.get('state') == 'current' else 'stale')
        return manual_evidence_stamp(root, folder, row)
    from check_runs import enabled, view
    if not enabled(root): return None
    outcome = view(root, folder.name) if check_view is None else check_view
    # Execution currentness and claim currentness are separate. Other rows' mapping
    # prose is not this row's assertion, but semantic requirement changes still bind.
    if outcome['state'] != 'current': return 'check-v2:' + digest(outcome)
    return 'check-v2:' + digest({'semantic': semantic_stamp(root, folder, row),
                                 'attempt_id': outcome['attempt_id'], 'attempt_digest': outcome['digest']})


def check_currency(root, folder):
    from acceptance_contract import enabled, resolve_claims
    if enabled(load_plan(folder)): return {'_acceptance':resolve_claims(root,folder)}
    from check_runs import enabled, view
    outcome = view(root, folder.name) if enabled(root) else None
    doc = load_plan(folder)
    if doc.get('manual_scope_contract') == 1:
        from manual_scope import view as scope_view
        outcome = dict(outcome or {}, _manual_scope=scope_view(root, folder, doc))
    return outcome


def scope_files(root, folder):
    """Fingerprint every registered changed/inspected project file."""
    root = root.resolve()
    impact = read(folder / 'impact.json')
    snap = impact_snapshot(root, impact)
    names = set(snap['changed_paths']) | set(impact['inspected_paths'])
    files = {}
    for name in sorted(names):
        from impact import path_name
        path_name(name)
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('unsafe scoped evidence path: ' + name)
        files[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    return files


@plan_mutation
def sync(root, folder, resolutions=None):
    from acceptance_contract import enabled, reconcile_claims
    if (folder/'verification.json').exists() and enabled(read(folder/'verification.json')):
        return reconcile_claims(root,folder,resolutions)
    req, config, impact = sources(root, folder)
    from feature_lifecycle import require_active
    require_active(req['feature'])
    old = load_plan(folder) if (folder / 'verification.json').exists() else {'items': [], 'retired': []}
    previous = {r['id']: r for r in old['items']}
    rows = candidates(req, config, impact)
    for row in rows:
        if row['id'] in previous:
            row.update({k: previous[row['id']][k] for k in ('mode', 'gates', 'coverage', 'history')})
            for key in ('dependencies', 'scope_reason', 'manual_scope_ref'):
                if key in previous[row['id']]:
                    row[key] = previous[row['id']][key]
    active = {r['id'] for r in rows}
    doc = {'schema_version': old.get('schema_version', 1), 'feature_id': folder.name, 'items': rows,
           'retired': old['retired'] + [r for r in old['items'] if r['id'] not in active]}
    from check_runs import enabled
    if enabled(root): doc.update(schema_version=max(4, doc['schema_version']), execution_contract=2)
    if 'annotation_reviews' in old:
        doc['annotation_reviews'] = old['annotation_reviews']
    if 'result_correction_reviews' in old:
        doc['result_correction_reviews'] = old['result_correction_reviews']
    if 'adoption_reviews' in old:
        doc['adoption_reviews'] = old['adoption_reviews']
    for key in ('manual_scope_contract', 'manual_scope_reviews'):
        if key in old: doc[key] = old[key]
    save(folder / 'verification.json', doc)
    req['feature']['verification_required'] = True
    save(folder / 'spec/requirements.json', req)
    render(folder)
    return doc


def state(row, stamp, evidence_stamp=None):
    if isinstance(evidence_stamp, dict) and 'applicability' in evidence_stamp:
        return evidence_stamp['status']
    if row.get('acceptance_contract')==1:
        raise ValueError('CONTRACT_UNSUPPORTED: acceptance row requires unified resolver view')
    if not row['history']:
        return 'not_run'
    result = row['history'][-1]
    if row.get('manual_scope_ref'):
        return 'retained' if evidence_stamp == 'manual-scope:current' and result['status'] in ('passed', 'retained') else 'stale'
    if isinstance(evidence_stamp, str) and evidence_stamp.startswith('check-v2:') and 'check_attempt' not in result:
        return 'stale'
    if 'evidence_digest' in result and evidence_stamp is not None:
        return result['status'] if result['evidence_digest'] == evidence_stamp else 'stale'
    return result['status'] if result['digest'] == stamp else 'stale'


def result(status, stamp, head, actual, evidence, method, *, semantic=None, files=None):
    row = {'status': status, 'digest': stamp, 'tested_revision': head,
            'actual': actual, 'evidence': evidence, 'method': method,
            'at': datetime.now(timezone.utc).isoformat()}
    if semantic is not None:
        row['semantic_digest'] = semantic
        row['scope_files'] = files
    return row


@plan_mutation
def run(root, folder):
    doc = load_plan(folder)
    from acceptance_contract import enabled
    if enabled(doc):
        from feature_lifecycle import require_active
        require_active(read(folder/'spec/requirements.json')['feature'])
        preflight = subprocess.run([sys.executable,str(Path(__file__).with_name('validate-feature.py')),'--stage','develop',str(root),folder.name],capture_output=True,text=True)
        if preflight.returncode: raise ValueError('development eligibility failed: '+preflight.stdout+preflight.stderr)
        execution = subprocess.run([sys.executable,str(Path(__file__).with_name('project.py')),'check',str(root),'--feature',folder.name],capture_output=True,text=True)
        print(execution.stdout,end='')
        return summary(root,folder)
    stamp, head = context(root, folder, doc)
    from feature_lifecycle import require_active
    require_active(read(folder / 'spec/requirements.json')['feature'])
    preflight = subprocess.run([sys.executable, str(Path(__file__).with_name('validate-feature.py')), '--stage', 'develop', str(root), folder.name], capture_output=True, text=True)
    if preflight.returncode:
        raise ValueError('development eligibility failed before execution: ' + preflight.stdout + preflight.stderr)
    from check_runs import enabled
    if enabled(root):
        preflight = subprocess.run([sys.executable, str(Path(__file__).with_name('validate-feature.py')), '--stage', 'develop', str(root), folder.name], capture_output=True, text=True)
        if preflight.returncode: raise ValueError('development eligibility failed before execution: ' + preflight.stdout + preflight.stderr)
        execution = subprocess.run([sys.executable, str(Path(__file__).with_name('project.py')), 'check', str(root), '--feature', folder.name], capture_output=True, text=True)
        print(execution.stdout, end='')
        if execution.returncode: return summary(root, folder)
        adopt_checks(root, folder, locked=True, allow_claims=False)
        return summary(root, folder)
    report_path = root / '.agent-workflow/project-baseline/quality-report.json'
    old_bytes = report_path.read_bytes() if report_path.exists() else None
    execution = subprocess.run([sys.executable, str(Path(__file__).with_name('project.py')), 'check', str(root), '--feature', folder.name], capture_output=True, text=True)
    # A missing/newly unproduced report is unavailable, never borrow an earlier green report.
    fresh = report_path.exists() and report_path.read_bytes() != old_bytes
    report = read(report_path) if fresh else {'results': []}
    results = {r['name']: r for r in report['results']}
    after, after_head = context(root, folder, doc)
    for row in doc['items']:
        if row['mode'] != 'automatic':
            continue
        selected = [results.get(name) for name in row['gates']]
        statuses = [r['status'] if r else 'unavailable' for r in selected]
        outcome = 'failed' if 'failed' in statuses else ('unavailable' if 'unavailable' in statuses else 'passed')
        if (after, after_head) != (stamp, head):
            outcome = 'unavailable'
        if outcome == 'passed' and execution.returncode != 0:
            # A command can exit zero while the runner rejects moved/unknown
            # input identity. Do not upgrade that diagnostic to a row pass.
            outcome = 'unavailable'
        actual = json.dumps(selected, ensure_ascii=False) if fresh else (execution.stdout + execution.stderr).strip() or 'No new quality report'
        row['history'].append(result(outcome, stamp, head, actual, 'quality-report executed at ' + str(report.get('tested_at', 'unavailable')), 'automatic'))
    # Do not overwrite concurrent edits to the plan while checks were running.
    if load_plan(folder) != doc_without_new_results(doc):
        raise ValueError('verification plan changed during execution; results not applied')
    save(folder / 'verification.json', doc)
    render(folder)
    print(execution.stdout, end='')
    return summary(root, folder)


def check_mapping_snapshot(root, folder, item_ids):
    from acceptance_contract import refuse_legacy
    refuse_legacy(load_plan(folder))
    from check_runs import current
    doc = load_plan(folder); report = current(root, folder.name)
    selected = [r for r in doc['items'] if r['id'] in item_ids]
    if (not isinstance(item_ids, list) or not item_ids or len(item_ids) != len(set(item_ids))
            or len(selected) != len(item_ids) or any(r['mode'] != 'automatic' for r in selected)):
        raise ValueError('explicit distinct automatic claim targets required')
    _, head = context(root, folder, doc)
    body = {'feature_id': folder.name, 'attempt_id': report['attempt_id'], 'attempt_digest': report['attempt_digest'],
            'target_revision': head, 'items': [{k: v for k, v in row.items() if k not in ('history', 'manual_scope_ref')} for row in selected],
            'claim_stamps': {r['id']: row_evidence_stamp(root, folder, r, {'state':'current','attempt_id':report['attempt_id'],'digest':report['attempt_digest']}) for r in selected}, 'plan_digest': digest(doc)}
    body['input_digest'] = digest(body)
    return body


def adopt_checks(root, folder, *, review=None, locked=False, allow_claims=True):
    def action():
        from acceptance_contract import refuse_legacy
        refuse_legacy(load_plan(folder))
        from check_runs import current
        doc = load_plan(folder); original = read(folder / 'verification.json'); report = current(root, folder.name)
        stamp, _ = context(root, folder, doc)
        if review is None:
            if allow_claims: raise ValueError('explicit current mapping review required for claim adoption')
            selected = [r for r in doc['items'] if r['source'].startswith('gate:')]
            binding = None
        else:
            ids = review.get('item_ids')
            if isinstance(ids, list) and ids and len(ids) == len(set(ids)):
                already = [r for r in doc['items'] if r['id'] in ids]
                view = {'state':'current','attempt_id':report['attempt_id'],'digest':report['attempt_digest']}
                if (len(already) == len(ids) and all(r['mode'] == 'automatic' and r['history']
                        and r['history'][-1].get('mapping_review', {}).get('review') == review
                        and state(r, stamp, row_evidence_stamp(root, folder, r, view)) == 'passed' for r in already)):
                    if current(root, folder.name) != report or read(folder / 'verification.json') != original:
                        raise ValueError('execution/plan changed during idempotent readback')
                    print('CHECK_RESULTS_ADOPTED: 0; already applied; no commands executed')
                    return doc
            binding = check_mapping_snapshot(root, folder, ids)
            if (review.get('input_digest') != binding['input_digest'] or not isinstance(review.get('reviewer'), str)
                    or not review['reviewer'].strip() or review.get('status') != 'supported'):
                raise ValueError('current exact-claim mapping review required; partial rejected')
            findings = review.get('findings')
            if not isinstance(findings, list) or len(findings) != len(ids) or {f.get('item_id') for f in findings} != set(ids):
                raise ValueError('review every automatic claim')
            for f in findings:
                if f.get('verdict') != 'supported' or any(not isinstance(f.get(k), str) or not f[k].strip() for k in ('assertion_evidence','required_scope','counterexample_check')):
                    raise ValueError('precise current assertion evidence required')
            selected = [r for r in doc['items'] if r['id'] in ids]
        results = {x['name']: x for x in report['results']}; changed = []
        for row in selected:
            evidence_stamp = row_evidence_stamp(root, folder, row, {'state':'current','attempt_id':report['attempt_id'],'digest':report['attempt_digest']})
            if state(row, stamp, evidence_stamp) == 'passed': continue
            gates = [results.get(g) for g in row['gates']]
            if not gates or any(not g or g['status'] != 'passed' for g in gates): raise ValueError('mapped gate absent or failed')
            if binding and not row['source'].startswith('gate:'):
                finding = next(f for f in review['findings'] if f['item_id'] == row['id'])
                test_ids = finding.get('test_ids')
                if (not isinstance(test_ids, list) or not test_ids or len(test_ids) != len(set(test_ids))
                        or not all(isinstance(t, str) and t for t in test_ids)
                        or not set(test_ids) <= {t for g in gates for t in g.get('test_ids', [])}):
                    raise ValueError('review must identify tests actually executed by the mapped gates')
            if not row['source'].startswith('gate:') and not set(row.get('test_ids', [])) <= {t for g in gates for t in g.get('test_ids', [])}:
                raise ValueError('claim test IDs not executed by mapped gates')
            entry = result('passed', stamp, report['project_snapshot']['git_head'],
                           json.dumps(gates, ensure_ascii=False), 'Check attempt ' + report['attempt_id'],
                           'check-v2 execution referenced; no command re-executed')
            entry.update(check_attempt={'id': report['attempt_id'], 'digest': report['attempt_digest']}, evidence_digest=evidence_stamp)
            if binding: entry['mapping_review'] = {'inputs': binding, 'review': review}
            row['history'].append(entry); changed.append(row['id'])
        if current(root, folder.name) != report or read(folder / 'verification.json') != original:
            raise ValueError('execution/plan changed before adoption; execution retained, not applied')
        if binding and check_mapping_snapshot(root, folder, review['item_ids']) != binding:
            raise ValueError('mapping changed before adoption')
        if changed:
            doc.update(schema_version=max(4, doc['schema_version']), execution_contract=2); save(folder / 'verification.json', doc); render(folder)
        print('CHECK_RESULTS_ADOPTED: ' + str(len(changed)) + '; no commands executed')
        return doc
    return action() if locked else plan_mutation(lambda root, folder: action())(root, folder)


def doc_without_new_results(doc):
    import copy
    old = copy.deepcopy(doc)
    for row in old['items']:
        if row['mode'] == 'automatic':
            row['history'].pop()
    return old


@plan_mutation
def record(root, folder, item_id, status, stamp, tested, actual, evidence):
    doc = load_plan(folder)
    from acceptance_contract import enabled, record_fact
    if enabled(doc): return record_fact(root,folder,item_id,status,stamp,tested,actual,evidence)
    current, head = context(root, folder, doc)
    from feature_lifecycle import require_active
    require_active(read(folder / 'spec/requirements.json')['feature'])
    if current != stamp or tested != head:
        raise ValueError('manual result does not match current digest/full commit; keep old-build evidence in report history')
    if not actual or not actual.strip() or not evidence or not evidence.strip():
        raise ValueError('actual observation and evidence required')
    row = next((r for r in doc['items'] if r['id'] == item_id), None)
    if row is None or row['mode'] != 'manual' or row['source'] == 'system:no-gates':
        raise ValueError('select a manual acceptance item, not a gate or missing-configuration row')
    scoped = row['source'].startswith('impact:') and bool(row.get('dependencies'))
    entry = result(status, stamp, tested, actual, evidence, 'manual',
                   semantic=semantic_stamp(root, folder, row) if scoped else None,
                   files=scope_files(root, folder) if scoped else None)
    row.pop('manual_scope_ref', None)
    row['history'].append(entry)
    entry['evidence_digest'] = manual_evidence_stamp(root, folder, row)
    save(folder / 'verification.json', doc)
    render(folder)


@plan_mutation
def retain(root, folder, item_id, stamp, changed, reason, evidence):
    """Carry a prior pass only after a scoped, current-input relevance review."""
    doc = load_plan(folder)
    from acceptance_contract import refuse_legacy
    refuse_legacy(doc)
    current, head = context(root, folder, doc)
    from feature_lifecycle import require_active
    require_active(read(folder / 'spec/requirements.json')['feature'])
    if stamp != current:
        raise ValueError('scope review digest is stale')
    row = next((r for r in doc['items'] if r['id'] == item_id), None)
    if row is None or row['mode'] != 'manual' or not row['history']:
        raise ValueError('only a previously observed manual item may retain evidence')
    if row['source'][:7] != 'impact:' or not row.get('dependencies'):
        raise ValueError('retention requires a scoped preserved impact behavior; otherwise retest')
    impact = read(folder / 'impact.json')
    behavior = next((b for b in impact['behaviors'] if b['id'] == row['source'][7:]), None)
    if behavior is None or behavior['kind'] != 'preserve':
        raise ValueError('only preserved behavior may retain prior evidence')
    if row.get('manual_scope_ref'):
        raise ValueError('manual scope references require batch review, not strict retain')
    previous = row['history'][-1]
    if previous['status'] not in ('passed', 'retained') or state(row, current, manual_evidence_stamp(root, folder, row)) != 'stale':
        raise ValueError('only a stale prior pass can be retained; failures and waivers need fresh disposition')
    if not isinstance(previous.get('scope_files'), dict) or previous.get('semantic_digest') not in (semantic_stamp(root, folder, row), legacy_semantic_stamp(root, folder, row)):
        raise ValueError('prior evidence lacks matching semantic and file provenance; retest')
    now = scope_files(root, folder)
    before = previous['scope_files']
    delta = sorted(p for p in before.keys() | now.keys() if before.get(p) != now.get(p))
    if not delta or sorted(set(changed)) != delta or len(changed) != len(delta):
        raise ValueError('review every changed registered path exactly once: ' + ', '.join(delta))
    if set(row['dependencies']) & set(delta):
        raise ValueError('registered behavior dependency changed; rerun the affected check')
    if not set(row['dependencies']) <= set(now):
        raise ValueError('registered behavior dependency is outside observed scope')
    if not reason.strip() or not evidence.strip():
        raise ValueError('scope reasoning and inspected evidence are required')
    carried = result('retained', current, previous['tested_revision'],
                     'Prior passed observation in history at ' + previous['tested_revision'],
                     'Scope review at ' + head + ': ' + evidence + '; prior result digest: ' + previous['digest'],
                     'prior observation retained after scoped review; not re-executed',
                     semantic=previous['semantic_digest'], files=now)
    carried['reviewed_revision'] = head
    carried['changed_paths'] = delta
    carried['reason'] = reason
    carried['source_result_digest'] = previous['digest']
    carried['evidence_digest'] = manual_evidence_stamp(root, folder, row)
    row['history'].append(carried)
    save(folder / 'verification.json', doc)
    render(folder)


def validate_verification(root, folder, req, stage):
    path = folder / 'verification.json'
    required = req.get('feature', {}).get('verification_required', False)
    if not isinstance(required, bool):
        return ['verification_required must be boolean']
    if not path.exists():
        return ['verification list missing; run sync'] if required and stage == 'check' else []
    try:
        doc = load_plan(folder)
        from acceptance_contract import enabled, resolve_claims
        if enabled(doc):
            if stage != 'check': return []
            return ['verification incomplete: '+json.dumps(x,ensure_ascii=False) for x in resolve_claims(root,folder)['blockers']]
        if stage != 'check':
            return []
        stamp, _ = context(root, folder, doc)
        execution_view = check_currency(root, folder)
        return ['verification incomplete: ' + r['id'] + ' (' + state(r, stamp, row_evidence_stamp(root, folder, r, execution_view)) + ')'
                for r in doc['items'] if state(r, stamp, row_evidence_stamp(root, folder, r, execution_view)) not in ('passed', 'waived', 'retained')]
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return ['invalid verification: ' + str(exc)]


def impact_results(root, folder):
    """Read current checklist evidence without duplicating editable acceptance records."""
    doc = load_plan(folder)
    from acceptance_contract import enabled, resolve_claims, latest_result
    if enabled(doc):
        view=resolve_claims(root,folder); by_id={x['id']:x for x in view['items']}
        impact_stamp=impact_snapshot(root,read(folder/'impact.json'))['digest']
        results={};origin_cache={}
        for row in doc['items']:
            if row['source'].startswith('impact:') and by_id[row['id']]['status'] in ('passed','waived'):
                last=latest_result(root,folder,row,doc=doc,inventory=view['world']['facts'],cache=origin_cache)
                results[row['source'][7:]]={'status':by_id[row['id']]['status'],'method':last.get('method','automatic reviewed attempt'),'evidence':json.dumps(last,ensure_ascii=False),'digest':impact_stamp}
        return results
    stamp, _ = context(root, folder, doc)
    execution_view = check_currency(root, folder)
    impact_stamp = impact_snapshot(root, read(folder / 'impact.json'))['digest']
    results = {}
    for row in doc['items']:
        if row['source'].startswith('impact:') and state(row, stamp, row_evidence_stamp(root, folder, row, execution_view)) in ('passed', 'waived', 'retained'):
            last = row['history'][-1]
            results[row['source'][7:]] = {'status': 'passed' if last['status'] == 'retained' else last['status'], 'method': last['method'],
                                       'evidence': last['actual'] + '\n' + last['evidence'], 'digest': impact_stamp}
            if doc.get('result_correction_reviews'):
                from result_corrections import links
                results[row['source'][7:]]['result_corrections'] = links(root, doc, row)
    return results


def annotation_links(doc, row, effective_status):
    """Read only explicit validated receipt links; never infer a note from prose."""
    events = {event['id']: event for event in doc.get('annotation_reviews', [])}
    links = []
    for index, entry in enumerate(row['history']):
        if entry.get('retention_kind') != 'annotation_amend':
            continue
        receipt = entry['annotation_receipt']  # load_plan already validates this binding.
        event = events[receipt['review_id']]
        verdict = next(r for r in event['review']['items'] if r['item_id'] == row['id'])
        inputs = event['inputs']
        current = index == len(row['history']) - 1 and effective_status == 'retained'
        links.append({
            'review_id': event['id'], 'result_history_index': index, 'history_index_basis': 'zero_based',
            'source_result_hash': receipt['source_result_hash'],
            'applicability': 'current_receipt' if current else 'historical_only',
            'scope': [{'path': m['path'], 'role': m['role']} for m in inputs['metadata']],
            'archive_additions': [r['path'] for r in inputs.get('archive_additions', [])],
            'item_assessment': verdict['evidence'],
            'shared_scope_reason': event['review']['classification_evidence'],
            'reviewed_revision': inputs['reviewed_revision'],
            'boundary': 'Linked archive/index review, not a new observation or status override; historical-only notes cannot establish current acceptance. Investigate changed inputs and evidence applicability first; this label alone does not require a new observation or full retest.',
        })
    # An explicit adverse/unknown row verdict has no applied receipt, so is not a correction approval.
    linked = {r['review_id'] for r in links}
    for event in events.values():
        verdict = next((r for r in event['review']['items'] if r['item_id'] == row['id']), None)
        if verdict and event['id'] not in linked:
            links.append({'review_id': event['id'], 'applicability': 'needs_review',
                          'scope': [{'path': m['path'], 'role': m['role']} for m in event['inputs']['metadata']],
                          'item_assessment': verdict['evidence'],
                          'boundary': 'Explicit row assessment has no applied receipt; do not infer an accepted correction or change acceptance state.'})
    return links


def legacy_execution_diagnostic(root, folder):
    """Read existing audit input guards; never adopt/rebind legacy assertions."""
    from project import quality_selection, quality_snapshot, quality_comparison
    report_path = root / '.agent-workflow/project-baseline/quality-report.json'
    try:
        if report_path.is_symlink():
            raise ValueError('quality report must be a regular file')
        original = report_path.read_bytes()
        report = json.loads(original)
        req, config, _ = sources(root, folder)
        if (not config['gates'] or config.get('selection_feature_id') != folder.name
                or report.get('quality_selection') != quality_selection(config)):
            raise ValueError('report selection is missing or does not match this feature')
        if report.get('input_comparison', {}).get('state') != 'same':
            raise ValueError('execution did not certify stable inputs')
        comparison = quality_comparison(root, report.get('project_snapshot'), quality_snapshot(root, config))
        if comparison['state'] != 'same':
            raise ValueError('execution inputs changed or are unknown: ' + comparison.get('reason', comparison['state']))
        if req.get('feature', {}).get('baseline') is not None:
            from revisions import binding
            if report.get('feature_baseline') != binding(root, folder.name):
                raise ValueError('report requirement baseline changed')
        results = report.get('results')
        if (not isinstance(results, list) or len(results) != len(config['gates'])
                or any(not isinstance(row, dict) for row in results)
                or len({row.get('name') for row in results}) != len(results)):
            raise ValueError('report does not contain the complete selected check set')
        by_name = {row['name']: row for row in results}
        for gate in config['gates']:
            row = by_name.get(gate['name'], {})
            if row.get('status') != 'passed' or row.get('returncode') != 0:
                raise ValueError('latest selected result failed, unavailable or missing')
            if row.get('command') != gate['command'] or row.get('test_ids', []) != gate.get('test_ids', []):
                raise ValueError('executed check contract does not match selection')
        if report_path.read_bytes() != original:
            raise ValueError('quality report changed during inspection')
        return {'state': 'current', 'reason': 'Latest legacy report matches existing input, selection and stable-execution guards; coverage and delivery are not approved.'}
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        return {'state': 'unavailable', 'reason': str(exc)}


def continuation_diagnostic(root, folder, items, execution_view, *, plan=None):
    from acceptance_contract import enabled
    if enabled(plan or load_plan(folder)):
        return {'contract':1,'state':'review_required' if any(x['status'] not in ('passed','waived') for x in items) else 'current',
                'next_action_code':'review_acceptance_delta' if any(x['status'] not in ('passed','waived') for x in items) else 'review_delivery','next_action':'Inspect complete changes and current claims; capture/apply acceptance review only when pending. Current judgments proceed to delivery guards without re-signing facts or running commands solely for record changes.'}

    """Read-only routing from existing facts; never certify assertion coverage."""
    from check_runs import enabled
    plan = load_plan(folder) if plan is None else plan
    automatic = [r for r in items if r['mode'] == 'automatic']
    pending = [r['id'] for r in automatic if r['status'] not in ('passed', 'retained', 'waived')]
    manual = [r['id'] for r in items if r['mode'] == 'manual' and r['status'] not in ('passed', 'retained', 'waived')]
    result = {'automatic_pending': pending, 'manual_pending': manual,
              'boundary': 'Read-only guidance, not coverage approval or permission to execute. Manual/device evidence, authority and final review remain separate.'}
    # These are investigation candidates, never a certificate of dependency
    # completeness, source availability or unchanged authority.
    candidates, waivers, gaps, negative, rejected = [], [], [], [], {}
    from manual_scope import source_row
    for row in plan['items']:
        if row['id'] not in manual: continue
        latest = row['history'][-1]['status'] if row['history'] else None
        ref = row.get('manual_scope_ref')
        prior = next((e for e in plan.get('manual_scope_reviews', []) if ref and e['id'] == ref['event_id']), None)
        finding = next((f for f in prior['review']['findings'] if f['item_id'] == row['id']), None) if prior else None
        if finding and finding['verdict'] != 'supported':
            negative.append(row['id'])
            gaps.append(row['id'])
            continue
        if latest == 'waived':
            waivers.append(row['id'])
        elif latest in ('passed', 'retained'):
            try:
                source_row(plan, row['id'])
                candidates.append(row['id'])
            except (ValueError, TypeError, KeyError) as exc:
                rejected[row['id']] = str(exc)
                gaps.append(row['id'])
        else:
            gaps.append(row['id'])
    result['manual_applicability'] = {
        'contract': 1 if plan.get('manual_scope_contract') == 1 else 'legacy',
        'review_candidates': candidates, 'waiver_authority_checks': waivers,
        'new_or_adverse_claims': gaps, 'prior_negative_assessments': negative, 'source_chain_refusals': rejected,
        'next_action': ('Inspect complete claims, changes, original identity and shared/transitive dependencies before capture-batch; adopt only explicitly supported targets.'
                        if plan.get('manual_scope_contract') == 1 else
                        'Existing batch applicability may review unchanged active passed/retained rows even when a full parent changed. Before use, review format compatibility and obtain preparation authorization; do not enable it automatically. Legacy single-row carry is stricter.'),
        'boundary': 'Candidates are not certified reusable. New/replaced claims, latest failure/unavailable, missing originals and unknown effects remain gaps. Saved negative assessments require new evidence/authority before reconsideration, not a new reviewer on identical facts. Waivers need original-authority scope review/current recording, never automatic conversion into retained evidence.'}
    if not enabled(root):
        legacy = legacy_execution_diagnostic(root, folder)
        result.update(contract='legacy', execution_state='not_evaluated', legacy_execution=legacy, reason=legacy['reason'])
        if legacy['state'] != 'current':
            result.update(next_action_code='investigate_execution',
                          next_action='Investigate the latest report/input blocker. Use focused checks to diagnose actual failures, then execute applicable required gates on final inputs within authorization. Never fall back to older success.')
        elif pending:
            result.update(next_action_code='review_legacy_binding',
                          next_action='Execution inputs match, but legacy acceptance is pending. Investigate claim/record changes and supported existing routes; legacy has no adopt-checks path. Do not re-sign old results, auto-migrate or promise that a physical rerun can be avoided.')
        else:
            result.update(next_action_code='review_delivery',
                          next_action='Automatic rows and latest execution guards are current. Inspect full coverage and remaining manual/device gaps, then use validate-feature.py --stage check and audit-delivery.py. Do not call project.py check or verification.py run solely for a stage transition; both execute commands.')
    elif not execution_view or execution_view.get('state') != 'current':
        result.update(contract=2, execution_state='unavailable', next_action_code='investigate_execution',
                      reason=(execution_view or {}).get('reason', 'No current execution fact'),
                      next_action='Investigate the latest attempt, input/selection identity and unresolved processes. Never borrow older success; run selected checks only within authorization after blockers are resolved.')
    else:
        claims = {r['id'] for r in plan['items'] if not r['source'].startswith('gate:')}
        result.update(contract=2, execution_state='current', next_action_code='review_execution_binding' if pending else 'review_delivery', attempt_id=execution_view['attempt_id'],
                      report_ref=execution_view['report_ref'],
                      reason='Latest execution inputs and selection match. Pending acceptance is not proof that a command needs re-execution; all requirements/decisions still bind claim stamps.',
                      next_action=('Inspect complete current claims against actual executed assertions; use capture-check-mapping and adopt-checks only for fully supported targets. Missing assertions require targeted tests. run always executes commands.' if pending else 'No pending automatic acceptance; resolve remaining manual/device/authority/final-review requirements without rerunning checks solely for a stage transition.'),
                      claim_review_targets=[i for i in pending if i in claims],
                      gate_binding_targets=[i for i in pending if i not in claims])
    return result


def summary(root, folder):
    doc = load_plan(folder)
    from acceptance_contract import enabled, resolve_claims
    if enabled(doc):
        view=resolve_claims(root,folder); view.pop('world',None)
        view['continuation']={'next_action_code':'review_acceptance_delta' if view['blockers'] else 'review_delivery','next_action':'Capture/apply acceptance review on full changes; no automatic rerun or migration.'}
        print(json.dumps(view,ensure_ascii=False,indent=2))
        return 0 if view['acceptance_eligible'] else 2
    stamp, head = context(root, folder, doc)
    execution_view = check_currency(root, folder)
    items = []
    for row in doc['items']:
        item = {'id': row['id'], 'mode': row['mode'], 'status': state(row, stamp, row_evidence_stamp(root, folder, row, execution_view)), 'expected': row['expected']}
        if row.get('dependencies'):
            item['dependencies'] = row['dependencies']
            item['scope_reason'] = row['scope_reason']
        if item['status'] == 'retained' and not row.get('manual_scope_ref'):
            last = row['history'][-1]
            item.update(tested_revision=last['tested_revision'], reviewed_revision=last['reviewed_revision'],
                        changed_paths=last['changed_paths'], reason=last['reason'])
        if row.get('manual_scope_ref'):
            item['manual_scope'] = execution_view.get('_manual_scope', {}).get('items', {}).get(row['id'], {})
        item['annotation_links'] = annotation_links(doc, row, item['status'])
        if doc.get('adoption_reviews'):
            from evidence_adoption import links as adoption_links
            item['evidence_adoptions'] = adoption_links(doc, row)
        if doc.get('result_correction_reviews'):
            from result_corrections import links
            item['result_corrections'] = links(root, doc, row)
        items.append(item)
    print(json.dumps({'digest': stamp, 'tested_revision': head, 'items': items,
                      'continuation': continuation_diagnostic(root, folder, items, execution_view, plan=doc)}, ensure_ascii=False, indent=2))
    return 0 if all(r['status'] in ('passed', 'waived', 'retained') for r in items) else 2


def render(folder):
    if not (folder / 'verification.json').exists():
        return
    doc = load_plan(folder)
    root = folder.parents[2]
    from acceptance_contract import enabled, project_views
    if enabled(doc): return project_views(root,folder)
    try:
        stamp, _ = context(root, folder, doc)
    except (OSError, ValueError, TypeError, KeyError):
        stamp = None
    execution_view = check_currency(root, folder) if stamp else None
    lines = ['# Verification checklist', '', 'Generated view; manual observation and automated checks are distinct.', '']
    for row in doc['items']:
        effective = state(row, stamp, row_evidence_stamp(root, folder, row, execution_view)) if stamp else 'stale'
        lines += ['## ' + row['id'], '', 'Mode: ' + row['mode'], 'Expected: ' + str(row['expected']),
                  'Status: ' + (effective if stamp else 'stale — synchronize sources'), '']
        if row.get('manual_scope_ref'):
            scoped = (execution_view or {}).get('_manual_scope', {})
            details = scoped.get('items', {}).get(row['id'], {'state': 'unavailable', 'reason': scoped.get('reason', 'scope review unavailable')})
            lines += ['Manual applicability (original observation unchanged; no new execution):', '```json', json.dumps(details, ensure_ascii=False, indent=2), '```', '']
        if row.get('dependencies'):
            lines += ['Dependencies: ' + ', '.join(row['dependencies']), 'Scope rationale: ' + row['scope_reason'], '']
        if row['history']:
            lines += ['Latest recorded evidence (not necessarily current):', '```json', json.dumps(row['history'][-1], ensure_ascii=False, indent=2), '```', '']
        if doc.get('adoption_reviews'):
            from evidence_adoption import links as adoption_links
            adopted = adoption_links(doc, row)
            if adopted:
                lines += ['Reviewed interpretation adoption (original execution preserved):', '```json', json.dumps(adopted, ensure_ascii=False, indent=2), '```', '']
        if doc.get('result_correction_reviews'):
            from result_corrections import links as correction_links
            notes = correction_links(root, doc, row)
            if notes:
                lines += ['Reviewed description corrections (read alongside original evidence; no new execution):', '```json', json.dumps(notes, ensure_ascii=False, indent=2), '```', '']
        links = annotation_links(doc, row, effective)
        if links:
            lines += ['Linked archive/index notes (original result and test identity unchanged):', '```json', json.dumps(links, ensure_ascii=False, indent=2), '```', '']
        elif doc.get('annotation_reviews'):
            lines += ['Annotation link: none; free-text notes are not inferred. Check an explicitly cited note separately when needed.', '']
    (folder / 'verification.md').write_text('\n'.join(lines))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['sync', 'run', 'status', 'record', 'retain', 'capture-check-mapping', 'adopt-checks', 'prepare-acceptance', 'compose-acceptance'])
    p.add_argument('root', type=Path)
    p.add_argument('feature_id')
    p.add_argument('--item'); p.add_argument('--status', choices=['passed', 'failed', 'unavailable', 'waived'])
    p.add_argument('--items', nargs='+'); p.add_argument('--review', type=Path)
    p.add_argument('--approval',type=Path); p.add_argument('--resolutions',type=Path)
    p.add_argument('--digest'); p.add_argument('--tested-revision'); p.add_argument('--actual'); p.add_argument('--evidence')
    p.add_argument('--changed-path', action='append', default=[]); p.add_argument('--reason')
    args = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.feature_id):
        p.error('invalid feature ID')
    root = args.root.resolve(); folder = root / '.agent-workflow/features' / args.feature_id
    if not folder.resolve().is_relative_to(root) or folder.is_symlink():
        p.error('unsafe feature path')
    try:
        if args.action == 'prepare-acceptance':
            from acceptance_contract import prepare
            if not args.approval: raise ValueError('PREPARE_REQUIRED: --approval required')
            prepare(root,folder,read(args.approval)); render(folder); return summary(root,folder)
        if args.action == 'compose-acceptance':
            from acceptance_contract import compose_delivery
            manifest=compose_delivery(root,folder); print(json.dumps(manifest,ensure_ascii=False,indent=2)); return 0 if manifest['delivery_eligible'] else 2
        if args.action == 'capture-check-mapping':
            print(json.dumps(check_mapping_snapshot(root, folder, args.items), ensure_ascii=False, indent=2)); return 0
        if args.action == 'adopt-checks':
            if not args.review: raise ValueError('adopt-checks requires --review')
            adopt_checks(root, folder, review=read(args.review)); return 0
        if args.action == 'sync':
            sync(root, folder,read(args.resolutions) if args.resolutions else None); render(folder); summary(root, folder); return 0
        if args.action == 'run':
            return run(root, folder)
        if args.action == 'record':
            if not all([args.item, args.status, args.digest, args.tested_revision, args.actual, args.evidence]):
                raise ValueError('record requires item, status, digest, tested-revision, actual and evidence')
            record(root, folder, args.item, args.status, args.digest, args.tested_revision, args.actual, args.evidence)
            return 0
        if args.action == 'retain':
            if not all([args.item, args.digest, args.reason, args.evidence]):
                raise ValueError('retain requires item, digest, changed-path, reason and evidence')
            retain(root, folder, args.item, args.digest, args.changed_path, args.reason, args.evidence)
            return 0
        return summary(root, folder)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        p.exit(1, 'ERROR: ' + str(exc) + '\n')


if __name__ == '__main__':
    sys.exit(main())
