#!/usr/bin/env python3
"""Report the actual inputs available at the start of feature verification."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from prd_intake import source_path


def read_json(path):
    return json.loads(path.read_text())


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)


def changed_paths(root):
    changed = git(root, 'diff', '--name-only', '-z', 'HEAD').split(b'\0')
    untracked = git(root, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0')
    return sorted({p.decode('utf-8', 'surrogateescape') for p in changed + untracked if p})


def collect(root, feature_id):
    folder = root / '.agent-workflow' / 'features' / feature_id
    if folder.is_symlink() or not folder.is_dir() or not folder.resolve().is_relative_to(root):
        raise ValueError('feature directory missing or unsafe')
    requirements = read_json(folder / 'spec/requirements.json')
    feature = requirements.get('feature', {})
    if not isinstance(feature, dict) or feature.get('id') != feature_id:
        raise ValueError('feature record does not match requested ID')

    issues = []
    try:
        head = git(root, 'rev-parse', 'HEAD').decode().strip()
        dirty = changed_paths(root)
    except subprocess.CalledProcessError as exc:
        raise ValueError('cannot identify project Git revision/worktree') from exc
    if dirty:
        issues.append('worktree_changed_paths_require_review')

    intake_path = folder / 'spec/prd-intake.json'
    intake = read_json(intake_path) if intake_path.exists() else None
    declared = feature.get('prd_paths')
    if declared is None and isinstance(feature.get('prd_path'), str):
        declared = [feature['prd_path']]
    # Older accepted workspaces indexed sources through intake units, before
    # feature.prd_paths and intake.sources became required for new features.
    if declared is None and isinstance(intake, dict) and 'sources' not in intake:
        units = intake.get('units')
        if isinstance(units, list):
            declared = sorted({u['source'] for u in units if isinstance(u, dict)
                               and isinstance(u.get('source'), str) and u['source']})
    if not isinstance(declared, list) or any(not isinstance(p, str) or not p for p in declared):
        declared = []
        issues.append('feature_source_index_missing_or_invalid')
    registered = None
    if intake is None:
        issues.append('prd_intake_missing')
    elif not isinstance(intake, dict) or intake.get('feature_id') != feature_id:
        issues.append('prd_intake_source_index_invalid')
    else:
        source_rows = intake.get('sources')
        legacy_units = intake.get('units')
        if source_rows is None and isinstance(legacy_units, list):
            source_rows = [{'path': row.get('source')} for row in legacy_units if isinstance(row, dict)]
        if not isinstance(source_rows, list):
            issues.append('prd_intake_source_index_invalid')
        else:
            registered = [row.get('path') for row in source_rows if isinstance(row, dict)]
            if len(registered) != len(source_rows) or any(not isinstance(p, str) or not p for p in registered):
                issues.append('prd_intake_source_index_invalid')
                registered = None
            elif set(registered) != set(declared) or (intake.get('sources') is not None and len(registered) != len(declared)):
                issues.append('source_indices_disagree')

    indexed = set(declared + (registered or []))
    source_dir = folder / 'sources'
    supplementary = []
    if source_dir.is_dir() and not source_dir.is_symlink():
        supplementary = [p.relative_to(folder).as_posix() for p in source_dir.rglob('*')
                         if p.is_file() or p.is_symlink()]
    paths = sorted(indexed.union(supplementary))
    if not paths:
        issues.append('no_source_paths_identified')
    sources = []
    for relative in paths:
        row = {'path': relative, 'indexed': relative in indexed}
        try:
            if source_dir.is_symlink():
                raise ValueError('sources directory is a symlink; refusing to follow it')
            path = source_path(folder, relative)
            data = path.read_bytes()
            row.update(state='readable', bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        except (OSError, ValueError, TypeError, KeyError) as exc:
            row.update(state='unavailable', reason=str(exc))
            issues.append('source_unavailable')
        sources.append(row)

    report_path = root / '.agent-workflow/project-baseline/quality-report.json'
    quality = {'state': 'missing'}
    if report_path.is_symlink():
        quality = {'state': 'invalid', 'reason': 'quality report is a symlink; refusing to follow it'}
        issues.append('quality_report_invalid')
    elif report_path.exists():
        try:
            report = read_json(report_path)
            if not isinstance(report, dict):
                raise ValueError('report must be an object')
            snapshot = report.get('project_snapshot')
            if not isinstance(snapshot, dict):
                raise ValueError('project_snapshot missing or invalid')
            quality = {'state': 'present', 'tested_at': report.get('tested_at'),
                       'recorded_git_head': snapshot.get('git_head'),
                       'sha256': hashlib.sha256(report_path.read_bytes()).hexdigest()}
            if quality['recorded_git_head'] != head:
                issues.append('quality_report_revision_differs_from_head_check_currency')
        except (OSError, ValueError, TypeError) as exc:
            quality = {'state': 'invalid', 'reason': str(exc)}
            issues.append('quality_report_invalid')
    else:
        issues.append('quality_report_missing_before_run')

    return {'feature_id': feature_id, 'git_head': head, 'worktree_changed_paths': dirty,
            'source_status_claims': feature.get('source_status', {}),
            'sources': sources, 'quality_report': quality,
            'issues_to_review': sorted(set(issues)),
            'status': 'review_required' if issues else 'inputs_identified',
            'note': 'Read-only input inventory; not semantic review, test execution, or delivery approval.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('feature_id')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.feature_id):
        parser.error('invalid feature ID')
    try:
        root = args.root.resolve()
        print(json.dumps(collect(root, args.feature_id), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print('VERIFY_INPUTS_ERROR: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
