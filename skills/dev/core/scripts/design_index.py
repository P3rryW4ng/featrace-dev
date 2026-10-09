"""Validate a feature's scoped Figma page/state index and match supplied nodes."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse

from prd_intake import source_path


def figma_identity(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in {'figma.com', 'www.figma.com'}:
        raise ValueError('Figma URL must use https://figma.com')
    match = re.fullmatch(r'/(?:file|design|proto)/([A-Za-z0-9]+)(?:/.*)?', parsed.path)
    if not match:
        raise ValueError('Figma URL needs a file key')
    nodes = parse_qs(parsed.query).get('node-id', [])
    if len(nodes) != 1:
        raise ValueError('Figma URL needs exactly one node-id')
    node = nodes[0].replace('-', ':')
    if not re.fullmatch(r'[0-9]+:[0-9]+', node):
        raise ValueError('invalid Figma node-id')
    return match.group(1), node


def validate_index(folder, req_doc, stage):
    """Only opt-in features are gated; source discovery remains an Agent review."""
    feature = req_doc.get('feature', {})
    required = feature.get('design_index_required', False)
    if not isinstance(required, bool):
        return ['design_index_required must be boolean'], []
    if not required:
        return [], []
    strict = stage in {'develop', 'check'}
    errors, warnings = [], []
    def pending(message):
        (errors if strict else warnings).append(message)
    path = folder / 'design-index.json'
    if not path.is_file() or path.is_symlink():
        pending('design index missing: create design-index.json for the registered Figma source')
        return errors, warnings
    try:
        doc = json.loads(path.read_text())
        intake = json.loads((folder / 'spec/prd-intake.json').read_text())
    except (OSError, ValueError) as exc:
        return ['invalid design index or intake: ' + str(exc)], []
    if not isinstance(doc, dict) or doc.get('schema_version') != 1 or doc.get('feature_id') != feature.get('id'):
        return ['invalid design index identity/schema'], []
    scope = doc.get('scope')
    if not isinstance(scope, dict) or scope.get('status') not in {'pending', 'reviewed'}:
        errors.append('design scope needs pending/reviewed status')
    elif scope['status'] != 'reviewed' or not _text(scope.get('evidence')):
        pending('design scope has not been reviewed against relevant Figma frames/states')
    sources = intake.get('sources', [])
    if not isinstance(sources, list) or not isinstance(intake.get('units'), list):
        return errors + ['design index requires valid intake sources and units'], warnings
    registered = {x['path'] for x in sources if isinstance(x, dict) and x.get('kind') == 'design' and _text(x.get('path'))}
    listed = doc.get('sources')
    if not isinstance(listed, list):
        return errors + ['design index sources must be an array'], warnings
    source_states = {}
    for row in listed:
        if not isinstance(row, dict) or not _text(row.get('path')) or row.get('status') not in {'current', 'superseded', 'excluded'}:
            errors.append('invalid design source disposition'); continue
        name = row['path']
        if name in source_states:
            errors.append('duplicate design source: ' + name)
        source_states[name] = row['status']
        if row['status'] != 'current' and not _text(row.get('reason')):
            errors.append('noncurrent design source needs a reason: ' + name)
    if set(source_states) != registered:
        pending('design index must account for every registered design source')
    if not any(v == 'current' for v in source_states.values()):
        pending('design index has no current design source')
    screens = doc.get('screens')
    if not isinstance(screens, list):
        return errors + ['design index screens must be an array'], warnings
    if not screens:
        pending('design index has no logical screens/states')
    units = {x.get('id'): x for x in intake['units'] if isinstance(x, dict)}
    requirements = req_doc.get('requirements', [])
    if not isinstance(requirements, list):
        return errors + ['design index requires valid requirements'], warnings
    req_ids = {x.get('id') for x in requirements if isinstance(x, dict) and x.get('status') != 'deprecated'}
    seen_screens, seen_states, seen_nodes = set(), set(), set()
    for screen in screens:
        if not isinstance(screen, dict) or not _text(screen.get('id')) or not _text(screen.get('name')):
            errors.append('design screen needs id and name'); continue
        sid = screen['id']
        if sid in seen_screens: errors.append('duplicate design screen: ' + sid)
        seen_screens.add(sid)
        refs = screen.get('requirement_ids')
        if not isinstance(refs, list) or not refs or any(x not in req_ids for x in refs):
            errors.append(sid + ': requirement_ids must name active requirements')
        states = screen.get('states')
        if not isinstance(states, list) or not states:
            errors.append(sid + ': at least one state required'); continue
        for state in states:
            if not isinstance(state, dict) or not _text(state.get('id')) or not _text(state.get('name')):
                errors.append(sid + ': state needs id and name'); continue
            label = sid + '/' + state['id']
            if state['id'] in seen_states: errors.append('duplicate design state id: ' + state['id'])
            seen_states.add(state['id'])
            try:
                identity = figma_identity(state.get('url', ''))
            except (ValueError, TypeError) as exc:
                errors.append(label + ': ' + str(exc)); continue
            if identity in seen_nodes: errors.append(label + ': duplicate Figma node identity')
            seen_nodes.add(identity)
            source = state.get('source')
            if source_states.get(source) != 'current':
                errors.append(label + ': state must cite a current registered design source')
            else:
                try:
                    actual = hashlib.sha256(source_path(folder, source).read_bytes()).hexdigest()
                    if state.get('source_sha256') != actual:
                        errors.append(label + ': design source bytes changed or source_sha256 missing')
                except (OSError, ValueError) as exc:
                    errors.append(label + ': ' + str(exc))
            status = state.get('status')
            if status not in {'indexed', 'read', 'unavailable', 'excluded'}:
                errors.append(label + ': invalid read status'); continue
            if status in {'unavailable', 'excluded'} and not _text(state.get('reason')):
                errors.append(label + ': unavailable/excluded state needs a reason')
            if status == 'unavailable' and not _text(state.get('impact')):
                errors.append(label + ': unavailable state needs impact')
            if status == 'read':
                linked = state.get('unit_ids')
                if not isinstance(linked, list) or not linked:
                    errors.append(label + ': read state needs intake unit_ids')
                elif any(x not in units or units[x].get('source') != source or units[x].get('status') != 'read'
                         or units[x].get('figma_file_key') != identity[0]
                         or not isinstance(units[x].get('figma_node_id'), str)
                         or units[x]['figma_node_id'].replace('-', ':') != identity[1] for x in linked):
                    errors.append(label + ': unit_ids must cite read units at this exact Figma file and node')
            elif stage == 'check' and status in {'indexed', 'unavailable'}:
                errors.append(label + ': design state is not read or explicitly excluded')
    return errors, warnings


def match_state(folder, url=None, screen_name=None, state_name=None, supplied=None):
    """Exact node identity is authoritative; names only suggest candidates."""
    doc = json.loads((folder / 'design-index.json').read_text())
    identity = figma_identity(url) if url else None
    if identity is None and not (screen_name or state_name):
        raise ValueError('provide a Figma node URL or a screen/state description')
    digest = None
    if supplied is not None:
        supplied = Path(supplied)
        if not supplied.is_file() or supplied.is_symlink():
            raise ValueError('supplied design evidence must be a regular file')
        digest = hashlib.sha256(supplied.read_bytes()).hexdigest()
    exact, candidates = [], []
    for screen in doc.get('screens', []):
        for state in screen.get('states', []):
            try: current = figma_identity(state['url'])
            except (ValueError, KeyError, TypeError): continue
            item = {'screen_id': screen['id'], 'screen': screen['name'], 'state_id': state['id'], 'state': state['name'], 'url': state['url']}
            if identity == current:
                exact.append({**item, 'evidence_bytes': 'not_compared' if digest is None else ('same' if digest == state.get('source_sha256') else 'different')})
            elif (identity is None or identity[0] == current[0] or screen_name or state_name) and (not screen_name or screen_name.casefold() in screen['name'].casefold()) and (not state_name or state_name.casefold() in state['name'].casefold()):
                candidates.append(item)
    if len(exact) > 1:
        return {'status': 'ambiguous_identity', 'requires_confirmation': True, 'candidates': exact}
    if len(exact) == 1:
        return {'status': 'exact_identity', 'requires_confirmation': False, 'content_review_required': digest is None or exact[0]['evidence_bytes'] != 'same', 'match': exact[0]}
    return {'status': 'candidate_only' if candidates else 'unmatched', 'requires_confirmation': True, 'candidates': candidates}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['validate', 'match'])
    parser.add_argument('root', type=Path)
    parser.add_argument('feature_id')
    parser.add_argument('--stage', choices=['draft', 'develop', 'check'], default='develop')
    parser.add_argument('--url'); parser.add_argument('--screen-name'); parser.add_argument('--state-name'); parser.add_argument('--source', type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.feature_id):
        parser.error('invalid feature ID')
    root = args.root.resolve(); folder = root / '.agent-workflow/features' / args.feature_id
    if folder.is_symlink() or not folder.resolve().is_relative_to(root):
        parser.error('unsafe feature path')
    try:
        if args.action == 'validate':
            req = json.loads((folder / 'spec/requirements.json').read_text())
            errors, warnings = validate_index(folder, req, args.stage)
            for item in warnings: print('WARNING: ' + item)
            for item in errors: print('ERROR: ' + item)
            return 1 if errors else 0
        print(json.dumps(match_state(folder, args.url, args.screen_name, args.state_name, args.source), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(1, 'DESIGN_INDEX_ERROR: ' + str(exc) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
