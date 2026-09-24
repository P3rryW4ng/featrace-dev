#!/usr/bin/env python3
"""Read scoped module evidence and register Agent-reviewed module dossiers."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from impact import digest, git, path_name

SECTIONS = ('technology', 'behaviors', 'entry_points', 'state_lifecycle', 'tests')
GRADLE_SETTINGS = ('settings.gradle.kts', 'settings.gradle')
GRADLE_BUILDS = ('build.gradle.kts', 'build.gradle')


def read(path):
    return json.loads(path.read_text())


def safe(root, relative):
    path = root / relative
    if path.resolve() != path or not path.is_relative_to(root):
        raise ValueError('symlink/outside path: ' + str(relative))
    return path


def write(path, content):
    if path.is_symlink():
        raise ValueError('refusing symlink output')
    if path.exists() and path.read_text() == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False) as f:
        f.write(content)
    os.replace(f.name, path)


def catalog(root):
    doc = read(safe(root, '.agent-workflow/modules/index.json'))
    if not isinstance(doc, dict) or doc.get('schema_version') != 1 or not isinstance(doc.get('modules'), list) or not doc['modules']:
        raise ValueError('module index requires schema_version=1 and modules')
    if not isinstance(doc.get('shared_stack'), str) or not doc['shared_stack'].strip():
        raise ValueError('shared_stack needs an evidence-based summary')
    globals_ = doc.get('global_files')
    if not isinstance(globals_, list) or not globals_:
        raise ValueError('global_files must register build/rule evidence')
    for name in globals_:
        path_name(name)
        if not safe(root, name).is_file():
            raise ValueError('missing global evidence: ' + name)
    ids = set()
    for m in doc['modules']:
        if not isinstance(m, dict) or not isinstance(m.get('id'), str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', m['id']) or m['id'] in ids:
            raise ValueError('invalid/duplicate module ID')
        if m['id'].lower() == 'index':
            raise ValueError('index is reserved for the project overview')
        ids.add(m['id'])
        if not isinstance(m.get('summary'), str) or not m['summary'].strip():
            raise ValueError('module needs summary')
        for field in ('roots', 'depends_on', 'evidence_files'):
            values = m.get(field)
            if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values) or len(set(values)) != len(values):
                raise ValueError('module needs unique ' + field)
        if not m['roots']:
            raise ValueError('module needs explicit roots')
        for name in m['roots'] + m['evidence_files']:
            path_name(name); safe(root, name)
    if any(dep not in ids for m in doc['modules'] for dep in m['depends_on']):
        raise ValueError('unknown dependency; register module or record reading gap')
    return doc


def snapshot(root, index, module):
    # Git enumerates only declared roots; no full-project source content scan.
    specs = [':(literal)' + p for p in module['roots']]
    names = git(root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z', '--', *specs).decode().split('\0')
    paths = set(filter(None, names)) | set(module['evidence_files']) | set(index['global_files'])
    files = {}
    for name in sorted(paths):
        path_name(name)
        p = safe(root, name)
        if p.exists() and not p.is_file():
            raise ValueError('submodule/directory needs manual handling: ' + name)
        files[name] = {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'executable': bool(p.stat().st_mode & 0o111)} if p.exists() else None
    # Only this module's declaration and global overview invalidate its receipt.
    return {'files': files, 'digest': digest({'module': module, 'global_files': index['global_files'], 'shared_stack': index['shared_stack'], 'files': files})}


def check_body(root, module_id, body, snap):
    if not isinstance(body, dict) or body.get('module_id') != module_id:
        raise ValueError('module dossier identity mismatch')
    for field in SECTIONS:
        rows = body.get(field)
        if not isinstance(rows, list) or not rows:
            raise ValueError('dossier needs section: ' + field)
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('detail'), str) or not row['detail'].strip():
                raise ValueError('section entry needs detail')
            refs = row.get('evidence_files')
            if not isinstance(refs, list) or not refs or any(not isinstance(p, str) or p not in snap['files'] or snap['files'][p] is None for p in refs):
                raise ValueError('section needs existing scoped evidence; register external evidence first')
    for key in ('gaps', 'feature_ids'):
        values = body.get(key)
        if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
            raise ValueError('dossier needs ' + key + ' array')
    for fid in body['feature_ids']:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', fid):
            raise ValueError('invalid feature reference')
        req = read(safe(root, '.agent-workflow/features/' + fid + '/spec/requirements.json'))
        if req.get('feature', {}).get('id') != fid:
            raise ValueError('feature reference mismatch')


def selection(index, selected):
    modules = {m['id']: m for m in index['modules']}
    if not selected or any(name not in modules for name in selected):
        raise ValueError('select known module IDs; do not guess from latest feature')
    reasons = {name: 'selected' for name in selected}
    # Review direct callers of the selected modules and dependencies of that set.
    for name, m in modules.items():
        if any(dep in selected for dep in m['depends_on']) and name not in reasons:
            reasons[name] = 'direct caller of selected module'
    pending = list(reasons)
    while pending:
        for dep in modules[pending.pop()]['depends_on']:
            if dep not in reasons:
                reasons[dep] = 'dependency'; pending.append(dep)
    return modules, reasons


def plan(root, selected):
    root = root.resolve()
    if Path(git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != root:
        raise ValueError('module scan requires Git root')
    index = catalog(root)
    modules, reasons = selection(index, selected)
    output = []
    for name, reason in sorted(reasons.items()):
        snap = snapshot(root, index, modules[name])
        path = safe(root, '.agent-workflow/modules/' + name + '.json')
        status = 'unreviewed'; old = {}
        if path.exists():
            old = read(path)
            check_body(root, name, old['body'], {'files': old.get('review', {}).get('files', {})})
            receipt = old.get('review', {})
            status = 'current' if receipt.get('digest') == snap['digest'] and receipt.get('body_digest') == digest(old['body']) else 'stale'
            if old['body']['gaps']:
                status = 'gaps'
        previous = old.get('review', {}).get('files', {})
        changes = sorted(p for p in set(previous) | set(snap['files']) if previous.get(p) != snap['files'].get(p))
        output.append({'module': name, 'reason': reason, 'status': status, 'digest': snap['digest'],
                       'changed_paths': changes, 'scope_files': list(snap['files']),
                       'dossier': str(path), 'reviewed_revision': old.get('review', {}).get('revision')})
    return output


def review(root, module_id, body, expected):
    root = root.resolve(); index = catalog(root)
    module = next((m for m in index['modules'] if m['id'] == module_id), None)
    if module is None:
        raise ValueError('unknown module')
    before = snapshot(root, index, module)
    if before['digest'] != expected:
        raise ValueError('module changed since investigation; re-read changed evidence')
    check_body(root, module_id, body, before)
    doc = {'body': body, 'review': {'digest': expected, 'body_digest': digest(body), 'files': before['files'],
                                   'revision': git(root, 'rev-parse', 'HEAD').decode().strip(),
                                   'at': datetime.now(timezone.utc).isoformat()}}
    if catalog(root) != index or snapshot(root, index, module) != before:
        raise ValueError('module changed during review')
    write(safe(root, '.agent-workflow/modules/' + module_id + '.json'), json.dumps(doc, ensure_ascii=False, indent=2) + '\n')
    render(root, index, module_id, doc)


def _mermaid_label(value):
    return str(value).replace('"', "'").replace('\n', ' ')


def _line_ref(root, path, number):
    return str(path.relative_to(root)) + ':' + str(number)


def _without_gradle_comments(text):
    text = re.sub(r'/\*.*?\*/', lambda match: ''.join('\n' if char == '\n' else ' ' for char in match.group()), text, flags=re.S)
    return '\n'.join(line.split('//', 1)[0] for line in text.splitlines())


def _line_number(text, offset):
    return text.count('\n', 0, offset) + 1


def _gradle_id(value):
    return ':' + ':'.join(part for part in value.split(':') if part)


def _default_gradle_root(build_id):
    return '/'.join(part for part in build_id.split(':') if part)


def _registered_matches(index, candidate_root):
    if not index:
        return []
    result = []
    root = candidate_root.rstrip('/')
    for module in index['modules']:
        for declared in module['roots']:
            declared = declared.rstrip('/')
            if root == declared or root.startswith(declared + '/') or declared.startswith(root + '/'):
                result.append(module['id'])
                break
    return sorted(result)


def discover_gradle_candidates(root, index=None):
    """Extract conservative Gradle project/dependency candidates; never update the reviewed catalog."""
    root = root.resolve()
    settings = next((root / name for name in GRADLE_SETTINGS if (root / name).is_file()), None)
    gaps, source_files = [], {}
    modules, mappings = {}, {}
    if settings is None:
        gaps.append('No root settings.gradle(.kts) file was found; Gradle module discovery was not attempted.')
    else:
        if settings.is_symlink():
            raise ValueError('Gradle settings evidence must not be a symlink')
        relative = str(settings.relative_to(root))
        source_files[relative] = hashlib.sha256(settings.read_bytes()).hexdigest()
        text = _without_gradle_comments(settings.read_text(errors='replace'))
        for match in re.finditer(r'\bincludeBuild\s*\(', text):
            gaps.append(_line_ref(root, settings, _line_number(text, match.start())) + ': composite build requires manual review')
        # Applied settings can register modules through loops, projectDir mappings
        # or plugins. Point reviewers to the handoff without evaluating the script.
        for match in re.finditer(r'\bapply\s*(?:\(\s*from\s*=|\s+from\s*:)', text):
            suffix = text[match.end():].split('\n', 1)[0]
            literal = re.match(r'\s*(?:file\s*\(\s*)?["\']([^"\']+)["\']', suffix)
            hint = ' (' + literal.group(1) + ')' if literal else ''
            gaps.append(_line_ref(root, settings, _line_number(text, match.start())) +
                        ': applied settings script' + hint + ' requires manual review')
        include_ranges = []
        for pattern in (r'\binclude\s*\((.*?)\)', r'\binclude\s+([^\n]+)'):
            for match in re.finditer(pattern, text, re.S if '\\n' not in pattern else 0):
                if any(start <= match.start() < end for start, end in include_ranges):
                    continue
                include_ranges.append(match.span())
                number = _line_number(text, match.start())
                found = [_gradle_id(value) for value in re.findall(r'["\'](:[^"\']+)["\']', match.group(1))]
                if not found:
                    gaps.append(_line_ref(root, settings, number) + ': include expression was not statically understood')
                for build_id in found:
                    modules.setdefault(build_id, {'build_id': build_id, 'root': _default_gradle_root(build_id),
                                                   'evidence_refs': []})['evidence_refs'].append(_line_ref(root, settings, number))
        for match in re.finditer(
                r'project\s*\(\s*["\'](:[^"\']+)["\']\s*\)\s*\.\s*projectDir\s*=\s*'
                r'(?:rootProject\s*\.\s*)?(?:file|File)\s*\(\s*["\']([^"\']+)["\']\s*\)', text, re.S):
            number = _line_number(text, match.start())
            build_id, path = _gradle_id(match.group(1)), match.group(2).replace('\\', '/')
            try:
                path_name(path)
            except ValueError:
                gaps.append(_line_ref(root, settings, number) + ': unsafe projectDir was ignored')
                continue
            mappings[build_id] = (path.rstrip('/'), _line_ref(root, settings, number))
        for build_id, (path, ref) in mappings.items():
            row = modules.setdefault(build_id, {'build_id': build_id, 'root': path, 'evidence_refs': []})
            row['root'] = path
            row['evidence_refs'].append(ref)

    try:
        index = index or (catalog(root) if (root / '.agent-workflow/modules/index.json').is_file() else None)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        gaps.append('Reviewed module catalog could not be used for candidate matching: ' + str(exc))
        index = None

    edges = {}
    for build_id, row in sorted(modules.items()):
        build_root = root / row['root']
        build_file = next((build_root / name for name in GRADLE_BUILDS if (build_root / name).is_file()), None)
        if build_file is None:
            gaps.append(build_id + ': no build.gradle(.kts) found at ' + row['root'])
            continue
        if build_file.is_symlink():
            gaps.append(build_id + ': symlinked build file requires manual review')
            continue
        relative = str(build_file.relative_to(root))
        source_files[relative] = hashlib.sha256(build_file.read_bytes()).hexdigest()
        build_text = _without_gradle_comments(build_file.read_text(errors='replace'))
        matched_lines = set()
        patterns = (
            r'(?P<configuration>[A-Za-z][A-Za-z0-9_]*)\s*\(\s*project\s*\(\s*'
            r'(?:(?:path\s*=|path\s*:)\s*)?["\'](?P<target>:[^"\']+)["\']',
            r'(?P<configuration>[A-Za-z][A-Za-z0-9_]*)\s+project\s*\(\s*'
            r'(?:(?:path\s*=|path\s*:)\s*)?["\'](?P<target>:[^"\']+)["\']',
        )
        for pattern in patterns:
            for match in re.finditer(pattern, build_text, re.S):
                number = _line_number(build_text, match.start())
                matched_lines.add(number)
                target = _gradle_id(match.group('target'))
                key = (build_id, target, match.group('configuration'))
                edge = edges.setdefault(key, {'from': build_id, 'to': target,
                    'configuration': match.group('configuration'), 'status': 'candidate', 'evidence_refs': []})
                edge['evidence_refs'].append(_line_ref(root, build_file, number))
                if target not in modules:
                    gaps.append(_line_ref(root, build_file, number) + ': dependency target ' + target + ' is not a static include candidate')
        for match in re.finditer(r'\b(?:implementation|api|compileOnly|runtimeOnly|testImplementation)\b[^\n;]*project\s*\(', build_text):
            number = _line_number(build_text, match.start())
            if number not in matched_lines:
                gaps.append(_line_ref(root, build_file, number) + ': project dependency expression was not statically understood')
        for match in re.finditer(r'\b(?:implementation|api|compileOnly|runtimeOnly|testImplementation)\s*\([^\n;]*\bprojects\.', build_text):
            gaps.append(_line_ref(root, build_file, _line_number(build_text, match.start())) +
                        ': type-safe project accessor requires manual review')
        for match in re.finditer(r'\badd\s*\(\s*[^,;\n]+,\s*project\s*\(', build_text):
            number = _line_number(build_text, match.start())
            if number not in matched_lines:
                gaps.append(_line_ref(root, build_file, number) + ': add-style project dependency requires manual review')

    rows = []
    for build_id, row in sorted(modules.items()):
        rows.append({**row, 'evidence_refs': sorted(set(row['evidence_refs'])),
                     'registered_module_ids': _registered_matches(index, row['root']), 'status': 'pending_review'})
    result = {'schema_version': 1, 'kind': 'gradle_static_candidates', 'status': 'candidate_only',
              'source_files': dict(sorted(source_files.items())), 'modules': rows,
              'edges': [{**edge, 'evidence_refs': sorted(set(edge['evidence_refs']))}
                        for _, edge in sorted(edges.items())], 'gaps': sorted(set(gaps)),
              'limits': ['Static Gradle declarations are candidates, not confirmed module ownership or runtime calls.',
                         'Dynamic/composite includes, type-safe accessors, convention plugins, aliases, reflection and runtime navigation require manual review.']}
    base = safe(root, '.agent-workflow/modules')
    write(base / 'candidates.json', json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    node_ids = {row['build_id']: 'C' + str(number) for number, row in enumerate(rows)}
    lines = ['# Gradle module dependency candidates', '',
             'Generated from static Gradle declarations. Every module and edge is pending review and does not update the reviewed module catalog.', '',
             '```mermaid', 'graph LR']
    for row in rows:
        lines.append('    ' + node_ids[row['build_id']] + '["' + _mermaid_label(row['build_id'] + '<br/>' + row['root']) + '"]')
    for edge in result['edges']:
        if edge['from'] in node_ids and edge['to'] in node_ids:
            lines.append('    ' + node_ids[edge['from']] + ' -. "candidate ' + _mermaid_label(edge['configuration']) + '" .-> ' + node_ids[edge['to']])
    lines += ['```', '', '## Candidates', '']
    lines += ['- ' + row['build_id'] + ': root=' + row['root'] + '; registered=' +
              (', '.join(row['registered_module_ids']) or 'none') + '; evidence=' + ', '.join(row['evidence_refs']) for row in rows] or ['- None discovered.']
    lines += ['', '## Parsing gaps', ''] + (['- ' + gap for gap in result['gaps']] or ['- None recorded.'])
    lines += ['', '## Evidence boundary', ''] + ['- ' + limit for limit in result['limits']]
    write(base / 'candidates.md', '\n'.join(lines) + '\n')
    return result


def load_gradle_candidates(root):
    path = safe(root, '.agent-workflow/modules/candidates.json')
    doc = read(path)
    if (not isinstance(doc, dict) or doc.get('schema_version') != 1
            or doc.get('kind') != 'gradle_static_candidates' or doc.get('status') != 'candidate_only'):
        raise ValueError('candidate artifact identity/status is invalid')
    if not isinstance(doc.get('source_files'), dict) or not isinstance(doc.get('modules'), list) or not isinstance(doc.get('edges'), list):
        raise ValueError('candidate artifact shape is invalid')
    for name, expected in doc['source_files'].items():
        path_name(name); source = safe(root, name)
        if not source.is_file() or source.is_symlink() or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError('candidate evidence is stale: ' + name)
    ids = set()
    for row in doc['modules']:
        if (not isinstance(row, dict) or not isinstance(row.get('build_id'), str) or row['build_id'] in ids
                or not isinstance(row.get('root'), str) or row.get('status') != 'pending_review'
                or not isinstance(row.get('registered_module_ids'), list)):
            raise ValueError('candidate module is invalid or duplicated')
        ids.add(row['build_id']); path_name(row['root'])
    for row in doc['edges']:
        if (not isinstance(row, dict) or row.get('from') not in ids or row.get('to') not in ids
                or row.get('status') != 'candidate' or not isinstance(row.get('configuration'), str)):
            raise ValueError('candidate edge is invalid')
    if not isinstance(doc.get('gaps'), list) or not isinstance(doc.get('limits'), list):
        raise ValueError('candidate gaps/limits are invalid')
    return doc


def project_graph(root, index=None):
    """Build a deterministic graph from declared modules and confirmed feature scopes."""
    root = root.resolve(); index = index or catalog(root)
    nodes = [{'id': 'module:' + row['id'], 'kind': 'module', 'label': row['id'], 'summary': row['summary']}
             for row in index['modules']]
    edges = []
    for row in index['modules']:
        for dep in row['depends_on']:
            edges.append({'from': 'module:' + row['id'], 'to': 'module:' + dep, 'relation': 'depends_on',
                          'status': 'declared', 'evidence_refs': ['.agent-workflow/modules/index.json']})
    capabilities, assignments, gaps = {}, {}, []
    features = root / '.agent-workflow/features'
    if features.exists():
        for folder in sorted(features.iterdir()):
            path = folder / 'spec/requirements.json'
            if not folder.is_dir() or not path.is_file():
                continue
            try:
                record = read(path)
            except (OSError, json.JSONDecodeError):
                gaps.append(folder.name + ': unreadable feature record')
                continue
            feature = record.get('feature') if isinstance(record, dict) else None
            if not isinstance(feature, dict):
                gaps.append(folder.name + ': invalid feature record')
                continue
            scope = feature.get('module_scope')
            if not isinstance(scope, dict) or scope.get('status') != 'confirmed':
                if feature.get('modules'):
                    gaps.append(folder.name + ': module labels have no confirmed capability roles')
                continue
            capability = scope.get('capability', {})
            cid, name = capability.get('id'), capability.get('name')
            if not isinstance(cid, str) or not isinstance(name, str):
                gaps.append(folder.name + ': invalid confirmed capability')
                continue
            previous = capabilities.setdefault(cid, {'id': 'capability:' + cid, 'kind': 'capability',
                                                       'label': name, 'feature_ids': []})
            if previous['label'] != name:
                gaps.append(cid + ': conflicting capability names')
            previous['feature_ids'].append(folder.name)
            rows = scope.get('assignments')
            if not isinstance(rows, list):
                gaps.append(folder.name + ': invalid module assignments')
                continue
            for row in rows:
                if (not isinstance(row, dict) or row.get('module_id') not in {m['id'] for m in index['modules']}
                        or row.get('role') not in {'owner', 'host', 'provider', 'consumer', 'shared'}
                        or not isinstance(row.get('responsibility'), str)
                        or not isinstance(row.get('evidence_refs'), list)
                        or any(not isinstance(ref, str) for ref in row.get('evidence_refs', []))):
                    gaps.append(folder.name + ': invalid or unknown module assignment')
                    continue
                key = (cid, row['module_id'], row.get('role'))
                edge = assignments.setdefault(key, {'from': 'capability:' + cid, 'to': 'module:' + row['module_id'],
                    'relation': row.get('role'), 'status': 'confirmed', 'feature_ids': [], 'responsibilities': [],
                    'evidence_refs': []})
                edge['feature_ids'].append(folder.name)
                if row.get('responsibility') not in edge['responsibilities']:
                    edge['responsibilities'].append(row.get('responsibility'))
                edge['evidence_refs'] = sorted(set(edge['evidence_refs']) | set(row.get('evidence_refs', [])))
    for node in capabilities.values():
        node['feature_ids'].sort()
    for edge in assignments.values():
        edge['feature_ids'].sort()
    nodes.extend(capabilities[key] for key in sorted(capabilities))
    edges.extend(assignments[key] for key in sorted(assignments))
    candidate_path = root / '.agent-workflow/modules/candidates.json'
    if candidate_path.is_file():
        try:
            candidate_doc = load_gradle_candidates(root)
            candidate_nodes = {}
            registered_ids = {row['id'] for row in index['modules']}
            extra_nodes, extra_edges = [], []
            for row in candidate_doc.get('modules', []):
                matches = row.get('registered_module_ids', [])
                target = 'module:' + matches[0] if len(matches) == 1 and matches[0] in registered_ids else 'candidate:' + row['build_id']
                candidate_nodes[row['build_id']] = target
                if target.startswith('candidate:'):
                    extra_nodes.append({'id': target, 'kind': 'module_candidate', 'label': row['build_id'],
                                        'root': row['root'], 'status': 'pending_review'})
            for row in candidate_doc.get('edges', []):
                if row.get('from') in candidate_nodes and row.get('to') in candidate_nodes:
                    extra_edges.append({'from': candidate_nodes[row['from']], 'to': candidate_nodes[row['to']],
                                        'relation': row.get('configuration', 'depends_on'), 'status': 'candidate',
                                        'evidence_refs': row.get('evidence_refs', [])})
            nodes.extend(extra_nodes); edges.extend(extra_edges)
            gaps.extend('Gradle candidate: ' + gap for gap in candidate_doc.get('gaps', []))
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            gaps.append('Gradle candidate artifact is invalid: ' + str(exc))
    return {'schema_version': 1, 'nodes': nodes, 'edges': edges, 'gaps': sorted(set(gaps)),
            'limits': ['Declared build/module relationships are not a complete runtime call graph.',
                       'Capability roles come only from confirmed feature scope records.',
                       'Dashed Gradle relationships are unconfirmed static candidates.']}


def render_graph(root, index=None):
    root = root.resolve(); index = index or catalog(root); graph = project_graph(root, index)
    base = safe(root, '.agent-workflow/modules')
    write(base / 'graph.json', json.dumps(graph, ensure_ascii=False, indent=2) + '\n')
    ids = {node['id']: ('N' + str(number)) for number, node in enumerate(graph['nodes'])}
    lines = ['# Project module and capability graph', '',
             'Generated from the reviewed module catalog and confirmed feature scopes. It is an impact-navigation aid, not a complete runtime call graph.', '',
             '```mermaid', 'graph LR']
    for node in graph['nodes']:
        suffix = '<br/>business capability' if node['kind'] == 'capability' else '<br/>code module'
        lines.append('    ' + ids[node['id']] + '["' + _mermaid_label(node['label']) + suffix + '"]')
    for edge in graph['edges']:
        arrow = ' -. "candidate ' + _mermaid_label(edge['relation']) + '" .-> ' if edge.get('status') == 'candidate' else ' -->|"' + _mermaid_label(edge['relation']) + '"| '
        lines.append('    ' + ids[edge['from']] + arrow + ids[edge['to']])
    lines += ['```', '', '## Known gaps', '']
    lines += ['- ' + gap for gap in graph['gaps']] or ['- None recorded.']
    lines += ['', '## Evidence boundary', ''] + ['- ' + limit for limit in graph['limits']]
    write(base / 'graph.md', '\n'.join(lines) + '\n')
    overview = ['# Project module overview', '', index['shared_stack'], '',
                'Registered modules (not exhaustive discovery):', '']
    for module in index['modules']:
        overview += ['- ' + module['id'] + ': ' + module['summary'] + '; roots=' + ', '.join(module['roots']) + '; depends_on=' + ', '.join(module['depends_on'])]
    overview += ['', 'See graph.md for declared dependencies and confirmed business-capability roles.']
    write(base / 'index.md', '\n'.join(overview) + '\n')
    return graph


def render(root, index, module_id, doc):
    body = doc['body']; lines = ['# ' + module_id, '', 'Source reviewed at ' + doc['review']['revision'] + '; run module plan before reuse. Not runtime acceptance.', '']
    for section in SECTIONS:
        lines += ['## ' + section, '']
        lines += ['- ' + r['detail'] + ' (evidence: ' + ', '.join(r['evidence_files']) + ')' for r in body[section]]
    lines += ['', 'Related features: ' + ', '.join(body['feature_ids']), 'Gaps: ' + ('; '.join(body['gaps']) or 'none declared')]
    write(safe(root, '.agent-workflow/modules/' + module_id + '.md'), '\n'.join(lines) + '\n')
    render_graph(root, index)


def validate_modules(root, folder, req, stage):
    feature = req.get('feature', {})
    required = feature.get('module_context_required', False)
    if not isinstance(required, bool):
        return ['module_context_required must be boolean']
    workflow_version = feature.get('workflow_version', 1)
    if not isinstance(workflow_version, int) or isinstance(workflow_version, bool) or workflow_version < 1:
        return ['workflow_version must be a positive integer']
    catalog_exists = (root / '.agent-workflow/modules/index.json').exists()
    if stage != 'draft' and workflow_version >= 2 and catalog_exists:
        if 'module_context_required' not in feature:
            return ['module catalog exists: set module_context_required and select modules, or record module_context_note when not applicable']
        if not required and not isinstance(feature.get('module_context_note'), str):
            return ['module_context_note is required when the project catalog is not applicable']
        if not required and not feature.get('module_context_note', '').strip():
            return ['module_context_note is required when the project catalog is not applicable']
    if not required or stage == 'draft':
        return []
    try:
        rows = plan(root, feature.get('modules', []))
        return ['module context needs review: ' + r['module'] + ' (' + r['status'] + ')' for r in rows if r['status'] != 'current']
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return ['invalid module context: ' + str(exc)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['plan', 'review', 'graph', 'discover']); p.add_argument('root', type=Path)
    p.add_argument('--module', action='append'); p.add_argument('--feature')
    p.add_argument('--input', type=Path); p.add_argument('--digest')
    args = p.parse_args(); root = args.root.resolve()
    try:
        if args.action == 'discover':
            if args.module or args.feature or args.input or args.digest:
                raise ValueError('discover does not accept module, feature, input or digest')
            result = discover_gradle_candidates(root)
            print(json.dumps({'modules': len(result['modules']), 'edges': len(result['edges']),
                              'gaps': result['gaps'], 'status': result['status']}, ensure_ascii=False))
            return 0
        if args.action == 'graph':
            if args.module or args.feature or args.input or args.digest:
                raise ValueError('graph does not accept module, feature, input or digest')
            graph = render_graph(root)
            print(json.dumps({'nodes': len(graph['nodes']), 'edges': len(graph['edges']), 'gaps': graph['gaps']}, ensure_ascii=False))
            return 0
        selected = args.module or []
        if args.feature:
            if selected or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.feature):
                raise ValueError('use module selection or a valid feature, not both')
            selected = read(safe(root, '.agent-workflow/features/' + args.feature + '/spec/requirements.json'))['feature'].get('modules', [])
        if args.action == 'review':
            if len(selected) != 1 or not args.input or not args.digest:
                raise ValueError('review requires one module, input and captured digest')
            review(root, selected[0], read(args.input), args.digest)
        rows = plan(root, selected)
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0 if all(r['status'] == 'current' for r in rows) else 2
    except (OSError, ValueError, TypeError, KeyError) as exc:
        p.exit(1, 'ERROR: ' + str(exc) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
