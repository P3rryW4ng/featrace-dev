import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/dev/core/scripts/project.py'
spec = importlib.util.spec_from_file_location('scan_project', SCRIPT)
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class ScanContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base = self.root / '.agent-workflow/project-baseline'; self.base.mkdir(parents=True)

    def run_action(self, action, expected):
        run = subprocess.run([sys.executable, str(SCRIPT), action, str(self.root)], capture_output=True, text=True)
        self.assertEqual(run.returncode, expected, run.stdout + run.stderr)
        return run

    def config(self, gates):
        (self.base / 'quality-gates.json').write_text(json.dumps({'gates': gates}))

    def gate(self):
        return {'name': 'sentinel', 'command': [sys.executable, '-c', "from pathlib import Path; Path('executed').write_text('yes')"]}

    def test_validate_does_not_execute(self):
        self.config([self.gate()]); self.run_action('validate-gates', 0)
        self.assertFalse((self.root / 'executed').exists())

    def test_invalid_later_gate_prevents_all_execution(self):
        self.config([self.gate(), {'name': 'bad', 'command': 'gradlew check'}])
        self.run_action('check', 2); self.assertFalse((self.root / 'executed').exists())

    def test_conditions_and_placeholders_rejected(self):
        for key, value in [('when', 'after source change'), ('enabled', False), ('command', ['gradlew', '--tests', '<pattern>'])]:
            with self.subTest(key=key):
                g=self.gate(); g[key]=value; self.config([g]); self.run_action('validate-gates', 2)

    def test_empty_selection_never_passes_check(self):
        self.config([]); self.run_action('validate-gates', 0); self.run_action('check', 2)

    def test_candidates_not_executed(self):
        (self.base / 'quality-candidates.json').write_text(json.dumps({'candidates': [self.gate()]}))
        self.config([]); self.run_action('check', 2); self.assertFalse((self.root / 'executed').exists())

    def test_selected_only_runs(self):
        self.config([self.gate()]); self.run_action('check', 0)
        self.assertTrue((self.root / 'executed').exists())

    def test_bad_cwd_duplicate_name_and_timeout(self):
        for gates in ([dict(self.gate(), cwd='..')], [self.gate(), self.gate()], [dict(self.gate(), timeout_seconds=float('nan'))], [None]):
            self.config(gates); self.run_action('validate-gates', 2)

    def test_registered_evidence_and_rules_invalidate(self):
        (self.root / 'rules.md').write_text('original')
        (self.base / 'evidence-files.json').write_text('{"files":["rules.md"]}')
        self.run_action('scan', 0); self.run_action('verify', 0)
        (self.root / 'rules.md').write_text('changed without commit')
        self.run_action('verify', 3)
        self.run_action('scan', 0); (self.root / 'rules.md').unlink(); self.run_action('verify', 3)
        self.run_action('scan', 0); (self.root / 'CLAUDE.md').write_text('new rules'); self.run_action('verify', 3)

    def test_evidence_outside_root_rejected(self):
        (self.base / 'evidence-files.json').write_text('{"files":["../outside"]}')
        self.run_action('scan', 2)

    def test_rescan_preserves_reviewed_coverage(self):
        self.run_action('scan', 0)
        (self.base / 'coverage.md').write_text('app: reviewed UI only')
        self.run_action('scan', 0)
        self.assertEqual((self.base / 'coverage.md').read_text(), 'app: reviewed UI only')


class ScanDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'src').mkdir()
        (self.root / 'README.md').write_text('baseline\n')
        (self.root / 'package.json').write_text('{"name":"fixture"}\n')
        (self.root / 'src/registered.py').write_text('VALUE = 1\n')
        (self.root / 'src/unregistered.py').write_text('OTHER = 1\n')
        self.git('init', '-b', 'main')
        self.git('add', 'README.md', 'package.json', 'src')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-m', 'fixture baseline')
        self.run_action('scan', 0)
        self.base = self.root / '.agent-workflow/project-baseline'
        (self.base / 'evidence-files.json').write_text('{"files":["src/registered.py"]}\n')
        self.run_action('scan', 0)

    def git(self, *args):
        run = subprocess.run(['git', '-C', str(self.root), *args], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        return run.stdout

    def run_action(self, action, expected):
        run = subprocess.run([sys.executable, str(SCRIPT), action, str(self.root)], capture_output=True, text=True)
        self.assertEqual(run.returncode, expected, run.stdout + run.stderr)
        return run.stdout

    def backup_count(self):
        history = self.root / '.agent-workflow/baseline-backups/managed-v1'
        return len([path for path in history.iterdir() if path.is_dir()]) if history.exists() else 0

    def test_unregistered_tracked_worktree_change_requires_review(self):
        (self.root / 'src/unregistered.py').write_text('OTHER = 2\n')
        output = self.run_action('verify', 3)
        self.assertIn('BASELINE_WORKTREE_REVIEW_REQUIRED', output)
        self.assertIn('WORKTREE_CHANGED_PATHS: src/unregistered.py', output)

    def test_untracked_worktree_change_requires_review(self):
        (self.root / 'src/new.py').write_text('NEW = 1\n')
        output = self.run_action('verify', 3)
        self.assertIn('WORKTREE_CHANGED_PATHS: src/new.py', output)

    def test_workflow_worktree_changes_are_ignored(self):
        (self.root / '.agent-workflow/local-note').write_text('local only\n')
        self.assertIn('BASELINE_VALID', self.run_action('verify', 0))

    def test_head_change_reports_changed_paths(self):
        (self.root / 'README.md').write_text('committed docs change\n')
        self.git('add', 'README.md')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-m', 'docs change')
        output = self.run_action('verify', 3)
        self.assertIn('BASELINE_STALE_REASONS: git_head', output)
        self.assertIn('HEAD_CHANGED_PATHS: README.md', output)

    def test_registered_evidence_and_manifest_reasons_are_distinct(self):
        (self.root / 'src/registered.py').write_text('VALUE = 2\n')
        output = self.run_action('verify', 3)
        self.assertIn('BASELINE_STALE_REASONS: evidence', output)
        self.assertIn('EVIDENCE_CHANGED_PATHS: src/registered.py', output)
        (self.root / 'src/registered.py').write_text('VALUE = 1\n')
        (self.root / 'package.json').write_text('{"name":"changed"}\n')
        output = self.run_action('verify', 3)
        self.assertIn('BASELINE_STALE_REASONS: manifests', output)
        self.assertIn('MANIFEST_CHANGED_PATHS: package.json', output)

    def test_workflow_only_commit_does_not_stale_baseline(self):
        note = self.root / '.agent-workflow/shared-note.md'
        note.write_text('shared record\n')
        self.git('add', '.agent-workflow/shared-note.md')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-m', 'workflow record')
        output = self.run_action('verify', 0)
        self.assertIn('BASELINE_HEAD_ADVANCED_WORKFLOW_ONLY', output)

    def test_unknown_fingerprint_shape_is_rejected(self):
        fingerprint = self.base / 'fingerprint.json'
        record = json.loads(fingerprint.read_text())
        record['unexpected'] = True
        fingerprint.write_text(json.dumps(record))
        output = self.run_action('verify', 3)
        self.assertIn('BASELINE_STALE_REASONS: fingerprint_shape', output)

    def test_fingerprint_only_refresh_skips_backup(self):
        before = self.backup_count()
        (self.root / 'README.md').write_text('reviewed docs change\n')
        self.git('add', 'README.md')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-m', 'docs change')
        output = self.run_action('scan', 0)
        self.assertIn('BASELINE_FINGERPRINT_REFRESHED', output)
        self.assertEqual(self.backup_count(), before)
        self.assertIn('BASELINE_VALID', self.run_action('verify', 0))

if __name__ == '__main__': unittest.main()
