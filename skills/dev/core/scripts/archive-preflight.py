#!/usr/bin/env python3
"""Prepare a reviewable archive report draft from existing workflow evidence."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from archive_git import report as git_record_report
from feature_lifecycle import ARCHIVE_DRAFT_MARKER, metadata, read_record


def read_json(path, default):
    if not path.exists():
        return default
    value = json.loads(path.read_text())
    return value


def cell(value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value if value is not None else '').replace('|', '\\|').replace('\n', '<br>')


def table(headers, rows):
    lines = ['| ' + ' | '.join(headers) + ' |', '|' + '|'.join('---' for _ in headers) + '|']
    lines += ['| ' + ' | '.join(cell(value) for value in row) + ' |' for row in rows]
    return lines


def regression_rows(record):
    dispositions = {row.get('candidate_id'): row for row in record.get('dispositions', []) if isinstance(row, dict)}
    rows = []
    for candidate in record.get('candidates', []):
        if not isinstance(candidate, dict):
            continue
        disposition = dispositions.get(candidate.get('id'), {})
        result = disposition.get('result', {}) if isinstance(disposition.get('result'), dict) else {}
        rows.append((candidate.get('id', ''),
                     {'modules': candidate.get('matched_modules', []), 'paths': candidate.get('matched_paths', [])},
                     disposition.get('action', 'pending'), result.get('status', '')))
    return rows


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)


def source_disposition(root, folder, req):
    rows = []
    top = git(root, 'rev-parse', '--show-toplevel')
    git_available = top.returncode == 0 and Path(top.stdout.strip()).resolve() == root.resolve()
    paths = req.get('feature', {}).get('prd_paths') or []
    for rel in paths:
        if not isinstance(rel, str) or not rel:
            rows.append({'path': cell(rel), 'state': 'invalid'})
            continue
        path = folder / rel
        try:
            resolved = path.resolve()
            resolved.relative_to(folder)
        except (OSError, ValueError):
            rows.append({'path': rel, 'state': 'outside_or_invalid'})
            continue
        if not path.is_file() or path.is_symlink():
            state = 'missing'
        else:
            try:
                project_rel = path.relative_to(root).as_posix()
            except ValueError:
                state = 'outside_project'
            else:
                if not git_available:
                    state = 'git_unavailable'
                elif git(root, 'ls-files', '--error-unmatch', '--', ':(literal)' + project_rel).returncode == 0:
                    state = 'tracked'
                elif git(root, 'check-ignore', '-q', '--', project_rel).returncode == 0:
                    state = 'ignored_by_policy'
                else:
                    state = 'untracked'
        rows.append({'path': rel, 'state': state})
    return rows


def module_hints(root, code_paths):
    roots = sorted({path.split('/', 1)[0] for path in code_paths if isinstance(path, str) and path and '/' in path})
    index_path = root / '.agent-workflow/modules/index.json'
    candidates = []
    if index_path.is_file() and not index_path.is_symlink():
        index = json.loads(index_path.read_text())
        for module in index.get('modules', []) if isinstance(index, dict) else []:
            if not isinstance(module, dict) or not isinstance(module.get('id'), str) or not isinstance(module.get('roots'), list):
                continue
            if any(any(path == base or path.startswith(base.rstrip('/') + '/') for base in module['roots'] if isinstance(base, str))
                   for path in code_paths if isinstance(path, str)):
                candidates.append(module['id'])
    return sorted(set(candidates)), roots


def run_readonly(script, root, feature_id, *prefix):
    command = [sys.executable, str(Path(__file__).with_name(script)), *prefix, str(root), feature_id]
    result = subprocess.run(command, capture_output=True, text=True)
    return {'status': 'passed' if result.returncode == 0 else 'failed', 'returncode': result.returncode,
            'output': (result.stdout + result.stderr).strip()}


def build_report(root, folder, req, revision, diagnostics):
    feature = req['feature']
    requirements = req.get('requirements', [])
    tasks = read_json(folder / 'tasks.json', {}).get('tasks', [])
    task_review = read_json(folder / 'task-review.json', {})
    decisions = read_json(folder / 'decisions.json', {}).get('decisions', [])
    trace = read_json(folder / 'traceability.json', {})
    fixes = read_json(folder / 'fixes.json', {}).get('fixes', [])
    regression = read_json(folder / 'regression-review.json', {})
    quality = read_json(root / '.agent-workflow/project-baseline/quality-report.json', {})
    lines = [f"# Delivery report — {feature['id']}", '', ARCHIVE_DRAFT_MARKER,
             '', 'Status: **DRAFT — REVIEW REQUIRED**', '',
             'This draft is assembled from existing workflow records. Review every section, replace the draft status, and add no conclusion that the cited evidence does not support.', '',
             '## Identity', '', f"- Feature: {feature.get('title', '')}", f"- Product status: {feature.get('status', '')}",
             f"- Proposed accepted revision: {revision or 'not supplied'}",
             f"- Modules: {', '.join(feature.get('modules', [])) or 'unclassified'}", '',
             '## Source applicability', '']
    lines += table(['Source', 'Status', 'Note'], [(name, status, feature.get('source_notes', {}).get(name, ''))
                   for name, status in sorted(feature.get('source_status', {}).items())])
    lines += ['', '## Requirements', '']
    lines += table(['ID', 'Status', 'Title', 'Acceptance criteria'], [(r.get('id',''), r.get('status',''), r.get('title',''), r.get('acceptance_criteria', [])) for r in requirements])
    lines += ['', '## Tasks', '']
    lines += table(['ID', 'Status', 'Title', 'Existing evidence'], [(t.get('id',''), t.get('status',''), t.get('title',''), t.get('test_evidence', [])) for t in tasks])
    if isinstance(task_review, dict) and isinstance(task_review.get('current'), dict):
        reviewed = task_review.get('review', {}) if isinstance(task_review.get('review'), dict) else {}
        lines += ['', '- Task semantics: ' + ('current' if reviewed.get('digest') == task_review['current'].get('digest') else 'pending'),
                  '- Superseded task reviews: ' + str(len(task_review.get('history', [])) if isinstance(task_review.get('history', []), list) else 'invalid')]
    lines += ['', '## Decisions', '']
    lines += table(['ID', 'Status', 'Chosen'], [(d.get('id',''), d.get('status',''), d.get('chosen','')) for d in decisions]) if decisions else ['No decisions recorded.']
    tests = trace.get('tests', []) if isinstance(trace, dict) else []
    lines += ['', '## Requirement tests and manual evidence', '']
    lines += table(['ID', 'Status', 'Description', 'Existing note'], [(t.get('id',''), t.get('status',''), t.get('description',''), t.get('note','')) for t in tests]) if tests else ['No traceability test rows recorded.']
    lines += ['', '## Quality gates', '']
    results = quality.get('results', []) if isinstance(quality, dict) else []
    if results:
        lines += [f"- Report tested at: {quality.get('tested_at', '')}", f"- Recorded Git HEAD: {quality.get('project_snapshot', {}).get('git_head', '')}", '']
        lines += table(['Gate', 'Status', 'Test IDs', 'Command'], [(g.get('name',''), g.get('status',''), g.get('test_ids', []), g.get('command', [])) for g in results])
    else:
        lines += ['No quality report results recorded.']
    lines += ['', '## Fixes', '']
    lines += table(['ID', 'Status', 'Kind', 'Tested revision'], [(f.get('id',''), f.get('status',''), f.get('kind',''), f.get('tested_revision','')) for f in fixes]) if fixes else ['No fixes recorded.']
    lines += ['', '## Historical regression review', '']
    if isinstance(regression, dict) and isinstance(regression.get('candidates'), list):
        rows = regression_rows(regression)
        lines += table(['Historical fix', 'Match', 'Action', 'Result'], rows) if rows else ['No related verified fixes were found from registered modules and paths.']
        lines += ['', f"Superseded audit entries: {len(regression.get('history', [])) if isinstance(regression.get('history', []), list) else 'invalid'}."]
    else:
        lines += ['Historical regression review not adopted for this feature.']
    lines += ['', '## Archive preflight', '',
              f"- Structural check: {diagnostics['validation']['status']} (rc={diagnostics['validation']['returncode']})",
              f"- Delivery audit: {diagnostics['audit']['status']} (rc={diagnostics['audit']['returncode']})",
              f"- Impact checklist: {'present' if (folder / 'impact.json').is_file() else 'missing; do not backfill historical evidence solely to remove this note'}",
              f"- Module candidates from registered catalog: {', '.join(diagnostics['module_candidates']) or 'none'}",
              f"- Code path roots for Agent review: {', '.join(diagnostics['code_path_roots']) or 'none'}", '',
              '### Source portability', '']
    lines += table(['Feature-relative source', 'Git state'], [(row['path'], row['state']) for row in diagnostics['sources']]) if diagnostics['sources'] else ['No prd_paths recorded.']
    lines += ['', '### Known limitations requiring review', '',
              '- Confirm that selected gates actually cover this feature; a passed unrelated gate is not behavioral evidence.',
              '- Confirm manual observations and the accepted revision from original evidence.',
              '- Decide explicitly whether ignored or untracked sources may be shared; this draft does not stage or upload them.',
              '- Resolve missing module labels before archive when they are needed for historical lookup.', '',
              '## Reviewer conclusion', '',
              'Replace this section and remove the draft marker only after checking the cited records. State accepted scope, evidence limits, remaining risk, and whether archive may proceed.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('feature_id')
    parser.add_argument('--revision', default='')
    parser.add_argument('--evidence', default='delivery-report.md')
    args = parser.parse_args()
    root = args.project.resolve()
    record, _, req = read_record(root, args.feature_id)
    folder = record.parent.parent
    metadata(req['feature'])
    report = folder / args.evidence
    if Path(args.evidence).is_absolute() or not report.resolve().is_relative_to(folder) or report.resolve() != report or report.is_symlink():
        raise ValueError('Evidence must be a regular feature-local report path')
    trace = read_json(folder / 'traceability.json', {})
    code_paths = [path for link in trace.get('links', []) if isinstance(link, dict)
                  for path in link.get('code', []) if isinstance(path, str)] if isinstance(trace, dict) else []
    candidates, path_roots = module_hints(root, code_paths)
    diagnostics = {
        'module_candidates': candidates,
        'code_path_roots': path_roots,
        'sources': source_disposition(root, folder, req),
        'validation': run_readonly('validate-feature.py', root, args.feature_id, '--stage', 'check'),
        'audit': run_readonly('audit-delivery.py', root, args.feature_id),
    }
    created = False
    if not report.exists() or not report.read_bytes().strip():
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(build_report(root, folder, req, args.revision.strip(), diagnostics))
        created = True
    diagnostics.update(report=report.relative_to(folder).as_posix(), created=created,
                       review_required=ARCHIVE_DRAFT_MARKER in report.read_text(),
                       modules=req['feature'].get('modules', []), git_record_status=git_record_report(root, args.feature_id, req['feature'].get('modules', [])))
    print('ARCHIVE_PREFLIGHT: ' + json.dumps(diagnostics, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        print('ARCHIVE_PREFLIGHT_ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(1)
