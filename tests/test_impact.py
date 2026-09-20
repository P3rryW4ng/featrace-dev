import copy
import json
import subprocess
import unittest
import test_fix_flow
from impact import MECHANISMS, snapshot, validate_impact


class ImpactTests(unittest.TestCase):
    write = test_fix_flow.FixFlowTests.write
    run_script = test_fix_flow.FixFlowTests.run_script

    def setUp(self):
        test_fix_flow.FixFlowTests.setUp(self)
        self.git('init')
        (self.root / 'convert.py').write_text('original')
        (self.root / 'state.py').write_text('shared')
        self.git('add', 'convert.py', 'state.py')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'base')
        self.req['feature']['impact_required'] = True
        self.write('spec/requirements.json', self.req)
        self.doc = {'schema_version': 1, 'feature_id': 'FEAT-001',
                    'base_revision': self.git('rev-parse', 'HEAD').strip(),
                    'allowed_paths': ['convert.py'], 'inspected_paths': ['convert.py', 'state.py'],
                    'excluded_changes': {},
                    'mechanisms': {k: {'status': 'reviewed', 'evidence': 'convert.py and state.py inspected'} for k in MECHANISMS},
                    'behaviors': [{'id': 'B-1', 'kind': 'change', 'statement': 'Convert input', 'basis': 'R-1', 'requirement_ids': ['R-1']},
                                  {'id': 'B-2', 'kind': 'preserve', 'statement': 'Keep shared state', 'basis': 'state.py existing contract', 'requirement_ids': ['R-1']}]}
        self.save()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.DEVNULL, text=True)

    def save(self):
        self.write('impact.json', self.doc)

    def errors(self, stage='check'):
        self.save()
        return validate_impact(self.root, self.folder, self.req, stage)[0]

    def accept(self):
        stamp = snapshot(self.root, self.doc)['digest']
        for b in self.doc['behaviors']:
            b['verification'] = {'status': 'passed', 'method': 'synthetic manual observation', 'evidence': 'Fixture observed correct output', 'digest': stamp}
        self.save()

    def test_missing_adopted_record_blocks_but_legacy_warns(self):
        (self.folder / 'impact.json').unlink()
        self.assertTrue(validate_impact(self.root, self.folder, self.req, 'develop')[0])
        del self.req['feature']['impact_required']
        errors, warnings = validate_impact(self.root, self.folder, self.req, 'check')
        self.assertFalse(errors); self.assertTrue(warnings)

    def test_unknown_blocks_develop_but_not_draft(self):
        self.doc['mechanisms']['navigation']['status'] = 'unknown'
        self.assertFalse(self.errors('draft'))
        self.assertTrue(self.errors('develop'))
        self.doc['mechanisms']['navigation']['status'] = 'not_applicable'
        self.doc['behaviors'][0]['kind'] = 'unknown'
        self.assertTrue(self.errors('develop'))

    def test_delivery_requires_both_changed_and_preserved_regression(self):
        self.assertFalse(self.errors('develop'))
        self.assertEqual(len(self.errors()), 2)
        self.accept()
        self.assertFalse(self.errors())
        self.doc['behaviors'][1]['verification']['status'] = 'planned'
        self.assertTrue(self.errors())

    def test_source_changes_stale_results_and_scope_expansion_blocks(self):
        self.accept()
        (self.root / 'convert.py').write_text('changed')
        self.assertTrue(any('stale' in x for x in self.errors()))
        self.accept()
        (self.root / 'state.py').write_text('changed shared state')
        errors = self.errors()
        self.assertTrue(any('scope expansion' in x for x in errors))
        self.assertTrue(any('stale' in x for x in errors))

    def test_new_files_and_rename_both_paths_detected(self):
        (self.root / 'convert.py').rename(self.root / 'new.py')
        self.git('add', '-A', 'convert.py', 'new.py')
        self.assertEqual(snapshot(self.root, self.doc)['changed_paths'], ['convert.py', 'new.py'])
        self.accept()
        self.assertTrue(any('new.py' in x for x in self.errors()))

    def test_contract_edit_stales_but_workflow_progress_does_not(self):
        self.accept()
        (self.folder / 'tasks.md').write_text('progress only')
        self.assertFalse(self.errors())
        self.doc['behaviors'][1]['statement'] = 'Different preservation contract'
        self.assertTrue(any('stale' in x for x in self.errors()))

    def test_exclusions_and_waiver_need_explicit_evidence(self):
        (self.root / 'notes.txt').write_text('unrelated user draft')
        self.doc['excluded_changes']['notes.txt'] = 'Pre-existing user notes, unrelated to feature'
        self.accept()
        self.doc['behaviors'][1]['verification']['status'] = 'waived'
        self.doc['behaviors'][1]['verification']['evidence'] = 'No runtime in fixture; accepted manual follow-up with owner'
        self.assertFalse(self.errors())
        self.doc['excluded_changes']['notes.txt'] = ''
        self.assertTrue(self.errors())

    def test_invalid_paths_and_malformed_records_fail_cleanly(self):
        original = copy.deepcopy(self.doc)
        for field, value in [('allowed_paths', ['../outside']), ('inspected_paths', [17]), ('behaviors', [None]), ('mechanisms', []), ('base_revision', 'HEAD')]:
            self.doc = copy.deepcopy(original); self.doc[field] = value
            self.assertTrue(self.errors())
        self.doc = original
        (self.root / 'state.py').unlink()
        (self.root / 'state.py').symlink_to('/etc/hosts')
        self.assertTrue(self.errors())

    def test_helper_validation_and_renderer_integrated(self):
        self.accept()
        output = self.run_script('impact.py', self.root, 'FEAT-001')
        self.assertEqual(json.loads(output)['digest'], snapshot(self.root, self.doc)['digest'])
        self.run_script('validate-feature.py', '--stage', 'check', self.root, 'FEAT-001')
        self.run_script('render-workspace.py', self.root, 'FEAT-001')
        self.assertIn('Keep shared state', (self.folder / 'impact.md').read_text())
        (self.root / 'extra.py').write_text('new code')
        self.assertIn('scope expansion', self.run_script('validate-feature.py', '--stage', 'check', self.root, 'FEAT-001', expected=1))

    def test_content_evidence_survives_commit_without_code_change(self):
        (self.root / 'convert.py').write_text('changed')
        self.accept()
        self.git('add', 'convert.py')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'implementation')
        self.assertFalse(self.errors())
