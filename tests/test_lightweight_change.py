import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'skills/dev/core/scripts/init-change.py'
VALIDATE = SCRIPT.with_name('validate-feature.py')


class LightweightChangeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.request = self.root / 'request.md'
        self.folder = self.root / '.agent-workflow/features/WORK-123'

    def create(self, kind='change', feature='WORK-123'):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.root), feature,
                               '--kind', kind, '--request-file', str(self.request)],
                              capture_output=True, text=True)

    def test_short_change_uses_existing_draft_records_without_claiming_approval(self):
        original = '钱包页现有入口改名，点击行为保持不变。\n'
        self.request.write_text(original, encoding='utf-8')
        result = self.create()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.folder / 'sources/prd-original.md').read_text(encoding='utf-8'), original)
        requirements = json.loads((self.folder / 'spec/requirements.json').read_text())
        self.assertEqual(requirements['feature']['entry_kind'], 'change')
        self.assertEqual(requirements['feature']['status'], 'drafted')
        self.assertEqual(requirements['requirements'], [])
        self.assertEqual(json.loads((self.folder / 'tasks.json').read_text())['tasks'], [])

    def test_standalone_defect_is_reported_but_expected_behavior_is_not_invented(self):
        original = '付款按钮连点后扣了两次款。\n'
        self.request.write_text(original, encoding='utf-8')
        result = self.create('defect')
        self.assertEqual(result.returncode, 0, result.stderr)
        fixes = json.loads((self.folder / 'fixes.json').read_text())['fixes']
        self.assertEqual(len(fixes), 1)
        self.assertEqual(fixes[0]['status'], 'reported')
        self.assertEqual(fixes[0]['kind'], 'unclassified')
        self.assertEqual(fixes[0]['description'], original.strip())
        self.assertEqual(fixes[0]['expected'], '')
        self.assertEqual(json.loads((self.folder / 'spec/requirements.json').read_text())['feature']['entry_kind'], 'defect')
        check = subprocess.run([sys.executable, str(VALIDATE), str(self.root), 'WORK-123',
                                '--stage', 'develop'], capture_output=True, text=True)
        self.assertNotEqual(check.returncode, 0)
        self.assertIn('at least one active requirement is required', check.stdout)

    def test_existing_id_does_not_overwrite_or_reselect(self):
        self.request.write_text('First request')
        self.assertEqual(self.create().returncode, 0)
        preserved = (self.folder / 'sources/prd-original.md').read_bytes()
        self.request.write_text('Different request')
        result = self.create('defect')
        self.assertEqual(result.returncode, 2)
        self.assertIn('already exists', result.stderr)
        self.assertEqual((self.folder / 'sources/prd-original.md').read_bytes(), preserved)
        self.assertEqual(json.loads((self.folder / 'fixes.json').read_text())['fixes'], [])

    def test_empty_or_invalid_request_writes_no_feature(self):
        self.request.write_text(' \n')
        self.assertEqual(self.create().returncode, 2)
        self.assertFalse(self.folder.exists())
        self.request.write_text('A real request')
        self.assertEqual(self.create(feature='../wrong').returncode, 2)
        self.assertFalse(self.folder.exists())

    def test_symlinked_request_is_rejected(self):
        actual = self.root / 'actual.md'
        actual.write_text('Do not follow source symlinks')
        self.request.symlink_to(actual)
        result = self.create()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.folder.exists())


if __name__ == '__main__':
    unittest.main()
