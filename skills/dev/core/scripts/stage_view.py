#!/usr/bin/env python3
"""Read-only Test/Verify starting views over canonical records; never a verdict."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

from impact import digest
import verification as v


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


records = module('stage_build_records', 'build-inputs.py')
handoff = module('stage_verify_binding', 'verify-handoff.py')
inventory = module('stage_source_inventory', 'verify-inputs.py')


def collect(root, feature_id, stage, task_ids, item_ids, base=None):
    root = Path(root).resolve()
    if stage not in ('test', 'verify') or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', feature_id):
        raise ValueError('invalid stage or feature identity')
    prefix = '.agent-workflow/features/' + feature_id + '/'
    hashes = {}
    def read(name, required=True, project=False):
        return records.read_record(root, name if project else prefix + name, hashes, required)
    req = read('spec/requirements.json')
    if req.get('feature', {}).get('id') != feature_id:
        raise ValueError('feature mismatch')
    requirements = records.rows(req, 'requirements', 'requirements')
    tasks_doc, decisions_doc, impact = read('tasks.json'), read('decisions.json'), read('impact.json')
    tasks = records.rows(tasks_doc, 'tasks', 'tasks'); decisions = records.rows(decisions_doc, 'decisions', 'decisions')
    behaviors = records.rows(impact, 'behaviors', 'impact')
    trace_doc = read('traceability.json'); trace = records.rows(trace_doc, 'links', 'traceability')
    for doc in (tasks_doc, decisions_doc, impact, trace_doc):
        if doc.get('feature_id', feature_id) != feature_id:
            raise ValueError('canonical record belongs to another feature')
    fixes_doc = read('fixes.json', False)
    fixes = [] if fixes_doc is None else records.rows(fixes_doc, 'fixes', 'fixes')
    plan_record = read('verification.json', False)
    plan = v.load_plan(root / prefix) if plan_record is not None else None
    attention = []
    if plan is None:
        attention.append('verification_plan_missing; return to ordinary Verify preparation')
    rows = [] if plan is None else plan['items']
    def ids(values, key, label):
        result = [r.get(key) for r in values]
        if any(not isinstance(i, str) or not i for i in result) or len(result) != len(set(result)):
            raise ValueError('invalid/duplicate ' + label + ' IDs')
        return set(result)
    task_known = ids(tasks, 'id', 'task'); req_known = ids(requirements, 'id', 'requirement'); row_known = ids(rows, 'id', 'verification')
    task_ids = sorted(set(task_ids)); item_ids = sorted(set(item_ids))
    if set(task_ids) - task_known or set(item_ids) - row_known:
        raise ValueError('selection references an unknown task/item')
    selected = set()
    for task in tasks:
        if task['id'] in task_ids:
            linked = task.get('requirement_ids')
            if not isinstance(linked, list) or not linked or any(not isinstance(i, str) for i in linked):
                raise ValueError('selected task has incomplete requirement linkage')
            selected.update(linked)
    for row in rows:
        if row['id'] in item_ids:
            source = row['source'].split(':')
            if source[0] == 'requirement': selected.add(source[1])
            elif source[0] == 'impact':
                found = next((b for b in behaviors if b['id'] == source[1]), None)
                if found is None: raise ValueError('selected impact row missing parent behavior')
                selected.update(found.get('requirement_ids', []))
    if not task_ids and not item_ids:
        selected = {r['id'] for r in requirements if r.get('status') != 'deprecated'}
    if fixes_doc is not None and fixes_doc.get('feature_id', feature_id) != feature_id:
        raise ValueError('fix record belongs to another feature')
    if selected - req_known:
        raise ValueError('missing linked requirement')
    # Preserved/unscoped authority may span tasks. Expand linked full parents, never trim ACs.
    while True:
        relevant_behaviors = [b for b in behaviors if b.get('kind') == 'preserve' or records.scoped(b, selected)]
        grown = set(selected)
        linked_authority = relevant_behaviors + [d for d in decisions if records.scoped(d, selected)] + [f for f in fixes if records.scoped(f, selected)]
        for b in linked_authority:
            linked = b.get('requirement_ids')
            if isinstance(linked, list) and all(isinstance(i, str) for i in linked): grown.update(linked)
            else: attention.append('authority linkage unknown: ' + str(b.get('id')))
        if grown - req_known: raise ValueError('impact references missing requirement')
        if grown == selected: break
        selected = grown
    related_tasks = [t for t in tasks if records.scoped(t, selected)]
    relevant_decisions = [d for d in decisions if records.scoped(d, selected) or d.get('status') not in ('approved', 'rejected', 'superseded')]
    relevant_fixes = [f for f in fixes if records.scoped(f, selected) or f.get('status') not in ('verified', 'closed')]
    chosen_behaviors = {b['id'] for b in relevant_behaviors}
    chosen_rows = [r for r in rows if r['id'] in item_ids or r['source'].startswith(('gate:', 'system:'))
                   or (r['source'].startswith('requirement:') and r['source'].split(':')[1] in selected)
                   or (r['source'].startswith('impact:') and r['source'].split(':')[1] in chosen_behaviors)]
    config = read('.agent-workflow/project-baseline/quality-gates.json', False, True)
    report = read('.agent-workflow/project-baseline/quality-report.json', False, True)
    intake = read('spec/prd-intake.json', False)
    regression = read('regression-review.json', False)
    task_review = read('task-review.json', False)
    stamp = None
    if plan is not None:
        try: stamp, _ = v.context(root, root / prefix, plan)
        except (OSError, ValueError, KeyError, TypeError) as exc: attention.append('canonical_context_unavailable: ' + str(exc))
    claims, global_states = [], []
    chosen_ids = {r["id"] for r in chosen_rows}
    for row in rows:
        latest = row['history'][-1] if row['history'] else None
        result = None if latest is None else {k: value for k, value in latest.items() if k not in ('carry_receipt', 'annotation_receipt')}
        status = 'unknown'
        if stamp is not None:
            try: status = v.state(row, stamp, v.manual_evidence_stamp(root, root / prefix, row) if row['mode'] == 'manual' else None)
            except (OSError, ValueError, KeyError, TypeError) as exc: attention.append('row_currency_unknown: ' + row['id'] + ': ' + str(exc))
        global_states.append({'id': row['id'], 'source': row['source'], 'effective_state': status})
        if status not in ('passed', 'retained', 'waived'):
            attention.append('unresolved_acceptance: ' + row['id'] + ': ' + status)
        if row['id'] not in chosen_ids:
            continue
        contract = {k: value for k, value in row.items() if k not in ('history', 'retention')}
        claims.append(dict(contract, effective_state=status, latest_result=result,
                           annotation_links=v.annotation_links(plan, row, status),
                           history_ref=prefix + 'verification.json#items/' + row['id'] + '/history',
                           history_entries=len(row['history']), provenance_readback_required=bool(latest and latest.get('retention_kind'))))
    revision_index = []
    if req['feature'].get('baseline') is not None:
        from revisions import inspect
        try:
            _, _, pending = inspect(root / prefix, req)
            revision_index = [{'id': r['id'], 'ref': prefix + 'revisions/' + r['id'] + '.json'} for r in pending]
            attention.extend('pending_revision: ' + r['id'] for r in pending)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            attention.append('revision_inspection_unknown: ' + str(exc))
    info = inventory.collect(root, feature_id)
    attention.extend(info['issues_to_review'])
    for d in decisions:
        if d.get('status') not in ('approved', 'rejected', 'superseded'):
            attention.append('unresolved_decision: ' + str(d.get('id')))
    for f in fixes:
        if f.get('status') not in ('verified', 'closed'): attention.append('unresolved_fix: ' + str(f.get('id')))
    for name, value in [('intake', intake), ('task_review', task_review), ('historical_regression', regression), ('quality_selection', config), ('quality_report', report)]:
        if value is None: attention.append(name + '_missing')
    unscoped = {'decisions': [d.get('id') for d in relevant_decisions if not d.get('requirement_ids')],
                'fixes': [f.get('id') for f in relevant_fixes if not f.get('requirement_ids')]}
    base = base or impact.get('base_revision') or info['git_head']
    frozen = handoff.capture(root, feature_id, base, [])
    feature = req['feature']
    identity = {k: feature[k] for k in ('id', 'status', 'status_note', 'workflow_version', 'modules', 'source_status', 'source_notes') if k in feature}
    baseline = feature.get('baseline')
    if isinstance(baseline, dict):
        identity['baseline'] = {k: baseline[k] for k in ('version', 'digest', 'verified_version', 'pending') if k in baseline}
    quality_summary = None if report is None else {k: value for k, value in report.items() if k not in ('results', 'project_snapshot')}
    if report is not None:
        if not isinstance(report.get('results'), list) or any(not isinstance(r, dict) for r in report['results']) or not isinstance(report.get('project_snapshot'), dict):
            raise ValueError('quality report shape invalid; inspect canonical report before using stage inputs')
        quality_summary['project_revision'] = (report.get('project_snapshot') or {}).get('git_head')
        quality_summary['results'] = [{k: value for k, value in r.items() if k not in ('stdout', 'stderr', 'output')} for r in report.get('results', [])]
        quality_summary['full_report_ref'] = '.agent-workflow/project-baseline/quality-report.json'
    view = {'schema_version': 1, 'kind': 'stage_starting_view', 'stage': stage, 'project': str(root), 'feature_id': feature_id,
            'selection': {'task_ids': task_ids, 'item_ids': item_ids}, 'base_revision': frozen['inputs']['base_revision'],
            'source_snapshot_digest': frozen['input_digest'], 'code_revision': info['git_head'],
            'feature': identity, 'pending_revisions': revision_index, 'requirements': [r for r in requirements if r['id'] in selected],
            'tasks': related_tasks, 'decisions': relevant_decisions, 'fixes': [{k: value for k, value in f.items() if k != 'regression_execution_history'} for f in relevant_fixes],
            'impact': {**{k: value for k, value in impact.items() if k != 'behaviors'}, 'behaviors': relevant_behaviors},
            'traceability': [t for t in trace if t.get('requirement_id') in selected],
            'claims': claims, 'global_claim_states': global_states, 'quality_selection': config, 'quality_report': quality_summary,
            'historical_regression': regression, 'task_review': task_review,
            'source_index': info['sources'], 'source_readback_refs': [r.get('sources', []) for r in requirements if r['id'] in selected],
            'authority_refs': {'intake': prefix + 'spec/prd-intake.json', 'verification': prefix + 'verification.json',
                               'records': list(hashes), 'modules': '.agent-workflow/modules/'},
            'global_attention': sorted(set(attention)), 'unscoped_authority_included': unscoped,
            'fix_execution_readback_refs': [prefix + 'fixes.json#' + str(f.get('id')) + '/regression_execution_history' for f in relevant_fixes if f.get('regression_execution_history')],
            'omitted_requirements': sorted(req_known - selected), 'not_loaded': ['raw source contents', 'past verification history', 'full code/tests', 'raw quality output and full retention receipts'],
            'expand_when_needed': ['Read referenced originals and assertions; projection is not evidence of correctness.',
                                   'Investigate consumers/shared state outside selected tasks; no omission proves independence.',
                                   'Read canonical history/intake/revisions/modules when linkage or validity is uncertain.',
                                   'Whole-feature completion still requires normal validation/audit and all active claims.'],
            'authority': 'read-only derived starting view; not an execution plan, independent Agent, test result or delivery verdict'}
    view['responsibility'] = ('Inspect/execute applicable assertions, report actual outcomes and uncovered scope; never mark whole claims complete.' if stage == 'test' else 'Compare whole claims with actual assertions/results, try counterexamples, inspect retained provenance and remaining gaps; do not trust Test prose.')
    view['metrics'] = {'canonical_record_bytes': sum((root / p).stat().st_size for p in hashes),
                       'projected_payload_bytes': len(json.dumps(view, ensure_ascii=False, indent=2).encode()),
                       'tokens': None, 'cost': None, 'basis': 'serialized view before metrics/signature versus loaded canonical JSON file bytes; not actual Agent read or token usage'}
    view['view_digest'] = digest(view)
    return view


def capture(root, feature_id, stage, task_ids=None, item_ids=None, base=None):
    first = collect(root, feature_id, stage, task_ids or [], item_ids or [], base)
    second = collect(root, feature_id, stage, task_ids or [], item_ids or [], first['base_revision'])
    if first != second: raise ValueError('stage inputs changed during capture; preserve scene and retry')
    return first


def check(root, feature_id, snapshot):
    if snapshot.get('project') != str(Path(root).resolve()) or snapshot.get('feature_id') != feature_id:
        raise ValueError('stage view project/feature mismatch')
    if snapshot.get('view_digest') != digest({k: val for k, val in snapshot.items() if k != 'view_digest'}):
        raise ValueError('stage view content changed')
    selected = snapshot['selection']
    current = capture(root, feature_id, snapshot['stage'], selected['task_ids'], selected['item_ids'], snapshot['base_revision'])
    if current != snapshot: raise ValueError('stage view stale; regenerate from current authority')
    return 'STAGE_VIEW_CURRENT: read-only starting inputs; no delivery approval'


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('action', choices=('capture', 'check'))
    p.add_argument('root', type=Path); p.add_argument('feature_id'); p.add_argument('--stage', choices=('test', 'verify'))
    p.add_argument('--task', action='append', default=[]); p.add_argument('--item', action='append', default=[]); p.add_argument('--snapshot', type=Path)
    a = p.parse_args()
    try:
        if a.action == 'capture':
            if not a.stage: p.error('capture requires --stage')
            print(json.dumps(capture(a.root, a.feature_id, a.stage, a.task, a.item), ensure_ascii=False, indent=2))
        else:
            if not a.snapshot: p.error('check requires --snapshot')
            print(check(a.root, a.feature_id, json.loads(a.snapshot.read_text())))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print('STAGE_VIEW_ERROR: ' + str(exc), file=sys.stderr); return 1


if __name__ == '__main__': sys.exit(main())
