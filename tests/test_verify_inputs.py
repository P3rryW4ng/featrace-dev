import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'skills/dev/core/scripts/verify-inputs.py'


class VerifyInputsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'project'
        self.folder = self.root / '.agent-workflow/features/FEAT-1'
        (self.folder / 'spec').mkdir(parents=True)
        (self.folder / 'sources').mkdir()
        self.base = self.root / '.agent-workflow/project-baseline'
        self.base.mkdir()
        (self.root / '.gitignore').write_text('/.agent-workflow/features/*/sources/\n/.agent-workflow/project-baseline/quality-report.json\n')
        (self.root / 'code.py').write_text('print("old behavior")\n')
        (self.folder / 'sources/prd.txt').write_text('Keep old behavior.\n')
        (self.folder / 'sources/design.png').write_bytes(b'fake synthetic image')
        self.write('spec/requirements.json', {'feature': {'id': 'FEAT-1',
                   'source_status': {'prd': 'present'}, 'prd_paths': ['sources/prd.txt']},
                   'requirements': []})
        self.write('spec/prd-intake.json', {'feature_id': 'FEAT-1', 'sources': [
                   {'id': 'SRC-01', 'kind': 'document', 'path': 'sources/prd.txt'}]})
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')
        self.head = self.git('rev-parse', 'HEAD').strip()
        self.quality(self.head)

    def write(self, relative, doc):
        (self.folder / relative).write_text(json.dumps(doc))

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True)

    def quality(self, head):
        (self.base / 'quality-report.json').write_text(json.dumps({
            'tested_at': '2026-09-24T00:00:00Z', 'project_snapshot': {'git_head': head},
            'results': [{'name': 'unit', 'status': 'passed'}]}))

    def check(self, expected=0):
        run = subprocess.run([sys.executable, str(SCRIPT), str(self.root), 'FEAT-1'],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, expected, run.stdout + run.stderr)
        return json.loads(run.stdout) if expected == 0 else run.stderr

    def test_current_sources_and_supplementary_file_are_reported_without_writes(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file() and '.git' not in p.parts}
        report = self.check()
        self.assertEqual(report['status'], 'inputs_identified')
        self.assertEqual(report['git_head'], self.head)
        self.assertEqual(report['worktree_changed_paths'], [])
        self.assertEqual(report['quality_report']['recorded_git_head'], self.head)
        self.assertEqual([(row['path'], row['indexed']) for row in report['sources']], [
            ('sources/design.png', False), ('sources/prd.txt', True)])
        self.assertTrue(all(row['state'] == 'readable' and len(row['sha256']) == 64 for row in report['sources']))
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_missing_source_and_old_quality_are_visible_not_claimed_passed(self):
        (self.folder / 'sources/prd.txt').unlink()
        self.quality('older-head')
        report = self.check()
        self.assertEqual(report['status'], 'review_required')
        self.assertIn('source_unavailable', report['issues_to_review'])
        self.assertIn('quality_report_revision_differs_from_head_check_currency', report['issues_to_review'])
        self.assertEqual(report['sources'][-1]['state'], 'unavailable')

    def test_dirty_code_and_conflicting_source_indices_are_reported(self):
        (self.root / 'code.py').write_text('print("changed")\n')
        intake = json.loads((self.folder / 'spec/prd-intake.json').read_text())
        intake['sources'][0]['path'] = 'sources/design.png'
        self.write('spec/prd-intake.json', intake)
        report = self.check()
        self.assertEqual(report['worktree_changed_paths'], ['.agent-workflow/features/FEAT-1/spec/prd-intake.json', 'code.py'])
        self.assertIn('source_indices_disagree', report['issues_to_review'])

    def test_outside_source_path_is_not_read(self):
        req = json.loads((self.folder / 'spec/requirements.json').read_text())
        req['feature']['prd_paths'] = ['../../../../code.py']
        self.write('spec/requirements.json', req)
        report = self.check()
        self.assertEqual(report['status'], 'review_required')
        self.assertEqual(report['sources'][0]['state'], 'unavailable')
        self.assertIn('source_unavailable', report['issues_to_review'])

    def test_symlinked_source_directory_is_not_followed(self):
        external = Path(self.temp.name) / 'elsewhere'
        self.folder.joinpath('sources/prd.txt').unlink()
        self.folder.joinpath('sources/design.png').unlink()
        self.folder.joinpath('sources').rmdir()
        external.mkdir()
        (external / 'prd.txt').write_text('outside')
        (self.folder / 'sources').symlink_to(external, target_is_directory=True)
        report = self.check()
        self.assertEqual(report['sources'][0]['state'], 'unavailable')
        self.assertIn('sources directory is a symlink', report['sources'][0]['reason'])

    def test_invalid_quality_report_is_not_treated_as_test_evidence(self):
        (self.base / 'quality-report.json').write_text('{broken')
        report = self.check()
        self.assertEqual(report['quality_report']['state'], 'invalid')
        self.assertIn('quality_report_invalid', report['issues_to_review'])

    def test_symlinked_quality_report_is_not_read(self):
        external = Path(self.temp.name) / 'other-report.json'
        external.write_text('{"tested_at":"fake"}')
        (self.base / 'quality-report.json').unlink()
        (self.base / 'quality-report.json').symlink_to(external)
        report = self.check()
        self.assertEqual(report['quality_report']['state'], 'invalid')
        self.assertIn('quality_report_invalid', report['issues_to_review'])

    def test_legacy_intake_units_are_accepted_as_source_index(self):
        req = json.loads((self.folder / 'spec/requirements.json').read_text())
        req['feature'].pop('prd_paths')
        self.write('spec/requirements.json', req)
        self.write('spec/prd-intake.json', {'feature_id': 'FEAT-1', 'units': [
            {'source': 'sources/prd.txt', 'locator': 'line 1'}]})
        report = self.check()
        self.assertNotIn('feature_source_index_missing_or_invalid', report['issues_to_review'])
        self.assertNotIn('prd_intake_source_index_invalid', report['issues_to_review'])
        self.assertEqual(next(row for row in report['sources'] if row['path'] == 'sources/prd.txt')['indexed'], True)


if __name__ == '__main__':
    unittest.main()
