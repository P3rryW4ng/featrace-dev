import copy
import json
import unittest
import test_delivery_audit
import sys
sys.path.insert(0, str(test_delivery_audit.SCRIPTS))
from regression_execution import capture, apply, current_evidence
from regression_review import discover


class RegressionExecutionTests(unittest.TestCase):
    def setUp(self):
        self.helper = test_delivery_audit.DeliveryAuditTests()
        self.helper.setUp(); self.addCleanup(self.helper.doCleanups)
        self.root, self.folder = self.helper.root, self.helper.feature
        (self.root / 'device_test.py').write_text('# synthetic device test source\n')
        import subprocess
        subprocess.run(['git', '-C', str(self.root), 'add', 'device_test.py'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(self.root), '-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'test source'], check=True, capture_output=True)
        head = subprocess.check_output(['git', '-C', str(self.root), 'rev-parse', 'HEAD'], text=True).strip()
        self.fixes = json.loads((self.folder / 'fixes.json').read_text())
        self.fixes['fixes'][0].update(requirement_ids=['R-1'], tested_revision=head, description='Fixture fix', code_paths=['README.md'])
        (self.folder / 'fixes.json').write_text(json.dumps(self.fixes))
        (self.folder / 'tasks.json').write_text(json.dumps({'tasks': []}))
        req = json.loads((self.folder / 'spec/requirements.json').read_text()); req['feature']['modules'] = ['app']
        (self.folder / 'spec/requirements.json').write_text(json.dumps(req))
        (self.folder / 'decisions.json').write_text(json.dumps({'decisions': []}))
        (self.folder / 'evidence').mkdir()
        (self.folder / 'evidence/run.txt').write_text('Synthetic device command executed exact fixture case; result success\n')
        (self.folder / 'evidence/package.txt').write_text('Synthetic fixture package/source binding at ' + head)
        self.execution = {'kind': 'device', 'status': 'passed', 'returncode': 0,
                          'tested_revision': head, 'executed_at': '2026-10-13T10:00:00Z',
                          'command': ['adb', '-s', 'fixture-device', 'shell', 'am', 'instrument', 'fixture/test'],
                          'executed_cases': ['null_nickname'], 'failed_cases': [], 'skipped_cases': [],
                          'test_files': ['device_test.py'], 'evidence_refs': ['evidence/run.txt'],
                          'package_identity_refs': ['evidence/package.txt'], 'environment': 'synthetic fixture device',
                          'coverage': 'Exact null nickname regression asserted'}
        # Required ordinary gates still execute, but do not pretend to run the device test.
        self.helper.gates([{'name': 'compile', 'command': ['python3', '-c', 'print("compile fixture")'], 'test_ids': []}])
        self.helper.script('project.py', 'check', self.root)

    def record(self):
        frozen = capture(self.root, self.folder, 'FIX-001', 'UT-1', self.execution)
        review = {'input_digest': frozen['input_digest'], 'status': 'supported', 'reviewer': 'fixture reviewer',
                  'assertion_evidence': 'Archived output records actual executed null regression; compiler result is separate',
                  'original_identity_evidence': 'Archived package/source fixture binding inspected',
                  'routine_check_reason': 'Requires a selected device, not an automatic routine gate'}
        snapshot, output = self.folder / 'snapshot.json', self.folder / 'review.json'
        snapshot.write_text(json.dumps(frozen)); output.write_text(json.dumps(review))
        apply(self.root, self.folder, snapshot, output)
        return frozen, snapshot, output

    def test_executed_device_regression_passes_audit_and_keeps_candidate_test_link(self):
        self.helper.script('audit-delivery.py', self.root, 'FEAT-001', expected=1)
        self.record()
        self.helper.script('audit-delivery.py', self.root, 'FEAT-001')
        fix = json.loads((self.folder / 'fixes.json').read_text())['fixes'][0]
        self.assertEqual(fix['regression_test_ids'], ['UT-1'])
        self.assertTrue(current_evidence(self.root, self.folder, fix, 'UT-1'))
        self.assertEqual(discover(self.root, 'FEAT-001')[1][0]['historical_regression_test_ids'], ['UT-1'])

    def test_compilation_skip_failure_and_missing_identity_not_execution(self):
        for patch in ({'executed_cases': []}, {'skipped_cases': ['null_nickname']}, {'returncode': 1}, {'package_identity_refs': []}):
            with self.assertRaises(ValueError):
                capture(self.root, self.folder, 'FIX-001', 'UT-1', dict(self.execution, **patch))

    def test_artifact_or_code_change_invalidates_receipt(self):
        self.record(); (self.folder / 'evidence/run.txt').write_text('changed result')
        self.helper.script('audit-delivery.py', self.root, 'FEAT-001', expected=1)

    def test_pending_capture_changes_and_wrong_review_reject(self):
        frozen = capture(self.root, self.folder, 'FIX-001', 'UT-1', self.execution)
        snapshot, output = self.folder / 'snapshot.json', self.folder / 'review.json'
        snapshot.write_text(json.dumps(frozen)); output.write_text(json.dumps({'status': 'supported', 'input_digest': 'wrong'}))
        with self.assertRaises(ValueError): apply(self.root, self.folder, snapshot, output)
        (self.root / 'README.md').write_text('changed business tree')
        with self.assertRaises(ValueError): apply(self.root, self.folder, snapshot, output)

    def test_tampered_receipt_and_deleted_test_link_reject(self):
        self.record(); doc = json.loads((self.folder / 'fixes.json').read_text())
        entry = doc['fixes'][0]['regression_execution_history'][-1]
        entry['inputs']['execution']['executed_cases'] = []
        (self.folder / 'fixes.json').write_text(json.dumps(doc))
        self.helper.script('audit-delivery.py', self.root, 'FEAT-001', expected=1)
        with self.assertRaises(ValueError): capture(self.root, self.folder, 'FIX-001', 'OTHER', self.execution)

    def test_input_changed_during_apply_never_saves_successful_receipt(self):
        from unittest.mock import patch
        import regression_execution as execution_module
        frozen = capture(self.root, self.folder, 'FIX-001', 'UT-1', self.execution)
        review = {'input_digest': frozen['input_digest'], 'status': 'supported', 'reviewer': 'fixture reviewer',
                  'assertion_evidence': 'actual cases', 'original_identity_evidence': 'fixture identity',
                  'routine_check_reason': 'selected device required'}
        snapshot, output = self.folder / 'snapshot.json', self.folder / 'review.json'
        snapshot.write_text(json.dumps(frozen)); output.write_text(json.dumps(review))
        original_capture = execution_module.capture
        calls = []
        def moving_capture(*args):
            result = original_capture(*args)
            if not calls:
                (self.folder / 'evidence/run.txt').write_text('artifact changed during registration')
            calls.append(True)
            return result
        with patch.object(execution_module, 'capture', moving_capture):
            with self.assertRaisesRegex(ValueError, 'changed before save'):
                apply(self.root, self.folder, snapshot, output)
        self.assertNotIn('regression_execution_history', json.loads((self.folder / 'fixes.json').read_text())['fixes'][0])
