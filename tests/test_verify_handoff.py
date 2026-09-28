import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/dev/core/scripts/verify-handoff.py'
spec = importlib.util.spec_from_file_location('verify_handoff', SCRIPT)
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)


class VerifyHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = (Path(self.tmp.name) / 'project').resolve()
        self.root.mkdir()
        self.feature = self.root / '.agent-workflow/features/DEMO'
        (self.feature / 'spec').mkdir(parents=True)
        (self.feature / 'sources').mkdir()
        (self.feature / 'spec/requirements.json').write_text(json.dumps({'feature': {'id': 'DEMO'}}))
        (self.feature / 'sources/prd.txt').write_text('Keep uppercase output')
        (self.root / '.gitignore').write_text('.agent-workflow/\nignored.txt\n')
        (self.root / 'code.py').write_text('def convert(s): return s.upper()\n')
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('add', '.')
        self.git('commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD').strip()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True)

    def capture(self, extra=()):
        return handoff.capture(self.root, 'DEMO', self.base, extra)

    def result(self, snapshot):
        return {'input_digest': snapshot['input_digest'], 'status': 'reviewed', 'summary': 'Read-only review',
                'read_paths': ['code.py'], 'findings': [], 'gaps': [],
                'checks_not_run': ['No tests executed by reviewer']}

    def test_roundtrip_is_read_only_and_does_not_approve_delivery(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        snapshot = self.capture()
        result = self.result(snapshot)
        output = handoff.check(self.root, 'DEMO', snapshot, result)
        self.assertEqual(output['status'], 'VERIFY_REVIEW_RETURN_CURRENT')
        self.assertNotIn('passed', output.values())
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_dirty_start_supported_but_later_tracked_untracked_and_ignored_changes_stale(self):
        (self.root / 'code.py').write_text('def convert(s): return s.lower()\n')
        for path in ('code.py', 'new.py', '.agent-workflow/features/DEMO/sources/prd.txt'):
            with self.subTest(path=path):
                snapshot = self.capture()
                p = self.root / path
                p.write_text((p.read_text() if p.exists() else '') + '\nchanged\n')
                with self.assertRaisesRegex(ValueError, 'stale'):
                    handoff.check(self.root, 'DEMO', snapshot, self.result(snapshot))

    def test_new_commit_and_index_only_changes_stale(self):
        snapshot = self.capture()
        self.git('commit', '--allow-empty', '-qm', 'new revision')
        with self.assertRaisesRegex(ValueError, 'stale'):
            handoff.check(self.root, 'DEMO', snapshot, None)
        (self.root / 'code.py').write_text('changed')
        snapshot = self.capture()
        self.git('add', 'code.py')
        with self.assertRaisesRegex(ValueError, 'stale'):
            handoff.check(self.root, 'DEMO', snapshot, None)

    def test_quality_and_requirement_changes_stale(self):
        base = self.root / '.agent-workflow/project-baseline'
        base.mkdir()
        report = base / 'quality-report.json'
        report.write_text('{"results": []}')
        snapshot = self.capture()
        report.write_text('{"results": ["different"]}')
        with self.assertRaisesRegex(ValueError, 'stale'):
            handoff.check(self.root, 'DEMO', snapshot, None)
        snapshot = self.capture()
        (self.feature / 'spec/requirements.json').write_text('{"feature":{"id":"DEMO"},"revision":2}')
        with self.assertRaisesRegex(ValueError, 'stale'):
            handoff.check(self.root, 'DEMO', snapshot, None)

    def test_missing_extra_becomes_available_and_stales(self):
        snapshot = self.capture(['ignored.txt'])
        self.assertEqual(snapshot['inputs']['files']['ignored.txt']['state'], 'missing')
        (self.root / 'ignored.txt').write_text('new evidence')
        with self.assertRaisesRegex(ValueError, 'stale'):
            handoff.check(self.root, 'DEMO', snapshot, None)

    def test_unbound_ignored_read_is_rejected_then_explicit_binding_works(self):
        (self.root / 'ignored.txt').write_text('private evidence')
        snapshot = self.capture()
        result = self.result(snapshot)
        result['read_paths'].append('ignored.txt')
        with self.assertRaisesRegex(ValueError, 'unbound'):
            handoff.check(self.root, 'DEMO', snapshot, result)
        snapshot = self.capture(['ignored.txt'])
        result['input_digest'] = snapshot['input_digest']
        handoff.check(self.root, 'DEMO', snapshot, result)

    def test_invalid_result_and_wrong_identity_are_rejected(self):
        snapshot = self.capture()
        for updates in ({'status': 'passed'}, {'input_digest': 'other'}, {'findings': [{'claim': 'Bug'}]},
                        {'read_paths': ['../escape']}, {'status': 'failed'}):
            result = self.result(snapshot)
            result.update(updates)
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                handoff.check(self.root, 'DEMO', snapshot, result)
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            handoff.check(self.root, 'OTHER', snapshot, None)
        snapshot['inputs']['git_head'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            handoff.check(self.root, 'DEMO', snapshot, None)

    def test_blocked_return_is_current_not_success(self):
        snapshot = self.capture()
        result = self.result(snapshot)
        result.update(status='blocked', gaps=['Original source unavailable'])
        output = handoff.check(self.root, 'DEMO', snapshot, result)
        self.assertEqual(output['review_status'], 'blocked')

    def test_claim_requires_read_file_locator_and_observation(self):
        snapshot = self.capture()
        result = self.result(snapshot)
        result['findings'] = [{'claim': 'Possible missing branch', 'evidence': [
            {'path': 'code.py', 'locator': 'line 1', 'observation': 'Only uppercase call present'}]}]
        handoff.check(self.root, 'DEMO', snapshot, result)
        result['findings'][0]['evidence'][0]['path'] = '.gitignore'
        with self.assertRaisesRegex(ValueError, 'evidence'):
            handoff.check(self.root, 'DEMO', snapshot, result)

    def test_symlink_evidence_not_followed_and_unsafe_paths_rejected(self):
        outside = Path(self.tmp.name) / 'secret'
        outside.write_text('do not read')
        (self.feature / 'sources/link').symlink_to(outside)
        snapshot = self.capture()
        state = snapshot['inputs']['files']['.agent-workflow/features/DEMO/sources/link']
        self.assertEqual(state, {'state': 'unavailable', 'reason': 'symlink'})
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            self.capture(['../secret'])

    def test_input_moving_during_capture_rejected(self):
        first = handoff.collect(self.root, 'DEMO', self.base, [])
        second = dict(first, git_head='moving')
        with patch.object(handoff, 'collect', side_effect=[first, second]):
            with self.assertRaisesRegex(ValueError, 'during capture'):
                self.capture()

    def test_deleted_file_can_be_cited_only_as_bound_baseline_evidence(self):
        self.git('rm', 'code.py')
        self.git('commit', '-qm', 'remove implementation')
        snapshot = self.capture()
        result = self.result(snapshot)
        result['read_paths'] = ['base:code.py']
        result['findings'] = [{'claim': 'Implementation was removed', 'evidence': [
            {'path': 'base:code.py', 'locator': 'baseline line 1', 'observation': 'Uppercase implementation existed'}]}]
        handoff.check(self.root, 'DEMO', snapshot, result)
        result['read_paths'] = ['base:missing.py']
        with self.assertRaisesRegex(ValueError, 'baseline path'):
            handoff.check(self.root, 'DEMO', snapshot, result)

    def test_submodule_is_explicitly_unsupported(self):
        self.git('update-index', '--add', '--cacheinfo', '160000,' + self.base + ',vendor')
        with self.assertRaisesRegex(ValueError, 'submodules'):
            self.capture()

    def test_tracked_symlink_cannot_be_used_as_read_evidence(self):
        outside = Path(self.tmp.name) / 'external'
        outside.write_text('external content')
        (self.root / 'link').symlink_to(outside)
        self.git('add', 'link')
        snapshot = self.capture()
        result = self.result(snapshot)
        result['read_paths'].append('link')
        with self.assertRaises(ValueError):
            handoff.check(self.root, 'DEMO', snapshot, result)

    def test_cli_missing_result_fails_without_writes(self):
        snapshot = Path(self.tmp.name) / 'snapshot.json'
        snapshot.write_text(json.dumps(self.capture()))
        run = subprocess.run([sys.executable, str(SCRIPT), 'check', str(self.root), 'DEMO',
                              '--snapshot', str(snapshot), '--result', str(snapshot.parent / 'absent.json')],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertIn('VERIFY_HANDOFF_ERROR', run.stderr)


if __name__ == '__main__':
    unittest.main()
