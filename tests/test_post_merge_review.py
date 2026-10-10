import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'skills/dev/core/scripts/post-merge-review.py'


class PostMergeReviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        subprocess.run(['git', 'init', str(self.root)], check=True, capture_output=True)
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        folder = self.root / '.agent-workflow/features/F-1'
        (folder / 'spec').mkdir(parents=True)
        (folder / 'spec/requirements.json').write_text(json.dumps({
            'feature': {'id': 'F-1', 'status': 'complete'}}))
        (folder / 'delivery-report.md').write_text('Accepted at the fixture base revision.\n')
        (self.root / 'src').mkdir()
        (self.root / 'src/main.py').write_text('value = 1\n')
        self.commit('accepted')
        self.base = self.git('rev-parse', 'HEAD').strip()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout

    def commit(self, message):
        self.git('add', '.')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '-m', message)

    def review(self, *, base=None, expected=0):
        proc = subprocess.run([sys.executable, '-B', str(SCRIPT), str(self.root),
                               'F-1', '--base', base or self.base],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, expected, proc.stdout + proc.stderr)
        return json.loads(proc.stdout) if expected == 0 else proc.stderr

    def test_workflow_only_commit_needs_no_project_recheck(self):
        (self.root / '.agent-workflow/shared.md').write_text('new record\n')
        self.commit('records')
        result = self.review()
        self.assertEqual(result['state'], 'NO_PROJECT_CHANGE')
        self.assertEqual(result['project_changed_paths'], [])
        self.assertIn('.agent-workflow/shared.md', result['committed_changed_paths'])

    def test_merge_paths_are_listed_without_semantic_pass(self):
        self.git('checkout', '-b', 'incoming')
        (self.root / 'src/other.py').write_text('other = True\n')
        self.commit('other source')
        self.git('checkout', '-')
        (self.root / '.agent-workflow/shared.md').write_text('review note\n')
        self.commit('workflow note')
        self.git('merge', '--no-ff', '-m', 'merge incoming', 'incoming')
        result = self.review()
        self.assertEqual(result['state'], 'REVIEW_REQUIRED')
        self.assertEqual(result['project_changed_paths'], ['src/other.py'])
        self.assertIn('.agent-workflow/shared.md', result['committed_changed_paths'])
        self.assertIn('no old check', result['meaning'])

    def test_uncommitted_project_changes_are_visible(self):
        (self.root / '.agent-workflow/shared.md').write_text('merge review context\n')
        self.commit('workflow records')
        (self.root / 'src/main.py').write_text('value = 2\n')
        (self.root / 'src/new.py').write_text('new = True\n')
        result = self.review()
        self.assertEqual(result['state'], 'REVIEW_REQUIRED')
        self.assertEqual(result['project_changed_paths'], ['src/main.py', 'src/new.py'])

    def test_unaccepted_or_unrelated_base_is_rejected(self):
        self.assertIn('full delivered commit', self.review(base='abc', expected=2))
        self.assertIn('has not advanced', self.review(expected=2))
        record = self.root / '.agent-workflow/features/F-1/spec/requirements.json'
        record.write_text(json.dumps({'feature': {'id': 'F-1', 'status': 'provisional'}}))
        self.assertIn('already complete', self.review(expected=2))


if __name__ == '__main__':
    unittest.main()
