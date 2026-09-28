import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from intake_helpers import attach_intake, CORE
from impact import MECHANISMS
import task_review
import regression_review

spec = importlib.util.spec_from_file_location('parallel_build', CORE / 'parallel-build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class ParallelBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'project with spaces'; self.root.mkdir()
        self.run = Path(self.temp.name) / 'attempt'
        self.folder = self.root / '.agent-workflow/features/FEAT-001'
        (self.folder / 'sources').mkdir(parents=True); (self.folder / 'spec').mkdir()
        (self.folder / 'sources/prd-original.txt').write_text('Provide independent uppercase and lowercase transformations.')
        self.req = {'feature': {'id': 'FEAT-001', 'status': 'provisional',
                    'source_status': {'prd': 'present', 'figma': 'not_applicable', 'api': 'not_applicable'},
                    'source_notes': {'figma': 'local functions', 'api': 'local functions'}},
                    'requirements': [{'id': 'R-1', 'title': 'Case conversion',
                    'statement': 'Return uppercase and lowercase text using separate functions', 'status': 'confirmed',
                    'sources': [{'type': 'prd', 'ref': 'sources/prd-original.txt'}],
                    'acceptance_criteria': ['upper abc gives ABC', 'lower ABC gives abc'],
                    'tasks': ['T-UP', 'T-LOW'], 'tests': ['TEST-UP', 'TEST-LOW'], 'assumptions': []}]}
        self.tasks = {'feature_id': 'FEAT-001', 'tasks': [
            {'id': t, 'title': t, 'status': 'planned', 'requirement_ids': ['R-1']} for t in ['T-UP', 'T-LOW']]}
        self.put('tasks.json', self.tasks); self.put('decisions.json', {'feature_id': 'FEAT-001', 'decisions': []})
        self.put('traceability.json', {'feature_id': 'FEAT-001', 'links': [
            {'requirement_id': 'R-1', 'tasks': ['T-UP', 'T-LOW'], 'tests': ['TEST-UP', 'TEST-LOW'], 'code': ['upper.py', 'lower.py']}]})
        attach_intake(self.folder, self.req)
        (self.root / '.gitignore').write_text('.agent-workflow/\n__pycache__/\n')
        for name in ['upper', 'lower']:
            (self.root / (name + '.py')).write_text('def convert(value):\n    return value\n')
        (self.root / 'tests').mkdir()
        for name, value, expected in [('upper', 'abc', 'ABC'), ('lower', 'ABC', 'abc')]:
            (self.root / ('tests/test_' + name + '.py')).write_text(
                'import unittest\nfrom ' + name + ' import convert\nclass ConversionTest(unittest.TestCase):\n'
                '    def test_conversion(self):\n        self.assertEqual(convert(' + repr(value) + '), ' + repr(expected) + ')\n')
        self.git(self.root, 'init', '-q'); self.git(self.root, 'config', 'user.name', 'Fixture')
        self.git(self.root, 'config', 'user.email', 'fixture@example.invalid')
        self.git(self.root, 'add', '.'); self.git(self.root, 'commit', '-qm', 'baseline')
        self.base = self.git(self.root, 'rev-parse', 'HEAD').strip()
        self.put('impact.json', {'schema_version': 1, 'feature_id': 'FEAT-001', 'base_revision': self.base,
            'allowed_paths': ['upper.py', 'lower.py'], 'inspected_paths': ['upper.py', 'lower.py'],
            'excluded_changes': {}, 'mechanisms': {k: {'status': 'reviewed', 'evidence': 'Synthetic independent files reviewed'} for k in MECHANISMS},
            'behaviors': [{'id': 'B-1', 'kind': 'change', 'statement': 'Case conversion', 'basis': 'R-1', 'requirement_ids': ['R-1']}]})
        task_review.sync(self.root, 'FEAT-001')
        task_review.review(self.root, 'FEAT-001', 'synthetic-fixture-reviewer',
                           'Compared both task meanings with confirmed R-1 and the synthetic source.',
                           ['T-UP', 'T-LOW'], ['R-1'], ['R-1 statement/AC; sources/prd-original.txt:1'])
        regression_review.sync(self.root, 'FEAT-001')
        self.plan = {'schema_version': 1, 'independence': {'reason': 'Two separate pure entry points',
            'evidence': ['upper.py:1-2', 'lower.py:1-2'], 'interfaces': ['convert(str)->str'],
            'preserve': ['Do not change the other entry point']},
            'tasks': [{'task_id': tid, 'allowed_paths': [name + '.py'], 'depends_on': [],
                'checks': [[sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_' + name + '.py']]}
                for tid, name in [('T-UP', 'upper'), ('T-LOW', 'lower')]],
            'integration_checks': [[sys.executable, '-m', 'unittest', 'discover', '-s', 'tests']], 'timeout_seconds': 10}

    def put(self, name, value):
        (self.folder / name).write_text(json.dumps(value))

    def git(self, root, *args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True, stderr=subprocess.PIPE)

    def prepare(self):
        return build.prepare(self.root, 'FEAT-001', self.plan, self.run)

    def worker(self, tid):
        return self.run / 'workers' / tid

    def implement(self):
        for tid, name in [('T-UP', 'upper'), ('T-LOW', 'lower')]:
            (self.worker(tid) / (name + '.py')).write_text('def convert(value):\n    return value.' + name + '()\n')

    def ready(self):
        self.prepare(); self.implement()
        for tid in ['T-UP', 'T-LOW']:
            self.assertEqual(build.finish(self.run, tid, 'ready', 'Implemented synthetic task')['status'], 'ready')

    def test_two_isolated_workers_integrate_and_primary_records_stay_unchanged(self):
        before = build.candidate_state(self.root); self.ready()
        self.assertEqual((self.worker('T-UP') / 'lower.py').read_text(), (self.root / 'lower.py').read_text())
        result = build.integrate(self.run)
        self.assertEqual(result['status'], 'candidate_checks_passed', result)
        self.assertTrue(all(c['returncode'] == 0 for c in result['checks']))
        self.assertEqual(before, build.candidate_state(self.root))
        self.assertEqual(self.git(self.root, 'rev-parse', 'HEAD').strip(), self.base)
        self.assertEqual(build.load(self.folder / 'tasks.json'), self.tasks)
        self.assertIn('.upper()', (self.run / 'integration/upper.py').read_text())
        self.assertIn('.lower()', (self.run / 'integration/lower.py').read_text())

    def test_ownership_conflict_and_dependencies_rejected_before_worktree_creation(self):
        self.plan['tasks'][1]['allowed_paths'] = ['upper.py']
        with self.assertRaisesRegex(ValueError, 'ownership conflict'): self.prepare()
        self.assertFalse(self.run.exists())
        self.plan['tasks'][1]['allowed_paths'] = ['lower.py']; self.plan['tasks'][1]['depends_on'] = ['T-UP']
        with self.assertRaisesRegex(ValueError, 'dependent'): self.prepare()

    def test_legacy_warning_cannot_bypass_parallel_scope(self):
        req = build.load(self.folder / 'spec/requirements.json')
        for marker in ['task_review_required', 'history_regression_required']:
            req['feature'].pop(marker, None)
        self.put('spec/requirements.json', req)
        for name in ['task-review.json', 'regression-review.json']:
            (self.folder / name).unlink()
        ordinary = subprocess.run([sys.executable, str(CORE / 'validate-feature.py'),
                                   str(self.root), 'FEAT-001', '--stage', 'develop'], capture_output=True, text=True)
        self.assertEqual(ordinary.returncode, 0, ordinary.stdout + ordinary.stderr)
        self.assertIn('WARNING', ordinary.stdout)
        before = build.candidate_state(self.root)
        with self.assertRaisesRegex(ValueError, 'parallel Scope review missing: task-review.json, regression-review.json'):
            self.prepare()
        self.assertFalse(self.run.exists())
        self.assertEqual(before, build.candidate_state(self.root))

    def test_present_but_unreviewed_or_stale_scope_still_blocks(self):
        tasks = build.load(self.folder / 'tasks.json')
        tasks['tasks'][0]['description'] = 'Return lowercase despite uppercase requirement'
        self.put('tasks.json', tasks)
        with self.assertRaisesRegex(ValueError, 'develop prerequisites failed'):
            self.prepare()
        self.assertFalse(self.run.exists())
        task_review.sync(self.root, 'FEAT-001')
        with self.assertRaisesRegex(ValueError, 'task semantics need review'):
            self.prepare()
        self.assertFalse(self.run.exists())

    def test_noncanonical_paths_and_malformed_record_rejected(self):
        self.plan['tasks'][0]['allowed_paths'] = ['upper.py', './lower.py']
        with self.assertRaisesRegex(ValueError, 'canonical ownership'): self.prepare()
        self.assertFalse(self.run.exists())
        with self.assertRaisesRegex(ValueError, 'must be an object'): build.unseal([])

    def test_frozen_inventory_addition_rejected(self):
        self.prepare()
        (self.run / 'inputs/.agent-workflow/features/FEAT-001/sources/added.txt').write_text('New authority')
        with self.assertRaisesRegex(ValueError, 'frozen authority'): build.preflight(self.run)

    def test_worker_index_changes_during_or_after_checks_rejected(self):
        self.plan['tasks'][0]['checks'].append(['git', 'add', 'upper.py'])
        self.prepare(); self.implement()
        result = build.finish(self.run, 'T-UP', 'ready', 'Implementation')
        self.assertEqual(result['status'], 'failed')
        self.assertIn('checks changed', result['error'])

    def test_worker_index_change_after_return_rejected(self):
        self.ready(); self.git(self.worker('T-UP'), 'add', 'upper.py')
        with self.assertRaisesRegex(ValueError, 'changed after tests'): build.integrate(self.run)

    def test_worker_commit_and_missing_return_rejected(self):
        self.prepare(); self.implement()
        build.finish(self.run, 'T-UP', 'ready', 'Implementation')
        with self.assertRaises(FileNotFoundError): build.integrate(self.run)
        self.assertFalse((self.run / 'integration').exists())
        self.git(self.worker('T-LOW'), 'add', 'lower.py')
        self.git(self.worker('T-LOW'), 'commit', '-qm', 'Unsupported worker commit')
        result = build.finish(self.run, 'T-LOW', 'ready', 'Committed task')
        self.assertEqual(result['status'], 'failed'); self.assertIn('HEAD changed', result['error'])

    def test_real_apply_conflict_preserves_candidate(self):
        self.ready(); before = build.candidate_state(self.root); original_git = build.git
        def inject(root, *args, **kwargs):
            value = original_git(root, *args, **kwargs)
            if args[:2] == ('worktree', 'add'):
                (self.run / 'integration/upper.py').write_text('Concurrent external edit\n')
            return value
        with patch.object(build, 'git', side_effect=inject): result = build.integrate(self.run)
        self.assertEqual(result['status'], 'merge_conflict')
        self.assertTrue((self.run / 'integration/upper.py').exists())
        self.assertEqual(before, build.candidate_state(self.root))

    def test_inspection_git_error_is_not_labeled_merge_conflict(self):
        self.ready(); original_git = build.git
        def inject(root, *args, **kwargs):
            if args == ('write-tree',):
                raise subprocess.CalledProcessError(1, ['git', *args], stderr=b'Inspection unavailable')
            return original_git(root, *args, **kwargs)
        with patch.object(build, 'git', side_effect=inject): result = build.integrate(self.run)
        self.assertEqual(result['status'], 'blocked')

    def test_worker_scope_expansion_blocks_integration_and_preserves_work(self):
        self.prepare(); self.implement(); (self.worker('T-UP') / 'lower.py').write_text('overwrite peer\n')
        result = build.finish(self.run, 'T-UP', 'ready', 'Attempted edit')
        self.assertEqual(result['status'], 'failed'); self.assertIn('scope expansion', result['error'])
        with self.assertRaises((ValueError, FileNotFoundError)): build.integrate(self.run)
        self.assertFalse((self.run / 'integration').exists()); self.assertTrue((self.worker('T-UP') / 'lower.py').exists())

    def test_failed_and_missing_return_do_not_merge(self):
        self.prepare()
        self.assertEqual(build.finish(self.run, 'T-UP', 'failed', 'Tool unavailable')['status'], 'failed')
        with self.assertRaisesRegex(ValueError, 'failed/blocked'): build.integrate(self.run)
        self.assertFalse((self.run / 'integration').exists())
        with self.assertRaises(FileNotFoundError): build.load(self.run / 'returns/T-LOW/result.json')

    def test_integration_failure_does_not_promote_or_hide_candidate(self):
        self.plan['integration_checks'].append([sys.executable, '-c', 'raise SystemExit(4)'])
        self.ready(); result = build.integrate(self.run)
        self.assertEqual(result['status'], 'checks_failed'); self.assertEqual(result['checks'][-1]['returncode'], 4)
        self.assertTrue((self.run / 'integration/upper.py').exists())
        self.assertEqual(self.git(self.root, 'rev-parse', 'HEAD').strip(), self.base)
        with self.assertRaisesRegex(ValueError, 'already exists'): build.integrate(self.run)

    def test_sources_drift_and_worker_changes_expire_results(self):
        self.ready(); (self.folder / 'sources/prd-original.txt').write_text('Updated product authority')
        with self.assertRaisesRegex(ValueError, 'stale'): build.integrate(self.run)
        self.assertFalse((self.run / 'integration').exists())

    def test_worker_changes_after_checks_are_not_accepted(self):
        self.ready(); (self.worker('T-UP') / 'upper.py').write_text('def convert(v): return v.lower()\n')
        with self.assertRaisesRegex(ValueError, 'changed after tests'): build.integrate(self.run)

    def test_shared_record_write_and_scratch_tampering_rejected(self):
        self.prepare(); self.implement()
        bad = self.worker('T-UP') / '.agent-workflow/features/FEAT-001/tasks.json'
        bad.parent.mkdir(parents=True); bad.write_text('{}')
        result = build.finish(self.run, 'T-UP', 'ready', 'Attempted record update')
        self.assertEqual(result['status'], 'failed'); self.assertIn('shared workflow', result['error'])
        manifest = build.load(self.run / 'run.json'); manifest['plan']['tasks'][0]['allowed_paths'] = ['lower.py']
        (self.run / 'run.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'scratch record changed'): build.preflight(self.run)

    def test_frozen_evidence_and_real_logs_are_bound(self):
        self.ready(); p = self.run / 'returns/T-UP/check-0.log'; p.write_text('fake green')
        with self.assertRaisesRegex(ValueError, 'evidence changed'): build.integrate(self.run)
        p = self.run / 'inputs/.agent-workflow/features/FEAT-001/sources/prd-original.txt'; p.write_text('edited frozen source')
        with self.assertRaisesRegex(ValueError, 'frozen authority'): build.preflight(self.run)

    def test_dirty_primary_out_inside_project_and_ineligible_task_rejected(self):
        (self.root / 'upper.py').write_text('user draft')
        with self.assertRaisesRegex(ValueError, 'uncommitted business'): self.prepare()
        self.git(self.root, 'checkout', '--', 'upper.py')
        with self.assertRaisesRegex(ValueError, 'outside the project'): build.prepare(self.root, 'FEAT-001', self.plan, self.root / 'attempt')
        self.tasks['tasks'][0]['status'] = 'done'; self.put('tasks.json', self.tasks)
        with self.assertRaisesRegex(ValueError, 'eligible existing'): self.prepare()

    def test_task_check_failure_records_actual_exit(self):
        self.prepare(); self.implement(); (self.worker('T-UP') / 'upper.py').write_text('def convert(v): return v\n')
        result = build.finish(self.run, 'T-UP', 'ready', 'Candidate implementation')
        self.assertEqual(result['status'], 'failed'); self.assertEqual(result['checks'][0]['returncode'], 1)

    def test_check_mutation_is_not_green(self):
        self.plan['integration_checks'] = [[sys.executable, '-c', "open('unexpected.py','w').write('new')"]]
        self.ready(); result = build.integrate(self.run)
        self.assertEqual(result['status'], 'blocked'); self.assertIn('changed candidate', result['error'])

    def test_worker_symlink_rejected(self):
        self.prepare(); self.implement(); (self.worker('T-UP') / 'upper.py').unlink()
        (self.worker('T-UP') / 'upper.py').symlink_to(self.root / 'lower.py')
        result = build.finish(self.run, 'T-UP', 'ready', 'Link returned')
        self.assertEqual(result['status'], 'failed'); self.assertIn('symlinks', result['error'])

    def test_missing_check_executable_is_failed_not_passed(self):
        self.plan['tasks'][0]['checks'] = [['missing-fixture-executable']]
        self.prepare(); self.implement(); result = build.finish(self.run, 'T-UP', 'ready', 'Code ready')
        self.assertEqual(result['status'], 'failed'); self.assertEqual(result['checks'][0]['status'], 'unavailable')


if __name__ == '__main__':
    unittest.main()
