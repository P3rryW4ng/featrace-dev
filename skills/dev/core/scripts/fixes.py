"""Structured fix records and generated review view. No automatic root-cause claims."""
import json
import re
from pathlib import Path

STATUSES = {'reported', 'investigating', 'blocked', 'resolved', 'verified'}
KINDS = {'unclassified', 'implementation_defect', 'task_description_gap', 'interpretation_gap',
         'requirement_change', 'source_conflict', 'environment'}


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def string_list(value):
    return isinstance(value, list) and all(nonempty(v) for v in value)


def read_fixes(folder, feature_id):
    path = folder / 'fixes.json'
    if not path.exists():
        return {'feature_id': feature_id, 'fixes': []}  # Legacy workspace.
    return json.loads(path.read_text())


def validate_fixes(folder, feature_id, requirements, tasks, decisions, stage):
    errors, warnings = [], []
    try:
        doc = read_fixes(folder, feature_id)
    except (ValueError, OSError) as exc:
        return ['invalid fixes.json: ' + str(exc)], warnings
    if not isinstance(doc, dict) or doc.get('feature_id') != feature_id or not isinstance(doc.get('fixes'), list):
        return ['fixes.json requires matching feature_id and fixes array'], warnings
    requirement_ids = {r.get('id') for r in requirements if isinstance(r, dict)}
    task_ids = {t.get('id') for t in tasks if isinstance(t, dict)}
    decisions_by_id = {d.get('id'): d for d in decisions if isinstance(d, dict)}
    seen = set()
    for index, item in enumerate(doc['fixes']):
        label = 'fix[%d]' % index
        if not isinstance(item, dict):
            errors.append(label + ' must be an object'); continue
        fid = item.get('id')
        if not nonempty(fid) or not re.fullmatch(r'FIX-\d+', fid):
            errors.append(label + ' needs FIX-N id'); continue
        if fid in seen:
            errors.append('duplicate fix id: ' + fid)
        seen.add(fid); label = fid
        if not nonempty(item.get('description')):
            errors.append(label + ': description required')
        status, kind = item.get('status'), item.get('kind')
        if status not in STATUSES:
            errors.append(label + ': invalid status'); continue
        if kind not in KINDS:
            errors.append(label + ': invalid kind'); continue
        contributing = item.get('contributing_kinds', [])
        if not string_list(contributing) or any(x not in KINDS - {'unclassified'} for x in contributing) or kind in contributing or len(set(contributing)) != len(contributing):
            errors.append(label + ': invalid contributing_kinds')
            contributing = []
        causes = {kind, *contributing}
        for field, valid_ids in (('requirement_ids', requirement_ids), ('task_ids', task_ids)):
            refs = item.get(field, [])
            if not string_list(refs) or any(x not in valid_ids for x in refs):
                errors.append(label + ': invalid ' + field)
        refs = item.get('decision_ids', [])
        if not string_list(refs):
            refs = []
            errors.append(label + ': decision_ids must be text array')
        if any(x not in decisions_by_id for x in refs):
            errors.append(label + ': invalid decision_ids')
        for field in ('evidence', 'verification', 'source_refs', 'code_refs'):
            if not string_list(item.get(field, [])):
                errors.append(label + ': ' + field + ' must be text array')
        task_changes = item.get('task_changes', [])
        if not isinstance(task_changes, list):
            errors.append(label + ': task_changes must be an array')
            task_changes = []
        for change in task_changes:
            if (not isinstance(change, dict) or change.get('task_id') not in task_ids or
                    not nonempty(change.get('before')) or not nonempty(change.get('after')) or
                    change['before'] == change['after']):
                errors.append(label + ': task_changes require linked task_id and distinct before/after')
        if status in {'resolved', 'verified'}:
            for field in ('expected', 'actual', 'root_cause', 'resolution'):
                if not nonempty(item.get(field)):
                    errors.append(label + ': ' + field + ' required before resolution')
            if not nonempty(item.get('reproduction')) and not nonempty(item.get('unreproducible_reason')):
                errors.append(label + ': reproduction or unreproducible_reason required')
            if not item.get('evidence'):
                errors.append(label + ': observed mismatch evidence required')
            if kind == 'unclassified':
                errors.append(label + ': classify cause before resolution')
            if not item.get('requirement_ids') and not nonempty(item.get('scope_reason')):
                errors.append(label + ': link requirement or explain why none applies')
            if causes & {'implementation_defect', 'task_description_gap', 'interpretation_gap', 'requirement_change'} and not item.get('task_ids'):
                errors.append(label + ': affected task_ids required')
            if causes & {'interpretation_gap', 'requirement_change', 'source_conflict'} and not item.get('source_refs'):
                errors.append(label + ': source_refs required')
            if 'task_description_gap' in causes:
                if not task_changes:
                    errors.append(label + ': task description gap needs before/after task_changes')
                if not item.get('source_refs') and not refs:
                    errors.append(label + ': task description gap needs source or decision reference')
            if causes & {'requirement_change', 'source_conflict'}:
                approved = any(decisions_by_id.get(did, {}).get('status') == 'approved' and
                               nonempty(decisions_by_id[did].get('chosen')) for did in refs if did in decisions_by_id)
                if not approved or not nonempty(item.get('approval_ref')):
                    errors.append(label + ': approved decision and approval_ref required for source/requirement change')
        if status == 'verified' and not item.get('verification'):
            errors.append(label + ': verification evidence required')
        if status == 'verified':
            regression = item.get('regression_test_ids', [])
            known_tests = {test for req in requirements if isinstance(req, dict)
                           for test in (req.get('tests') if isinstance(req.get('tests'), list) else [])
                           if isinstance(test, str)}
            if not string_list(regression) or any(test not in known_tests for test in regression):
                errors.append(label + ': regression_test_ids must name declared requirement tests')
                regression = []
            if not regression and not nonempty(item.get('regression_waiver')):
                errors.append(label + ': regression test or explicit waiver required')
        if status == 'verified' and not nonempty(item.get('tested_revision')):
            errors.append(label + ': tested_revision required')
        if stage == 'check' and status != 'verified':
            errors.append(label + ': unresolved fix blocks feature check')
        elif stage == 'develop' and status != 'verified':
            warnings.append(label + ': unresolved fix; continue only eligible repair work')
    return errors, warnings


def render_fixes(folder, feature_id):
    doc = read_fixes(folder, feature_id)
    if not isinstance(doc, dict) or not isinstance(doc.get('fixes'), list):
        raise ValueError('invalid fixes.json')
    lines = ['# Fixes', '', 'Generated from fixes.json; edit the JSON record.', '']
    for fix in doc['fixes']:
        lines += ['## %s — %s' % (fix.get('id', '?'), fix.get('description', '')), '',
                  '- Status: ' + fix.get('status', ''), '- Cause: ' + fix.get('kind', ''),
                  '- Contributing causes: ' + ', '.join(fix.get('contributing_kinds', [])),
                  '- Expected: ' + fix.get('expected', ''), '- Actual: ' + fix.get('actual', ''),
                  '- Reproduction: ' + fix.get('reproduction', ''),
                  '- Requirements: ' + ', '.join(fix.get('requirement_ids', [])),
                  '- Tasks: ' + ', '.join(fix.get('task_ids', [])),
                  '- Task description changes: ' + '; '.join('%s: %s → %s' % (change.get('task_id', '?'), change.get('before', ''), change.get('after', '')) for change in fix.get('task_changes', [])),
                  '- Decisions: ' + ', '.join(fix.get('decision_ids', [])),
                  '- Source references: ' + ', '.join(fix.get('source_refs', [])),
                  '- Code references: ' + ', '.join(fix.get('code_refs', [])),
                  '- Scope reason: ' + fix.get('scope_reason', ''),
                  '- Approval reference: ' + fix.get('approval_ref', ''),
                  '- Root cause: ' + fix.get('root_cause', ''),
                  '- Resolution: ' + fix.get('resolution', ''),
                  '- Evidence: ' + '; '.join(fix.get('evidence', [])),
                  '- Verification: ' + '; '.join(fix.get('verification', [])),
                  '- Regression tests: ' + ', '.join(fix.get('regression_test_ids', [])),
                  '- Regression waiver: ' + fix.get('regression_waiver', ''),
                  '- Tested revision: ' + fix.get('tested_revision', ''), '']
    (folder / 'fixes.md').write_text('\n'.join(lines) + '\n')
