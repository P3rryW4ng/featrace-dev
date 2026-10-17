#!/usr/bin/env python3
"""Read-only audit of the latest selected checks for one feature."""
import argparse
import json
from pathlib import Path
import re
import sys

from project import quality_selection, quality_comparison, quality_snapshot, validate_gates
from revisions import binding
from verification import validate_verification


def audit(root, feature_id):
    errors = []
    feature = root / '.agent-workflow' / 'features' / feature_id
    baseline = root / '.agent-workflow' / 'project-baseline'
    try:
        req = json.loads((feature / 'spec' / 'requirements.json').read_text())
        fixes_path = feature / 'fixes.json'
        from fixes import read_fixes
        fixes = read_fixes(feature, feature_id)
        report = json.loads((baseline / 'quality-report.json').read_text())
        selected_config = json.loads((baseline / 'quality-gates.json').read_text())
        validate_gates(root, selected_config)
    except (OSError, ValueError) as exc:
        return ['required feature record or quality report missing/invalid: ' + str(exc)]
    if (not isinstance(req, dict) or req.get('feature', {}).get('id') != feature_id or
            not isinstance(fixes, dict) or fixes.get('feature_id') != feature_id or
            not isinstance(fixes.get('fixes'), list)):
        return ['feature or fix record does not match requested ID']
    if not isinstance(report, dict) or not isinstance(report.get('results'), list):
        return ['quality report must contain results']
    if selected_config.get('selection_feature_id') != feature_id or report.get('quality_selection') != quality_selection(selected_config):
        errors.append('quality report or selected gates are not bound to this feature; reselect applicable gates and rerun check')
    try:
        current = quality_snapshot(root)
    except (OSError, ValueError, TypeError) as exc:
        return ['cannot inspect current project snapshot: ' + str(exc)]
    comparison = quality_comparison(root, report.get('project_snapshot'), current)
    if comparison['state'] != 'same':
        errors.append('quality report is stale or unknown for the current check inputs: ' + json.dumps(comparison, ensure_ascii=False))
    execution_identity = report.get('input_comparison')
    if not isinstance(execution_identity, dict) or execution_identity.get('state') != 'same':
        errors.append('quality execution did not certify stable inputs; legacy/missing identity needs a fresh applicable check')
    if req.get('feature', {}).get('baseline') is not None:
        try:
            if report.get('feature_baseline') != binding(root, feature_id):
                errors.append('quality report is not bound to the current requirement baseline; rerun check --feature')
        except (OSError, ValueError, TypeError, KeyError) as exc:
            errors.append('invalid requirement baseline: ' + str(exc))
    results = report['results']
    if not results:
        errors.append('quality report has no executed checks')
    selected = set()
    for result in results:
        if not isinstance(result, dict) or result.get('status') != 'passed':
            errors.append('quality report contains a failed or unavailable check')
            continue
        ids = result.get('test_ids', [])
        if not isinstance(ids, list) or any(not isinstance(x, str) or not x.strip() for x in ids):
            errors.append('quality result has invalid test_ids')
        else:
            selected.update(ids)
    for fix in fixes['fixes']:
        if not isinstance(fix, dict):
            errors.append('invalid fix entry'); continue
        if fix.get('status') != 'verified':
            continue  # Closure and unfinished work are handled by validate-feature.py.
        regression = fix.get('regression_test_ids', [])
        if not isinstance(regression, list) or any(not isinstance(x, str) for x in regression):
            errors.append('%s has invalid regression_test_ids' % fix.get('id', '?'))
            continue
        for test in regression:
            if test not in selected:
                try:
                    from regression_execution import current_evidence
                    if current_evidence(root, feature, fix, test):
                        continue
                except (OSError, ValueError, TypeError, KeyError) as exc:
                    errors.append('%s invalid device regression evidence: %s' % (fix.get('id', '?'), exc))
                errors.append('%s regression test not selected by a passed check: %s' % (fix.get('id', '?'), test))
    errors.extend(validate_verification(root, feature, req, 'check'))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('feature_id')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', args.feature_id):
        parser.error('invalid feature ID')
    errors = audit(args.root.resolve(), args.feature_id)
    for error in errors:
        print('ERROR: ' + error)
    if errors:
        return 1
    print('DELIVERY_EVIDENCE_CURRENT: selected checks passed and verified-fix tests have current gate/device execution evidence')
    print('Scope: Git business tree/index/worktree, nonignored untracked files, manifests and declared inputs; ignored/external inputs and runtime environment require explicit scope. Identity is not semantic coverage or package provenance.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
