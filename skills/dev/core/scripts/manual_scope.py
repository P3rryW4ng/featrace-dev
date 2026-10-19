"""Reviewed current applicability of existing manual facts; never new execution."""
import copy
from datetime import datetime, timezone
from pathlib import Path

from impact import digest, git, path_name

RECORDS = ('spec/requirements.json', 'decisions.json', 'impact.json',
           'spec/prd-intake.json', 'traceability.json', 'tasks.json')


def workspace(root, folder):
    from check_runs import safe
    original = Path(root).absolute()
    folder = safe(original, Path(folder).absolute())
    root = original.resolve()
    if folder.parent != root / '.agent-workflow/features':
        raise ValueError('manual scope requires a feature directory in this workspace')
    return root, folder


def contract(row):
    return {k: v for k, v in row.items() if k not in ('history', 'retention', 'manual_scope_ref')}


def text(value):
    return isinstance(value, str) and bool(value.strip())


def semantic(name, value):
    value = copy.deepcopy(value)
    if name == 'spec/requirements.json':
        # A known lifecycle control, checked by the ordinary feature guards.
        value['feature'].pop('status', None)
    if name == 'tasks.json':
        from task_review import semantic_tasks
        value['tasks'] = semantic_tasks(value['tasks'])
    if name == 'impact.json':
        for row in value['behaviors']:
            row.pop('verification', None)
    return value


def records(root, folder, revision=None):
    import verification as v
    from evidence_carry import historical
    values = {}
    for name in RECORDS:
        if revision:
            rel = (folder / name).relative_to(root).as_posix()
            exists = git(root, 'ls-tree', revision, '--', rel)
            value = historical(root, folder, revision, name) if exists else None
        else:
            path = folder / name
            if path.is_symlink(): raise ValueError('unsafe manual scope record')
            value = v.read(path) if path.exists() else None
        values[name] = None if value is None else digest(semantic(name, value))
    if any(values[n] is None for n in RECORDS[:5]):
        raise ValueError('manual scope authority/contract unavailable')
    return values


def inputs(root, folder, doc):
    """One operation-local shared read; no persistent cache or per-row Git walk."""
    import verification as v
    from evidence_carry import project_files, source_identity
    from regression_continuity import check_worktree
    from check_identity import capture
    from check_runs import read
    v.sources(root, folder)  # Keep ordinary scope/config eligibility.
    tree = project_files(root)
    check_worktree(root, tree)
    registry = root / '.agent-workflow/project-baseline/evidence-files.json'
    required = read(root, registry)['files'] if registry.exists() else []
    identity = capture(root, required, ('AGENTS.md', 'CLAUDE.md'))
    if identity.get('state') != 'identified': raise ValueError('manual scope actual inputs unknown')
    identity.pop('head')  # Workflow-only commits do not change business identity.
    source = source_identity(root, folder)
    return {'records': records(root, folder), 'project': tree, 'actual_inputs': identity,
            'source_inputs': source,
            'scope_kind': 'complete-authority-and-project-change-review'}


def guarded_inputs(root, folder, doc):
    from check_runs import execution_lock, no_unfinished
    with execution_lock(root):
        no_unfinished(root)
        return inputs(root, folder, doc)


def prepare(root, folder):
    import verification as v
    from feature_lifecycle import require_active
    root, folder = workspace(root, folder)
    @v.plan_mutation
    def action(root, folder):
        doc = v.load_plan(folder)
        require_active(v.read(folder / 'spec/requirements.json')['feature'])
        v.sources(root, folder)
        if doc.get('manual_scope_contract') == 1: return doc
        doc.update(schema_version=5, manual_scope_contract=1, manual_scope_reviews=[])
        v.save(folder / 'verification.json', doc)
        v.render(folder)
        return doc
    return action(root, folder)


def support_events(doc, ident):
    selected = []
    for name, field, nested in [('result_correction_reviews', 'corrections', False),
                                ('annotation_reviews', 'items', True),
                                ('adoption_reviews', 'rows', True)]:
        for event in doc.get(name, []):
            rows = event.get('inputs', {}).get(field, []) if nested else event.get(field, [])
            if any(r.get('item_id') == ident for r in rows):
                selected.append(event.get('id') or event.get('digest'))
    return selected


def source_row(doc, ident):
    row = next((r for r in doc['items'] if r['id'] == ident), None)
    if (row is None or row['mode'] != 'manual' or not row['source'].startswith(('requirement:', 'impact:'))
            or not row['history'] or row['history'][-1]['status'] not in ('passed', 'retained')):
        raise ValueError('select latest passed/retained active manual fact; no withdrawal/waiver fallback')
    from evidence_carry import original_observation
    # Existing validated contiguous carry/annotation chains only. Interpretation
    # adoption of an unavailable source remains on its existing explicit path.
    origin = original_observation(row, row['history'][-1])
    return row, origin


def capture(root, folder, requests):
    import verification as v
    from evidence_carry import historical, project_files, parent, observation_ref
    from feature_lifecycle import require_active
    root, folder = workspace(root, folder)
    doc = v.load_plan(folder)
    if doc.get('manual_scope_contract') != 1: raise ValueError('explicit manual-scope prepare required')
    require_active(v.read(folder / 'spec/requirements.json')['feature'])
    if not isinstance(requests, list) or not requests: raise ValueError('explicit manual scope requests required')
    current = guarded_inputs(root, folder, doc)
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    before_trees, before_records, targets, seen = {}, {}, [], set()
    historical_cache, checked_intervals, checked_revisions, existence = {}, set(), set(), {}
    def history(revision, name):
        key = (revision, name)
        if key not in historical_cache: historical_cache[key] = historical(root, folder, revision, name)
        return historical_cache[key]
    for request in requests:
        if not isinstance(request, dict) or set(request) - {'item_id', 'contract_revision'}:
            raise ValueError('invalid manual scope request')
        ident = request.get('item_id')
        if not text(ident) or ident in seen: raise ValueError('distinct manual scope target IDs required')
        seen.add(ident); row, origin = source_row(doc, ident)
        base = origin['tested_revision']
        prior = row.get('manual_scope_ref')
        previous = next((e for e in doc.get('manual_scope_reviews', []) if prior and e['id'] == prior['event_id']), None)
        old_target = next((t for t in previous['snapshot']['targets'] if t['item_id'] == ident), None) if previous else None
        records_at = request.get('contract_revision') or (old_target['contract_revision'] if old_target else base)
        for revision in (base, records_at):
            if revision not in checked_revisions:
                if git(root, 'rev-parse', revision + '^{commit}').decode().strip() != revision:
                    raise ValueError('full original/contract revision required')
                checked_revisions.add(revision)
        if (base, records_at) not in checked_intervals:
            git(root, 'merge-base', '--is-ancestor', base, records_at)
            git(root, 'merge-base', '--is-ancestor', records_at, head)
        if base not in before_trees: before_trees[base] = project_files(root, base)
        if (base, records_at) not in checked_intervals:
            interval = git(root, 'rev-list', '--ancestry-path', base + '..' + records_at).decode().splitlines()
            if any(project_files(root, rev) != before_trees[base] for rev in interval):
                raise ValueError('business tree changed before original contract record')
            checked_intervals.add((base, records_at))
        if records_at not in before_records: before_records[records_at] = records(root, folder, records_at)
        old_plan = history(records_at, 'verification.json')
        old_row = next((r for r in old_plan['items'] if r['id'] == ident), None)
        if (old_row is None or contract(old_row) != contract(row) or not old_row['history']
                or old_row['history'][-1] != origin):
            raise ValueError('recorded original row/observation unavailable or claim changed; use explicit adoption')
        # Authority already present at execution must not be substituted later.
        for name in ('spec/requirements.json', 'impact.json'):
            rel = (folder / name).relative_to(root).as_posix()
            if (base, rel) not in existence: existence[(base, rel)] = bool(git(root, 'ls-tree', base, '--', rel))
            if existence[(base, rel)]:
                if digest(parent(history(base, 'spec/requirements.json'),
                                 history(base, 'impact.json'), row)) != digest(parent(
                        history(records_at, 'spec/requirements.json'),
                        history(records_at, 'impact.json'), old_row)):
                    raise ValueError('parent authority changed before original record was saved')
        changes = ['project:' + base + ':' + p for p in sorted(before_trees[base].keys() | current['project'].keys())
                   if before_trees[base].get(p) != current['project'].get(p)]
        changes += ['record:' + records_at + ':' + n for n in RECORDS
                    if before_records[records_at][n] != current['records'][n]]
        targets.append({'item_id': ident, 'contract_revision': records_at,
                        'original': observation_ref(row, origin), 'original_registered_at': origin['at'],
                        'observed_at': origin.get('observed_at'),
                        'latest_hash': digest(row['history'][-1]), 'row_contract': contract(row),
                        'support_events': support_events(doc, ident),
                        'changes': changes})
        if records_at != base:
            targets[-1]['contract_record'] = {'revision': records_at, 'tested_revision': base,
                'source_result_hash': digest(origin), 'records_digest': digest(before_records[records_at]),
                'row_contract_digest': digest(contract(old_row))}
    snapshot = {'schema_version': 1, 'feature_id': folder.name, 'reviewed_revision': head,
                'requests': requests, 'current': current, 'before_projects': before_trees,
                'before_records': before_records, 'targets': targets, 'plan_digest': digest(doc)}
    snapshot['input_digest'] = digest(snapshot)
    if guarded_inputs(root, folder, doc) != current or v.read(folder / 'verification.json') != doc:
        raise ValueError('manual scope inputs moved during capture')
    return snapshot


def validate_review(snapshot, review):
    from evidence_carry import validate_origin, validate_contract_record
    if (not isinstance(review, dict) or review.get('input_digest') != snapshot['input_digest']
            or review.get('independent_context') is not True or not text(review.get('reviewer'))):
        raise ValueError('fresh complete manual-scope batch review required')
    findings = review.get('findings')
    ids = [t['item_id'] for t in snapshot['targets']]
    if (not isinstance(findings, list) or len(findings) != len(ids)
            or any(not isinstance(f, dict) for f in findings) or {f.get('item_id') for f in findings} != set(ids)):
        raise ValueError('review every requested manual claim exactly once')
    assessments = review.get('assessments')
    if not isinstance(assessments, dict): raise ValueError('shared change assessments required')
    expected_changes = {c for t in snapshot['targets'] for c in t['changes']}
    if set(assessments) != expected_changes: raise ValueError('assess every changed code/authority path exactly once')
    for assessment in assessments.values():
        if not isinstance(assessment, dict) or not text(assessment.get('evidence')): raise ValueError('change assessment lacks evidence')
    for f in findings:
        target = next(t for t in snapshot['targets'] if t['item_id'] == f['item_id'])
        if f.get('verdict') not in ('supported', 'affected', 'unknown', 'partial'):
            raise ValueError('invalid manual scope verdict')
        refs = f.get('assessment_refs')
        if not isinstance(refs, dict) or set(refs) != set(target['changes']) or any(effect not in ('unaffected', 'affected', 'unknown') for effect in refs.values()):
            raise ValueError('each claim must address every applicable change')
        for field in ('claim_evidence', 'dependency_evidence', 'contract_evidence', 'environment_evidence', 'counterexample'):
            if not text(f.get(field)): raise ValueError('complete claim/dependency/environment/counterexample evidence required')
        paths = f.get('dependencies')
        if not isinstance(paths, list) or not paths or len(set(paths)) != len(paths):
            raise ValueError('distinct investigated dependencies required')
        for path in paths:
            path_name(path)
            if path not in snapshot['current']['project']: raise ValueError('dependency unavailable')
        if f['verdict'] == 'supported':
            if any(effect != 'unaffected' for effect in refs.values()):
                raise ValueError('supported claim contradicts change assessment')
            validate_origin(f, target['original']['tested_revision'], snapshot['current']['source_inputs'])
            if 'contract_record' in target:
                validate_contract_record(target['contract_record'], f, target['original']['result_hash'])
    selected = review.get('apply_ids')
    if (not isinstance(selected, list) or len(selected) != len(set(selected))
            or not set(selected) <= {f['item_id'] for f in findings if f['verdict'] == 'supported'}):
        raise ValueError('explicit supported subset required (may be empty)')
    return selected


def validate_document(doc):
    if type(doc.get('schema_version')) is not int or doc.get('schema_version') != 5 or type(doc.get('manual_scope_contract')) is not int or doc.get('manual_scope_contract') != 1:
        raise ValueError('manual scope requires schema 5 contract')
    if 'execution_contract' in doc and (type(doc['execution_contract']) is not int or doc['execution_contract'] != 2):
        raise ValueError('unsupported automatic execution contract in schema 5')
    events = doc.get('manual_scope_reviews')
    if not isinstance(events, list): raise ValueError('manual scope review ledger required')
    seen = set()
    for event in events:
        if (not isinstance(event, dict) or not text(event.get('at')) or event.get('id') in seen
                or event.get('id') != digest({k: val for k, val in event.items() if k != 'id'})):
            raise ValueError('corrupt or duplicate manual scope event')
        seen.add(event['id']); snap = event['snapshot']
        if (snap.get('schema_version') != 1 or snap.get('feature_id') != doc['feature_id']
                or snap.get('input_digest') != digest({k: val for k, val in snap.items() if k != 'input_digest'})):
            raise ValueError('manual scope snapshot mismatch')
        validate_review(snap, event['review'])
        for target in snap['targets']:
            origin = target['original']; index = origin['history_index']
            rows = [r for r in doc['items'] + doc['retired'] if r['id'] == target['item_id']
                    and type(index) is int and 0 <= index < len(r['history'])
                    and digest(r['history'][index]) == origin['result_hash']]
            if len(rows) != 1: raise ValueError('manual scope original row unavailable')
            row = rows[0]; origin = target['original']; i = origin['history_index']
            if (type(i) is not int or i < 0 or i >= len(row['history']) or origin['item_id'] != row['id']
                    or digest(row['history'][i]) != origin['result_hash']
                    or row['history'][i]['tested_revision'] != origin['tested_revision']
                    or target.get('original_registered_at') != row['history'][i]['at']
                    or target.get('observed_at') != row['history'][i].get('observed_at')):
                raise ValueError('manual scope original fact changed')
    for row in doc['items'] + doc['retired']:
        ref = row.get('manual_scope_ref')
        latest_assessment = next((e for e in reversed(events) if any(
            t['item_id'] == row['id'] and row['history'] and t['latest_hash'] == digest(row['history'][-1])
            for t in e['snapshot']['targets'])), None)
        if latest_assessment is not None and (not isinstance(ref, dict) or ref.get('event_id') != latest_assessment['id']):
            raise ValueError('manual scope must retain the latest assessment; no older green/missing reference')
        if ref is None: continue
        if (row['mode'] != 'manual' or not isinstance(ref, dict) or set(ref) != {'event_id', 'item_id'}
                or ref['event_id'] not in seen or ref['item_id'] != row['id']):
            raise ValueError('invalid manual scope reference')
        event = next(e for e in events if e['id'] == ref['event_id'])
        if not any(t['item_id'] == row['id'] for t in event['snapshot']['targets']):
            raise ValueError('scope reference does not belong to claim')


def assessment_matches(current, doc, row, event, target):
    """Internal basis check, independent of a positive adoption verdict."""
    return bool(current == event['snapshot']['current'] and row['history']
                and row['history'][-1]['status'] in ('passed', 'retained')
                and digest(row['history'][-1]) == target['latest_hash']
                and contract(row) == target['row_contract']
                and support_events(doc, row['id']) == target['support_events'])


def view(root, folder, doc=None):
    import verification as v
    root, folder = workspace(root, folder)
    doc = v.load_plan(folder) if doc is None else doc
    if doc.get('manual_scope_contract') != 1: return None
    try:
        current = guarded_inputs(root, folder, doc)
        result = {}
        for row in doc['items']:
            ref = row.get('manual_scope_ref')
            if not ref: continue
            event = next(e for e in doc['manual_scope_reviews'] if e['id'] == ref['event_id'])
            target = next(t for t in event['snapshot']['targets'] if t['item_id'] == row['id'])
            finding = next(f for f in event['review']['findings'] if f['item_id'] == row['id'])
            assessment_current = assessment_matches(current, doc, row, event, target)
            okay = (assessment_current and row['id'] in event['review']['apply_ids'] and finding['verdict'] == 'supported')
            result[row['id']] = {'state': 'current' if okay else 'stale', 'event_id': event['id'],
                                  'verdict': finding['verdict'], 'original': target['original'],
                                  'review_ref': '.agent-workflow/features/' + folder.name + '/verification.json#manual_scope_reviews/' + event['id'],
                                  'observed_at': target['observed_at'], 'original_registered_at': target['original_registered_at'],
                                  'reviewed_at': event['at'],
                                  'reviewed_revision': event['snapshot']['reviewed_revision'],
                                  'reason': 'reviewed applicability; no new execution' if okay else 'scope inputs changed or claim not supported/adopted'}
        return {'state': 'readable', 'items': result}
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return {'state': 'unavailable', 'reason': str(exc), 'items': {}}


def apply(root, folder, snapshot, review):
    import verification as v
    root, folder = workspace(root, folder)
    @v.plan_mutation
    def action(root, folder):
        doc = v.load_plan(folder); original = copy.deepcopy(doc)
        selected = validate_review(snapshot, review)
        for event in doc.get('manual_scope_reviews', []):
            if event['review'] == review and event['snapshot'] == snapshot:
                current = guarded_inputs(root, folder, doc)
                rows = {r['id']: r for r in doc['items']}
                if all(t['item_id'] in rows
                       and rows[t['item_id']].get('manual_scope_ref', {}).get('event_id') == event['id']
                       and assessment_matches(current, doc, rows[t['item_id']], event, t)
                       for t in snapshot['targets']):
                    if v.read(folder / 'verification.json') != doc: raise ValueError('plan changed during idempotent readback')
                    return doc
                raise ValueError('already applied manual scope review is no longer current')
        # Repeating a review on identical facts cannot erase an earlier negative.
        for finding in review['findings']:
            row = next(r for r in doc['items'] if r['id'] == finding['item_id'])
            ref = row.get('manual_scope_ref')
            prior = next((e for e in doc['manual_scope_reviews'] if ref and e['id'] == ref['event_id']), None)
            if prior and finding['verdict'] == 'supported' and prior['snapshot']['current'] == snapshot['current']:
                previous = next(f for f in prior['review']['findings'] if f['item_id'] == row['id'])
                before = next(t for t in prior['snapshot']['targets'] if t['item_id'] == row['id'])
                after = next(t for t in snapshot['targets'] if t['item_id'] == row['id'])
                if previous['verdict'] != 'supported' and all(before[k] == after[k] for k in ('latest_hash', 'row_contract', 'support_events')):
                    raise ValueError('negative assessment needs new evidence/authority before support')
        fresh = capture(root, folder, snapshot['requests'])
        if fresh != snapshot: raise ValueError('manual scope inputs/plan changed; no adoption')
        event = {'snapshot': snapshot, 'review': review, 'at': datetime.now(timezone.utc).isoformat()}
        event['id'] = digest(event)
        # Recapture of the same current basis is a no-op, not another history/event.
        checked = view(root, folder, doc)
        already = all(checked and checked['items'].get(i, {}).get('state') == 'current' for i in selected)
        same_mixed = any(
            e['snapshot']['current'] == snapshot['current']
            and e['snapshot']['targets'] == snapshot['targets']
            and e['review']['findings'] == review['findings']
            and e['review']['apply_ids'] == selected
            and all(next(r for r in doc['items'] if r['id'] == t['item_id']).get('manual_scope_ref', {}).get('event_id') == e['id']
                    for t in snapshot['targets'])
            for e in doc['manual_scope_reviews'])
        if already and (same_mixed or (selected and all(f['verdict'] == 'supported' for f in review['findings']))):
            if v.read(folder / 'verification.json') != doc: raise ValueError('plan changed during recapture readback')
            return doc
        doc['manual_scope_reviews'].append(event)
        for target in snapshot['targets']:
            row = next(r for r in doc['items'] if r['id'] == target['item_id'])
            row['manual_scope_ref'] = {'event_id': event['id'], 'item_id': row['id']}
        validate_document(doc)
        if guarded_inputs(root, folder, original) != snapshot['current'] or v.read(folder / 'verification.json') != original:
            raise ValueError('manual scope moved before save')
        v.save(folder / 'verification.json', doc)
        v.render(folder)
        return doc
    return action(root, folder)
