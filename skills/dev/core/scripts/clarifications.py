"""Opt-in clarification contract on existing decision records; no semantic inference."""
import json


def text(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value):
    return isinstance(value, list) and all(text(v) for v in value)


def validate_clarifications(decisions, stage):
    errors, warnings = [], []
    ids = [d.get('id') for d in decisions if isinstance(d, dict)]
    for d in decisions:
        if not isinstance(d, dict):
            continue
        label = str(d.get('id'))
        if ids.count(d.get('id')) > 1:
            errors.append('duplicate decision id: ' + label)
        if 'clarification' not in d:
            continue  # Existing decisions retain their previous contract.
        c = d['clarification']
        if not isinstance(c, dict):
            errors.append(label + ': clarification must be an object')
            continue
        if not text(c.get('question')):
            errors.append(label + ': original question required')
        if not strings(c.get('evidence')):
            errors.append(label + ': clarification evidence must be a string array')
        state = d.get('status')
        if state not in ('pending', 'blocked', 'approved', 'superseded'):
            errors.append(label + ': invalid clarification decision status')
        kind = c.get('resolution_kind')
        if kind not in ('unclassified', 'existing_rule', 'change', 'withdrawn'):
            errors.append(label + ': invalid resolution_kind')
        application = c.get('application')
        if not isinstance(application, dict):
            errors.append(label + ': application object required')
            continue
        applied = application.get('status')
        if applied not in ('pending', 'applied', 'not_needed'):
            errors.append(label + ': invalid application status')
        if not strings(application.get('evidence')):
            errors.append(label + ': application evidence must be a string array')
        if state in ('pending', 'blocked'):
            warnings.append(label + ': clarification unresolved')
            if applied != 'pending':
                errors.append(label + ': unresolved clarification cannot be marked applied')
        if state == 'superseded':
            target = next((x for x in decisions if isinstance(x, dict) and x.get('id') == d.get('superseded_by')), None)
            if not target or target is d or target.get('status') != 'approved' or not text(target.get('chosen')):
                errors.append(label + ': superseded_by must name another approved decision')
        if state == 'approved':
            if not text(d.get('chosen')) or kind == 'unclassified':
                errors.append(label + ': approved clarification requires chosen and resolution_kind')
            if not strings(c.get('evidence')) or not c.get('evidence') or not text(c.get('impact_review')):
                errors.append(label + ': approved clarification requires evidence and impact_review')
            if kind in ('change', 'withdrawn') and not text(c.get('confirmation_ref')):
                errors.append(label + ': change/withdrawal requires confirmation_ref')
            if kind == 'change' and applied == 'not_needed':
                errors.append(label + ': confirmed change must be applied, not not_needed')
            if applied in ('applied', 'not_needed') and not application.get('evidence'):
                errors.append(label + ': application outcome requires evidence')
            if applied == 'pending':
                (errors if stage == 'check' else warnings).append(label + ': confirmed clarification not yet applied')
    return errors, warnings


def render_decisions(folder, decisions):
    lines = ['# Decisions', '']
    for d in decisions:
        lines += [f"## {d.get('id', '?')} — {d.get('title', '')}", '',
                  '- Status: ' + str(d.get('status', '')),
                  '- Chosen: ' + str(d.get('chosen') or 'pending')]
        for field in ('sources', 'options', 'impact', 'rationale', 'supersedes', 'superseded_by'):
            if d.get(field):
                lines.append('- ' + field + ': ' + json.dumps(d[field], ensure_ascii=False))
        if 'clarification' in d:
            lines += ['', '```json', json.dumps(d['clarification'], ensure_ascii=False, indent=2), '```']
        lines.append('')
    (folder / 'decisions.md').write_text('\n'.join(lines))
