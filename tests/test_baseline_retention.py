import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from test_scan_contract import module, SCRIPT

class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.work = self.root / '.agent-workflow'
        self.base = self.work / 'project-baseline'
        self.history = self.work / 'baseline-backups/managed-v1'

    def run_action(self, action, expected=0, *extra):
        run = subprocess.run([sys.executable, str(SCRIPT), action, str(self.root), *extra], capture_output=True, text=True)
        self.assertEqual(run.returncode, expected, run.stdout + run.stderr)
        return run.stdout

    def change(self, n):
        (self.root / 'package.json').write_text(json.dumps({'version': n}))
        self.run_action('scan')

    def test_noop_preserves_mtime_and_no_backups(self):
        self.run_action('scan'); before = (self.base / 'fingerprint.json').stat().st_mtime_ns
        self.assertIn('UNCHANGED', self.run_action('scan'))
        self.assertEqual(before, (self.base / 'fingerprint.json').stat().st_mtime_ns)
        self.assertEqual(list(self.history.iterdir()), [])

    def test_retains_three_complete_backups_preserves_legacy_and_features(self):
        self.run_action('scan')
        legacy = self.work / 'baseline-backups/old-manual'; legacy.mkdir()
        feature = self.work / 'features/a'; feature.mkdir(parents=True); (feature / 'prd.md').write_text('original')
        for n in range(6): self.change(n)
        backups = sorted(self.history.iterdir())
        self.assertEqual(len(backups), 3)
        self.assertEqual([json.loads((p / 'baseline/fingerprint.json').read_text())['files']['package.json'] for p in backups],
                         [module.hashlib.sha256(json.dumps({'version': n}).encode()).hexdigest() for n in range(2,5)])
        self.assertTrue(legacy.exists()); self.assertEqual((feature / 'prd.md').read_text(), 'original')

    def test_pin_and_custom_retention(self):
        self.run_action('scan'); self.change(1)
        pinned = next(self.history.iterdir()); (pinned / 'PINNED').touch()
        for n in range(2,6):
            (self.root / 'package.json').write_text(str(n)); self.run_action('scan', 0, '--keep', '2')
        self.assertTrue(pinned.exists()); self.assertEqual(len(list(self.history.iterdir())), 3)

    def test_draft_publish_includes_analysis_changes(self):
        self.run_action('scan'); old = module.tree_bytes(self.base)
        self.run_action('scan-prepare')
        candidate = self.work / 'baseline-draft/baseline'
        (candidate / 'architecture.md').write_text('Reviewed module A only')
        self.assertEqual(module.tree_bytes(self.base), old)
        self.run_action('scan-publish')
        self.assertEqual((self.base / 'architecture.md').read_text(), 'Reviewed module A only')
        self.assertEqual(module.tree_bytes(next(self.history.iterdir()) / 'baseline'), old)

    def test_bad_draft_keeps_current_and_can_retry(self):
        self.run_action('scan'); old = module.tree_bytes(self.base); self.run_action('scan-prepare')
        candidate = self.work / 'baseline-draft/baseline'
        (candidate / 'quality-gates.json').write_text('{"gates":[{"command":"bad"}]}')
        self.run_action('scan-publish', 2)
        self.assertEqual(module.tree_bytes(self.base), old); self.assertTrue(candidate.exists())
        self.assertEqual(list(self.history.iterdir()), [])
        (candidate / 'quality-gates.json').write_text('{"gates":[]}'); self.run_action('scan-publish')

    def test_concurrent_changes_refused_and_discard_is_scoped(self):
        self.run_action('scan'); self.run_action('scan-prepare'); self.run_action('scan', 2)
        (self.root / 'package.json').write_text('{}'); self.run_action('scan-publish', 2)
        self.run_action('scan-discard'); self.assertTrue(self.base.exists()); self.run_action('scan')

    def test_failed_rename_rolls_back(self):
        self.run_action('scan'); old = module.tree_bytes(self.base)
        candidate = self.work / 'candidate'; module.shutil.copytree(self.base, candidate)
        (candidate / 'coverage.md').write_text('new coverage')
        original = Path.rename
        def rename(path, target):
            if path == candidate: raise OSError('simulated failure')
            return original(path, target)
        with patch.object(Path, 'rename', rename), self.assertRaises(OSError):
            module.promote(self.root, candidate, 3)
        self.assertEqual(module.tree_bytes(self.base), old)
        self.assertEqual(list(self.history.iterdir()), [])

    def test_interrupted_swap_recovers_and_symlink_rejected(self):
        self.run_action('scan'); old = module.tree_bytes(self.base)
        self.base.rename(self.work / '.baseline-previous'); self.run_action('scan')
        self.assertEqual(module.tree_bytes(self.base), old)
        (self.base / 'outside').symlink_to(self.root / 'package.json'); self.run_action('scan', 2)

if __name__ == '__main__': unittest.main()
