"""PRD intake records: deterministic checks, never a semantic PRD parser."""
import hashlib
import json
from pathlib import Path


def new_intake(feature_id):
    return {'version': 1, 'feature_id': feature_id, 'inventory_complete': False,
            'sources': [], 'units': [], 'items': [], 'review': {'reviewer': '', 'notes': '', 'digest': ''}}


def text(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value):
    return isinstance(value, list) and all(text(v) for v in value)


def source_path(folder, relative):
    if not text(relative) or Path(relative).is_absolute():
        raise ValueError('source path must be relative')
    path = (folder / relative).resolve()
    path.relative_to((folder / 'sources').resolve())
    if not path.is_file():
        raise ValueError('source file does not exist: ' + relative)
    return path


def review_digest(folder, intake, requirements):
    payload = {k: v for k, v in intake.items() if k != 'review'}
    files = {u['source']: hashlib.sha256(source_path(folder, u['source']).read_bytes()).hexdigest()
             for u in intake['units']}
    if isinstance(intake.get('sources'), list):
        for row in intake['sources']:
            files[row['path']] = hashlib.sha256(source_path(folder, row['path']).read_bytes()).hexdigest()
    # Only requirements/evidence semantics matter, not feature progress or task assignment.
    semantic = [{k: v for k, v in r.items() if k not in {'tasks', 'tests'}}
                for r in requirements['requirements']]
    data = {'intake': payload, 'requirements': semantic, 'sources': files}
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate_intake(folder, req_doc, stage, require_review=True):
    errors, warnings = [], []
    strict = stage in {'develop', 'check'}
    path = folder / 'spec/prd-intake.json'
    if not path.exists():
        (errors if strict else warnings).append('PRD intake missing: create and review spec/prd-intake.json before development')
        return errors, warnings
    try:
        doc = json.loads(path.read_text())
    except (ValueError, OSError) as exc:
        return ['invalid PRD intake: ' + str(exc)], []
    if not isinstance(doc, dict) or doc.get('version') != 1 or doc.get('feature_id') != req_doc['feature']['id']:
        return ['PRD intake version/feature_id is invalid'], []
    if not isinstance(doc.get('inventory_complete'), bool):
        errors.append('inventory_complete must be boolean')
    if not all(isinstance(doc.get(k), list) for k in ('units', 'items')):
        return errors + ['intake units/items must be arrays'], warnings

    def pending(message):
        (errors if strict else warnings).append(message)

    if not doc.get('inventory_complete'):
        pending('PRD inventory has not been reviewed as complete')
    if not doc['units']:
        pending('PRD inventory is empty')
    # Legacy intake v1 may omit sources; new workspaces register every supplied part.
    registered = doc.get('sources')
    if registered is not None:
        if not isinstance(registered, list):
            return errors + ['sources must be an array'], warnings
        paths, ids = set(), set()
        for row in registered:
            if not isinstance(row, dict) or not text(row.get('id')) or not text(row.get('path')) or row.get('kind') not in {'document', 'html'}:
                errors.append('each source needs id, path and document/html kind'); continue
            if row['id'] in ids or row['path'] in paths:
                errors.append('duplicate source id or path')
            ids.add(row['id']); paths.add(row['path'])
            try:
                source_path(folder, row['path'])
            except (ValueError, OSError) as exc:
                errors.append(row['id'] + ': ' + str(exc))
        if not paths:
            pending('no PRD document or HTML source registered')
        declared = req_doc.get('feature', {}).get('prd_paths')
        if declared is not None and (not strings(declared) or len(declared) != len(paths) or set(declared) != paths):
            errors.append('feature.prd_paths must match registered source paths')
        if errors:
            return errors, warnings
        for source in paths:
            if not any(isinstance(u, dict) and u.get('source') == source for u in doc['units']):
                pending('source has no reading unit: ' + source)
        for row in registered:
            if row['kind'] == 'html' and not (text(row.get('interaction_scope')) or any(isinstance(u, dict) and u.get('source') == row['path'] and u.get('kind') == 'interaction' for u in doc['units'])):
                pending('HTML has no interaction inventory or documented static scope: ' + row['path'])
        for unit in doc['units']:
            if isinstance(unit, dict) and text(unit.get('source')) and unit['source'] not in paths:
                errors.append('unit source is not registered: ' + unit['source'])
    units, items = {}, {}
    for kind, entries, target in [('unit', doc['units'], units), ('item', doc['items'], items)]:
        for row in entries:
            if not isinstance(row, dict) or not text(row.get('id')):
                errors.append(kind + ' needs an object with a non-empty id'); continue
            if row['id'] in target:
                errors.append('duplicate ' + kind + ' id: ' + row['id'])
            target[row['id']] = row
    if errors:
        return errors, warnings
    reqs = {r['id']: r for r in req_doc['requirements'] if isinstance(r, dict) and text(r.get('id'))}
    for uid, unit in units.items():
        for field in ('source', 'locator', 'kind'):
            if not text(unit.get(field)):
                errors.append(uid + ': missing ' + field)
        if unit.get('status') not in ('read', 'unreadable', 'pending', 'not_applicable'):
            errors.append(uid + ': invalid read status')
        elif unit['status'] in ('pending', 'unreadable'):
            pending(uid + ': unresolved reading gap')
            if not text(unit.get('reason')) or not text(unit.get('impact')):
                errors.append(uid + ': reading gap needs reason and impact')
        elif unit['status'] == 'not_applicable' and not text(unit.get('reason')):
            errors.append(uid + ': not_applicable needs scope rationale')
        try:
            source_path(folder, unit.get('source'))
        except (ValueError, OSError) as exc:
            errors.append(uid + ': ' + str(exc))
        if unit.get('kind') == 'interaction' and unit.get('status') == 'read':
            if not all(text(unit.get(field)) for field in ('trigger', 'before', 'after', 'observation')):
                errors.append(uid + ': observed interaction needs trigger, before, after and observation')
            if registered is not None and not any(row.get('path') == unit.get('source') and row.get('kind') == 'html' for row in registered if isinstance(row, dict)):
                errors.append(uid + ': interaction must refer to registered HTML')
        if unit.get('status') == 'read' and not any(i.get('unit_id') == uid for i in items.values()):
            pending(uid + ': read unit has no extracted item or background disposition')
    for sid, item in items.items():
        if not text(item.get('unit_id')) or item['unit_id'] not in units:
            errors.append(sid + ': unknown unit'); continue
        for field in ('quote', 'context'):
            if not text(item.get(field)):
                errors.append(sid + ': missing ' + field)
        if item.get('kind') not in ('rule', 'example', 'suggestion', 'background', 'undecided'):
            errors.append(sid + ': invalid item kind')
        if not strings(item.get('related_ids')) or any(x not in items for x in item.get('related_ids', []) if isinstance(x, str)):
            errors.append(sid + ': related_ids must name existing source items')
        disposition = item.get('disposition')
        if disposition == 'mapped' and units[item['unit_id']].get('status') != 'read':
            errors.append(sid + ': cannot map unread or not-applicable material')
        if disposition not in ('mapped', 'excluded', 'pending'):
            errors.append(sid + ': invalid disposition')
        elif disposition == 'pending':
            pending(sid + ': source item still unresolved')
        elif disposition == 'excluded':
            if item.get('kind') not in ('background', 'example', 'suggestion') or not text(item.get('reason')):
                errors.append(sid + ': only justified non-binding content may be excluded')
        aspects = item.get('aspects')
        if not isinstance(aspects, list):
            errors.append(sid + ': aspects must be an array'); continue
        if disposition == 'mapped' and not aspects:
            pending(sid + ': mapped item needs aspect-level coverage')
        for aspect in aspects:
            if not isinstance(aspect, dict):
                errors.append(sid + ': aspect must be an object'); continue
            if aspect.get('kind') not in ('behavior', 'condition', 'exception', 'limit', 'negation', 'relationship') or not text(aspect.get('text')):
                errors.append(sid + ': aspect needs kind and original meaning')
            rid, field = aspect.get('requirement_id'), aspect.get('field')
            if not text(rid) or rid not in reqs:
                errors.append(sid + ': aspect references unknown requirement'); continue
            req = reqs[rid]
            if not strings(req.get('source_item_ids')) or sid not in req.get('source_item_ids', []):
                errors.append(sid + ': missing reverse source_item_ids link in ' + rid)
            target = None
            if field == 'statement':
                target = req.get('statement')
            elif isinstance(field, str) and field.startswith('acceptance_criteria/'):
                index = field.split('/')[-1]
                criteria = req.get('acceptance_criteria', [])
                if index.isdigit() and isinstance(criteria, list) and int(index) < len(criteria):
                    target = criteria[int(index)]
            if not text(target) or aspect.get('target_text') != target:
                errors.append(sid + ': coverage target missing or changed')
            if aspect.get('review') != 'verified':
                pending(sid + ': condition/exception coverage not reviewed')
    if errors:
        return errors, warnings
    for rid, req in reqs.items():
        if req.get('status') == 'deprecated':
            continue
        refs = req.get('source_item_ids')
        if not strings(refs) or not refs:
            pending(rid + ': source_item_ids required'); continue
        for sid in refs:
            if sid not in items:
                errors.append(rid + ': unknown source item ' + sid)
            elif items[sid].get('disposition') != 'mapped' or not any(isinstance(a, dict) and a.get('requirement_id') == rid for a in items[sid].get('aspects', [])):
                if items[sid].get('disposition') == 'pending' and not strict:
                    pending(rid + ': forward aspect coverage awaits resolution of ' + sid)
                else:
                    errors.append(rid + ': missing forward aspect coverage for ' + sid)
        if req.get('status') == 'inferred' and not req.get('assumptions'):
            pending(rid + ': inferred requirement needs explicit assumptions')
    if not errors and require_review and strict:
        review = doc.get('review')
        if not isinstance(review, dict) or not text(review.get('reviewer')) or not text(review.get('notes')):
            errors.append('PRD semantic review attribution and notes required')
        elif review.get('stage') == 'draft':
            errors.append('draft PRD review cannot satisfy develop/check: complete reading gaps and record a full review')
        elif review.get('digest') != review_digest(folder, doc, req_doc):
            errors.append('PRD review missing or stale: reread sources and reconcile before recording review')
    return errors, warnings


def render_intake(folder):
    path = folder / 'spec/prd-intake.json'
    if not path.exists():
        return
    doc = json.loads(path.read_text())
    lines = ['# PRD reading and coverage record', '', 'Evidence index, not a second product specification.', '', '## Registered sources', '']
    for source in doc.get('sources', []):
        lines.append(f"- {source['id']} [{source['kind']}] {source['path']}")
    lines += ['', '## Reading inventory', '']
    for u in doc['units']:
        lines += [f"- {u['id']} [{u['status']}] {u['source']} — {u['locator']}", f"  - Reason/impact: {u.get('reason', '')} {u.get('impact', '')}"]
        if u.get('kind') == 'interaction':
            lines += [f"  - {u.get('before', '?')} --{u.get('trigger', '?')}--> {u.get('after', '?')}", '  - Observation: ' + u.get('observation', '')]
    lines += ['', '## Source items and coverage', '']
    for i in doc['items']:
        lines += [f"### {i['id']} [{i['kind']}; {i['disposition']}]", '', f"Source unit: {i['unit_id']}", '', i['quote'], '', 'Context: ' + i['context'], 'Related: ' + ', '.join(i.get('related_ids', [])), 'Disposition reason: ' + i.get('reason', ''), '']
        for a in i['aspects']:
            lines += [f"- {a['kind']}: {a['text']} → {a.get('requirement_id', '?')}/{a.get('field', '?')} [{a.get('review', 'pending')}]", '  - Target: ' + a.get('target_text', '')]
    lines += ['', '## Review record', '', json.dumps(doc.get('review', {}), ensure_ascii=False, indent=2), '', 'A recorded review is an attribution, not proof of semantic correctness. Develop validation checks its freshness.']
    (folder / 'spec/prd-analysis.md').write_text('\n'.join(lines) + '\n')
