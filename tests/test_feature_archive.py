import json
import subprocess
import unittest
import test_fix_flow
from prd_intake import review_digest


class FeatureArchiveTests(unittest.TestCase):
    write = test_fix_flow.FixFlowTests.write
    run_script = test_fix_flow.FixFlowTests.run_script

    def setUp(self):
        test_fix_flow.FixFlowTests.setUp(self)
        self.req['feature'].update(status='complete', title='Synthetic uppercase')
        self.write('spec/requirements.json', self.req)
        (self.folder / 'delivery-report.md').write_text('Synthetic revision fixture-v1; unit test passed; no device required.')

    def command(self, action, *args, expected=0):
        return self.run_script('feature-archive.py', action, self.root, 'FEAT-001', *args, expected=expected)

    def archive(self, expected=0):
        return self.command('archive', '--reason', 'Accepted delivery', '--revision', 'fixture-v1', expected=expected)

    def feature(self):
        return json.loads((self.folder / 'spec/requirements.json').read_text())['feature']

    def listing(self, *args):
        return json.loads(self.run_script('feature-context.py', 'list', self.root, *args))['features']

    def test_archive_preserves_sources_report_status_and_default_listing(self):
        originals = {p: p.read_bytes() for p in self.folder.rglob('*') if p.is_file() and p.name != 'requirements.json'}
        self.archive()
        feature = self.feature()
        self.assertTrue(feature['archive']['archived'])
        self.assertEqual(feature['status'], 'complete')
        self.assertEqual(feature['archive']['history'][0]['revision'], 'fixture-v1')
        self.assertEqual(len(feature['archive']['history'][0]['evidence_sha256']), 64)
        self.assertEqual(self.listing(), [])
        self.assertEqual(len(self.listing('--scope', 'archived')), 1)
        self.assertEqual(len(self.listing('--scope', 'all')), 1)
        self.assertEqual(originals, {p: p.read_bytes() for p in self.folder.rglob('*') if p.is_file() and p.name != 'requirements.json'})

    def test_restore_preserves_history_and_is_idempotent(self):
        self.archive()
        self.assertIn('UNCHANGED', self.archive())
        self.command('restore', '--reason', 'Investigate regression')
        self.assertIn('UNCHANGED', self.command('restore'))
        self.assertFalse(self.feature()['archive']['archived'])
        self.assertEqual(self.feature()['status'], 'complete')
        self.assertEqual([e['action'] for e in self.feature()['archive']['history']], ['archive', 'restore'])
        self.assertEqual(len(self.listing()), 1)
        self.archive()
        self.assertEqual(len(self.feature()['archive']['history']), 3)

    def test_modules_many_to_many_and_clear_without_semantic_review_change(self):
        intake = json.loads((self.folder / 'spec/prd-intake.json').read_text())
        before = review_digest(self.folder, intake, self.req)
        self.command('classify', '--module', '钱包', '--module', 'identity')
        self.assertEqual(len(self.listing('--module', '钱包')), 1)
        self.assertEqual(len(self.listing('--module', 'identity')), 1)
        self.assertEqual(self.listing('--module', 'unknown'), [])
        self.assertEqual(before, review_digest(self.folder, intake, json.loads((self.folder / 'spec/requirements.json').read_text())))
        self.archive()
        self.assertEqual(len(self.listing('--scope', 'archived', '--module', '钱包')), 1)
        self.command('classify', '--clear-modules')
        self.assertEqual(self.feature()['modules'], [])

    def test_archive_rejects_incomplete_feature_or_tasks(self):
        for change in ('status', 'tasks', 'requirements', 'sources'):
            with self.subTest(change=change):
                req = json.loads(json.dumps(self.req))
                tasks = {'feature_id': 'FEAT-001', 'tasks': [{'id':'T-1', 'title':'Implement', 'status':'done', 'requirement_ids':['R-1'], 'test_evidence':['fixture']}]}
                if change == 'status': req['feature']['status'] = 'drafted'
                if change == 'tasks': tasks['tasks'][0]['status'] = 'in_progress'
                if change == 'requirements': req['requirements'][0]['status'] = 'inferred'
                if change == 'sources': req['feature']['source_status']['api'] = 'unknown'
                self.write('spec/requirements.json', req)
                self.write('tasks.json', tasks)
                before = (self.folder / 'spec/requirements.json').read_bytes()
                self.archive(expected=1)
                self.assertEqual(before, (self.folder / 'spec/requirements.json').read_bytes())

    def test_pending_decision_and_unresolved_fix_reject(self):
        self.write('decisions.json', {'feature_id':'FEAT-001','decisions':[{'id':'D-1','status':'pending'}]})
        self.archive(expected=1)
        self.write('decisions.json', {'feature_id':'FEAT-001','decisions':[]})
        self.run_script('record-fix.py', self.root, 'FEAT-001', 'bad output')
        # Even a manually set complete status cannot hide the open fix.
        req = json.loads((self.folder/'spec/requirements.json').read_text())
        req['feature']['status'] = 'complete'
        self.write('spec/requirements.json', req)
        self.archive(expected=1)
        self.assertNotIn('archive', self.feature())

    def test_preflight_creates_review_draft_and_archive_rejects_until_reviewed(self):
        report = self.folder / 'delivery-report.md'
        report.unlink()
        output = self.run_script('archive-preflight.py', self.root, 'FEAT-001', '--revision', 'fixture-v1')
        payload = json.loads(output.split('ARCHIVE_PREFLIGHT: ', 1)[1])
        self.assertTrue(payload['created'])
        self.assertTrue(payload['review_required'])
        text = report.read_text()
        self.assertIn('ARCHIVE_REPORT_DRAFT_REVIEW_REQUIRED', text)
        self.assertIn('Synthetic uppercase', text)
        self.assertIn('UT-1', text)
        self.archive(expected=1)
        report.write_text(text.replace('<!-- ARCHIVE_REPORT_DRAFT_REVIEW_REQUIRED -->', '')
                          .replace('Status: **DRAFT — REVIEW REQUIRED**', 'Status: **REVIEWED**'))
        self.archive()
        self.assertTrue(self.feature()['archive']['archived'])

    def test_preflight_preserves_existing_report_and_suggests_registered_module(self):
        original = (self.folder / 'delivery-report.md').read_bytes()
        trace = json.loads((self.folder / 'traceability.json').read_text())
        trace['links'][0]['code'] = ['wallet/convert.py']
        self.write('traceability.json', trace)
        modules = self.root / '.agent-workflow/modules'
        modules.mkdir()
        (modules / 'index.json').write_text(json.dumps({'schema_version': 1, 'shared_stack': 'fixture',
            'global_files': ['build.cfg'], 'modules': [{'id': 'wallet', 'summary': 'wallet',
            'roots': ['wallet'], 'evidence_files': [], 'depends_on': []}]}))
        req = json.loads((self.folder / 'spec/requirements.json').read_text())
        req['feature']['prd_paths'] = ['sources/prd-original.txt']
        self.write('spec/requirements.json', req)
        subprocess.run(['git', 'init', str(self.root)], check=True, capture_output=True)
        (self.root / '.gitignore').write_text('.agent-workflow/features/*/sources/**\n')
        output = self.run_script('archive-preflight.py', self.root, 'FEAT-001')
        payload = json.loads(output.split('ARCHIVE_PREFLIGHT: ', 1)[1])
        self.assertFalse(payload['created'])
        self.assertFalse(payload['review_required'])
        self.assertEqual(payload['module_candidates'], ['wallet'])
        self.assertEqual(payload['sources'], [{'path': 'sources/prd-original.txt', 'state': 'ignored_by_policy'}])
        self.assertEqual(original, (self.folder / 'delivery-report.md').read_bytes())

    def test_missing_empty_or_outside_evidence_rejects(self):
        self.command('archive', '--reason', 'done', expected=1)
        report = self.folder / 'delivery-report.md'
        self.command('archive', '--reason', 'done', '--revision', 'v1', '--evidence', report, expected=1)
        report.write_text('')
        self.archive(expected=1)
        report.unlink()
        self.archive(expected=1)
        self.command('archive', '--reason', 'done', '--revision', 'v1', '--evidence', '../../../outside.md', expected=1)
        self.assertNotIn('archive', self.feature())

    def test_archived_mutations_blocked_but_status_and_render_allowed(self):
        self.archive()
        before = (self.folder / 'spec/requirements.json').read_bytes()
        self.run_script('record-fix.py', self.root, 'FEAT-001', 'regression', expected=2)
        self.run_script('record-clarification.py', self.root, 'FEAT-001', 'new question', expected=2)
        for stage in ('develop', 'check'):
            self.run_script('validate-feature.py', '--stage', stage, self.root, 'FEAT-001', expected=1)
        self.assertEqual(before, (self.folder / 'spec/requirements.json').read_bytes())
        self.assertIn('ARCHIVED: True', self.run_script('feature-status.py', self.root, 'FEAT-001'))
        self.run_script('render-workspace.py', self.root, 'FEAT-001')
        self.assertIn('Archived: True', (self.folder / 'spec/spec.md').read_text())
        self.assertTrue(json.loads(self.run_script('feature-context.py', 'use', self.root, '--feature', 'FEAT-001'))['archived'])
        self.command('restore', '--reason', 'Investigate regression')
        self.run_script('record-fix.py', self.root, 'FEAT-001', 'regression')
        self.assertEqual(self.feature()['status'], 'provisional')

    def test_bad_metadata_and_duplicate_modules_preserved(self):
        self.command('classify', '--module', 'wallet', '--module', 'wallet', expected=1)
        self.assertNotIn('modules', self.feature())
        self.req['feature']['archive'] = {'archived':True, 'history':[]}
        self.write('spec/requirements.json', self.req)
        before = (self.folder/'spec/requirements.json').read_bytes()
        self.command('restore', '--reason', 'repair', expected=1)
        self.assertEqual(before, (self.folder/'spec/requirements.json').read_bytes())
        self.assertIn('error', self.listing()[0])

    def test_symlink_record_and_evidence_rejected(self):
        report = self.folder / 'delivery-report.md'
        report.unlink()
        report.symlink_to(self.folder / 'sources/prd-original.txt')
        self.archive(expected=1)
        record = self.folder / 'spec/requirements.json'
        other = self.root / 'record.json'
        record.rename(other)
        record.symlink_to(other)
        self.command('classify', '--module', 'wallet', expected=1)
        self.assertNotIn('modules', json.loads(other.read_text())['feature'])
