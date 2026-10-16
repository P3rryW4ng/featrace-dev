import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_delivery_audit

CORE = Path(__file__).resolve().parents[1] / 'skills/dev/core/scripts'
sys.path.insert(0, str(CORE))
import check_identity as ci
import project
from project import quality_snapshot, quality_comparison, snapshot


class CheckIdentityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_delivery_audit.DeliveryAuditTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root, self.base = self.fixture.root, self.fixture.base

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.PIPE)

    def capture(self):
        return quality_snapshot(self.root)

    def changed(self, before):
        result = quality_comparison(self.root, before, self.capture())
        self.assertEqual(result['state'], 'changed', result)
        return result

    def test_worktree_and_index_are_separate_even_when_worktree_reverted(self):
        before = self.capture()
        p = self.root / 'README.md'
        p.write_text('staged implementation')
        self.git('add', 'README.md')
        p.write_text('fixture 1')
        result = self.changed(before)
        self.assertIn('README.md', result['changes']['index'])
        self.assertNotIn('files', result['changes'])

    def test_unstaged_untracked_deletion_rename_and_mode_are_detected(self):
        for kind in ('unstaged', 'untracked', 'deleted', 'rename', 'mode'):
            with self.subTest(kind=kind):
                before = self.capture()
                p = self.root / 'README.md'
                if kind == 'unstaged': p.write_text('edited')
                elif kind == 'untracked': (self.root / 'new test.py').write_bytes(b'\x00binary')
                elif kind == 'deleted': p.unlink()
                elif kind == 'rename': p.rename(self.root / 'renamed.md')
                else: p.chmod(0o755)
                self.changed(before)
                self.git('reset', '--hard', 'HEAD')
                self.git('clean', '-fd', '--', 'new test.py', 'renamed.md')

    def test_assume_unchanged_cannot_hide_actual_source_bytes(self):
        before = self.capture()
        self.git('update-index', '--assume-unchanged', 'README.md')
        (self.root / 'README.md').write_text('hidden from ordinary git diff')
        self.assertEqual(self.git('diff', '--name-only'), b'')
        self.changed(before)

    def test_workflow_records_do_not_change_identity_but_declared_workflow_input_does(self):
        before = self.capture()
        (self.fixture.feature / 'notes.md').write_text('only records')
        self.assertEqual(quality_comparison(self.root, before, self.capture())['state'], 'same')
        script = self.root / '.agent-workflow/check.py'
        script.write_text('assert True')
        (self.base / 'evidence-files.json').write_text(json.dumps({'files': ['.agent-workflow/check.py']}))
        before = self.capture()
        script.write_text('assert False')
        self.changed(before)

    def test_ignored_input_only_bound_when_declared_and_missing_is_unknown(self):
        (self.root / '.gitignore').write_text('/ignored.cfg\n')
        hidden = self.root / 'ignored.cfg'
        hidden.write_text('one')
        before = self.capture(); hidden.write_text('two')
        self.assertEqual(quality_comparison(self.root, before, self.capture())['state'], 'same')
        (self.base / 'evidence-files.json').write_text('{"files":["ignored.cfg"]}')
        before = self.capture(); hidden.write_text('three'); self.changed(before)
        hidden.unlink()
        self.assertEqual(self.capture()['check_inputs']['state'], 'unknown')

    def test_missing_git_and_read_failures_are_unknown_not_same(self):
        with patch.object(ci, 'git', side_effect=ValueError('Git unavailable')):
            value = ci.capture(self.root)
        self.assertEqual(ci.compare(value, value)['state'], 'unknown')
        with patch.object(ci, 'path_state', side_effect=PermissionError('unreadable')):
            self.assertEqual(ci.capture(self.root)['state'], 'unknown')

    def test_capture_movement_and_unsupported_version_are_unknown(self):
        one = ci.collect(self.root, (), ())
        with patch.object(ci, 'collect', side_effect=[one, dict(one, head='different')]):
            moved = ci.capture(self.root)
        self.assertEqual(moved['state'], 'unknown')
        self.assertEqual(ci.compare(one, dict(one, schema_version=999))['state'], 'unknown')
        self.assertEqual(ci.compare(dict(one, files={'README.md': 'malformed'}), one)['state'], 'unknown')

    def test_symlink_parent_outside_input_and_submodule_are_not_followed(self):
        link = self.root / 'outside'
        link.symlink_to(self.base, target_is_directory=True)
        for name in ('outside/quality-gates.json', '../escape'):
            with self.subTest(name=name):
                self.assertEqual(ci.capture(self.root, [name])['state'], 'unknown')
        link.unlink()
        self.git('update-index', '--add', '--cacheinfo', '160000', self.git('rev-parse', 'HEAD').decode().strip(), 'submodule')
        self.assertEqual(ci.capture(self.root)['state'], 'unknown')

    def test_legacy_report_is_unknown_without_changing_scan_fingerprint(self):
        legacy = snapshot(self.root)
        self.assertNotIn('check_inputs', legacy)
        self.assertEqual(legacy['version'], 2)
        self.assertEqual(quality_comparison(self.root, legacy, self.capture())['state'], 'unknown')

    def test_executor_and_audit_agree_on_dirty_source_and_preserve_actual_pass(self):
        (self.root / 'README.md').write_text('preexisting dirty source')
        self.fixture.script('project.py', 'check', self.root)
        self.fixture.script('audit-delivery.py', self.root, 'FEAT-001')
        (self.root / 'README.md').write_text('changed after execution')
        self.assertIn('changed', self.fixture.script('audit-delivery.py', self.root, 'FEAT-001', expected=1))

    def test_runner_detects_index_only_drift_and_cannot_certify_restored_input(self):
        self.fixture.gates([{'name': 'stage', 'command': [sys.executable, '-c',
            "import subprocess; subprocess.run(['git','add','README.md'],check=True)"], 'test_ids': ['UT-1']}])
        (self.root / 'README.md').write_text('already edited')
        self.fixture.script('project.py', 'check', self.root, expected=1)
        # Restore exactly the pre-run index; the command's exit zero still
        # cannot turn the uncertified run into a current pass.
        self.git('reset', 'HEAD', '--', 'README.md')
        output = self.fixture.script('audit-delivery.py', self.root, 'FEAT-001', expected=1)
        self.assertIn('did not certify stable inputs', output)

    def test_runner_detects_command_drift_but_prose_only_remains_current(self):
        self.fixture.script('project.py', 'check', self.root)
        p = self.base / 'quality-gates.json'; config = json.loads(p.read_text())
        config['selection_reason'] = 'reviewed wording only'; p.write_text(json.dumps(config))
        self.fixture.script('audit-delivery.py', self.root, 'FEAT-001')
        self.fixture.gates([{'name': 'unit', 'command': [sys.executable, '-c',
            "import json; from pathlib import Path; p=Path('.agent-workflow/project-baseline/quality-gates.json'); d=json.loads(p.read_text()); d['gates'][0]['command']=['other']; p.write_text(json.dumps(d))"], 'test_ids': ['UT-1']}])
        self.fixture.script('project.py', 'check', self.root, expected=1)

    def test_unknown_preflight_does_not_execute_commands(self):
        (self.base / 'evidence-files.json').write_text('{"files":["missing.cfg"]}')
        self.fixture.gates([{'name': 'sentinel', 'command': [sys.executable, '-c',
            "from pathlib import Path; Path('executed').touch()"], 'test_ids': ['UT-1']}])
        self.fixture.script('project.py', 'check', self.root, expected=2)
        self.assertFalse((self.root / 'executed').exists())
        self.assertFalse((self.base / 'quality-report.json').exists())

    def test_dangling_registry_symlink_is_not_an_empty_registry(self):
        (self.base / 'evidence-files.json').symlink_to(self.base / 'not-present.json')
        output = self.fixture.script('project.py', 'check', self.root, expected=2)
        self.assertIn('symlink', output)
        self.assertFalse((self.base / 'quality-report.json').exists())

    def test_selection_moving_between_parse_and_capture_never_executes(self):
        self.fixture.gates([{'name': 'sentinel', 'command': [sys.executable, '-c',
            "from pathlib import Path; Path('executed').touch()"], 'test_ids': ['UT-1']}])
        original = project.validate_gates
        calls = []
        def change_after_parse(root, config):
            prepared = original(root, config)
            if not calls:
                calls.append(True)
                changed = json.loads((self.base / 'quality-gates.json').read_text())
                changed['gates'][0]['command'] = [sys.executable, '-c', 'print("different")']
                (self.base / 'quality-gates.json').write_text(json.dumps(changed))
            return prepared
        with patch.object(project, 'validate_gates', side_effect=change_after_parse), patch.object(
                sys, 'argv', ['project.py', 'check', str(self.root)]):
            with self.assertRaisesRegex(ValueError, 'selection moved'):
                project.main()
        self.assertFalse((self.root / 'executed').exists())

    def test_non_git_execution_is_refused_but_scan_is_still_inventory_only(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(ci.capture(Path(tmp))['state'], 'unknown')

    def test_new_untracked_source_during_run_is_not_certified(self):
        self.fixture.gates([{'name': 'generate', 'command': [sys.executable, '-c',
            "from pathlib import Path; Path('new-source.py').write_text('new code')"], 'test_ids': ['UT-1']}])
        self.fixture.script('project.py', 'check', self.root, expected=1)
        report = json.loads((self.base / 'quality-report.json').read_text())
        self.assertEqual(report['results'][0]['status'], 'passed')
        self.assertEqual(report['input_comparison']['state'], 'changed')
        self.fixture.script('audit-delivery.py', self.root, 'FEAT-001', expected=1)

    def test_verification_row_does_not_upgrade_runner_identity_failure(self):
        import test_verification
        helper = test_verification.VerificationTests()
        helper.setUp(); self.addCleanup(helper.doCleanups)
        (helper.root / 'convert.py').write_text('def convert(value): return value.upper()\n# dirty\n')
        helper.gates([sys.executable, '-c',
                      "import subprocess; subprocess.run(['git','add','convert.py'],check=True)"])
        helper.run_checks()
        automatic = [row for row in helper.plan()['items'] if row['mode'] == 'automatic']
        self.assertTrue(automatic)
        self.assertTrue(all(row['history'][-1]['status'] == 'unavailable' for row in automatic))

    def test_workflow_commit_still_current_and_source_commit_stale(self):
        self.fixture.test_workflow_only_commit_does_not_stale_quality_report()
        (self.root / 'README.md').write_text('new source')
        self.git('add', 'README.md')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'source')
        self.fixture.script('audit-delivery.py', self.root, 'FEAT-001', expected=1)


if __name__ == '__main__': unittest.main()
