import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/dev/core/scripts'


class DeliveryAuditTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.base = self.root / '.agent-workflow/project-baseline'
        self.base.mkdir(parents=True)
        self.feature = self.root / '.agent-workflow/features/FEAT-001'
        (self.feature / 'spec').mkdir(parents=True)
        (self.feature / 'spec/requirements.json').write_text(json.dumps({
            'feature': {'id': 'FEAT-001', 'status': 'provisional'},
            'requirements': [{'id': 'R-1', 'tests': ['UT-1']}]}))
        (self.feature / 'fixes.json').write_text(json.dumps({
            'feature_id': 'FEAT-001', 'fixes': [{'id': 'FIX-001', 'status': 'verified',
                                               'regression_test_ids': ['UT-1']}]}))
        self.gates([{'name': 'test', 'command': [sys.executable, '-c', 'print("passed")'],
                     'test_ids': ['UT-1']}])
        subprocess.run(['git', 'init', str(self.root)], check=True, capture_output=True)
        (self.root / 'README.md').write_text('fixture 1')
        subprocess.run(['git', '-C', str(self.root), 'add', 'README.md'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(self.root), '-c', 'user.name=Fixture',
                        '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'fixture'],
                       check=True, capture_output=True)

    def gates(self, gates):
        (self.base / 'quality-gates.json').write_text(json.dumps({'gates': gates}))

    def script(self, name, *args, expected=0):
        proc = subprocess.run([sys.executable, '-B', str(SCRIPTS / name),
                               *map(str, args)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, expected, proc.stdout + proc.stderr)
        return proc.stdout + proc.stderr

    def test_report_tracks_selected_fix_test_and_current_revision(self):
        self.script('project.py', 'check', self.root)
        self.assertIn('DELIVERY_EVIDENCE_CURRENT',
                      self.script('audit-delivery.py', self.root, 'FEAT-001'))
        (self.root / 'README.md').write_text('fixture 2')
        subprocess.run(['git', '-C', str(self.root), 'add', 'README.md'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(self.root), '-c', 'user.name=Fixture',
                        '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'changed'],
                       check=True, capture_output=True)
        self.assertIn('stale', self.script('audit-delivery.py', self.root, 'FEAT-001', expected=1))

    def test_old_selector_cannot_stand_in_for_new_fix_test(self):
        self.gates([{'name': 'old-test', 'command': [sys.executable, '-c', 'print("old passed")'],
                     'test_ids': ['UT-OLD']}])
        self.script('project.py', 'check', self.root)
        self.assertIn('UT-1', self.script('audit-delivery.py', self.root, 'FEAT-001', expected=1))
        self.gates([{'name': 'new-test', 'command': [sys.executable, '-c', 'print("new passed")'],
                     'test_ids': ['UT-1']}])
        self.script('project.py', 'check', self.root)
        self.script('audit-delivery.py', self.root, 'FEAT-001')

    def test_unavailable_result_cannot_claim_selection(self):
        self.gates([{'name': 'failing', 'command': [sys.executable, '-c', 'raise SystemExit(1)'],
                     'test_ids': ['UT-1']}])
        self.script('project.py', 'check', self.root, expected=1)
        self.assertIn('failed or unavailable',
                      self.script('audit-delivery.py', self.root, 'FEAT-001', expected=1))

    def test_invalid_test_id_metadata_prevents_execution(self):
        for ids in ('UT-1', [''], ['UT-1', 'UT-1']):
            with self.subTest(ids=ids):
                self.gates([{'name': 'test', 'command': [sys.executable, '-c', 'print("run")'],
                             'test_ids': ids}])
                self.assertIn('test_ids', self.script('project.py', 'validate-gates',
                                                      self.root, expected=2))

    def test_check_cannot_claim_final_snapshot_after_manifest_changes(self):
        self.gates([{'name': 'changes-manifest',
                     'command': [sys.executable, '-c',
                                 'from pathlib import Path; Path("package.json").write_text("changed")'],
                     'test_ids': ['UT-1']}])
        self.assertIn('PROJECT_CHANGED_DURING_CHECK',
                      self.script('project.py', 'check', self.root, expected=1))
        self.assertIn('stale', self.script('audit-delivery.py', self.root, 'FEAT-001', expected=1))


if __name__ == '__main__':
    unittest.main()
