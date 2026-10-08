import json
import sys
import unittest
import test_impact
from verification import sync, load_plan, context, record, retain, state, validate_verification


class VerificationTests(unittest.TestCase):
    write = test_impact.ImpactTests.write
    run_script = test_impact.ImpactTests.run_script
    git = test_impact.ImpactTests.git
    save = test_impact.ImpactTests.save

    def setUp(self):
        test_impact.ImpactTests.setUp(self)
        self.base = self.root / '.agent-workflow/project-baseline'
        self.base.mkdir()
        self.gates([sys.executable, '-c', 'assert 1 + 1 == 2'])
        sync(self.root, self.folder)

    def gates(self, command):
        (self.base / 'quality-gates.json').write_text(json.dumps({'gates': [{'name': 'unit', 'command': command, 'test_ids': ['UT-1']}]}))

    def plan(self):
        return load_plan(self.folder)

    def run_checks(self, expected=2):
        return self.run_script('verification.py', 'run', self.root, 'FEAT-001', expected=expected)

    def accept_manual(self):
        doc = self.plan()
        stamp, head = context(self.root, self.folder, doc)
        for row in doc['items']:
            if row['mode'] == 'manual':
                record(self.root, self.folder, row['id'], 'passed', stamp, head, 'Observed expected output on fixture', 'User observation on current fixture')

    def test_generate_defaults_and_idempotence(self):
        doc = self.plan()
        self.assertEqual(len(doc['items']), 4)
        self.assertEqual([r['mode'] for r in doc['items']].count('manual'), 3)
        self.assertTrue(all(not r['history'] for r in doc['items']))
        sync(self.root, self.folder)
        self.assertEqual(doc, self.plan())

    def test_run_records_actual_commands_without_passing_ui_items(self):
        self.run_checks()
        rows = self.plan()['items']
        self.assertEqual(rows[-1]['history'][-1]['status'], 'passed')
        self.assertTrue(all(not r['history'] for r in rows[:-1]))
        self.assertIn('verification incomplete', self.run_script('validate-feature.py', '--stage', 'check', self.root, 'FEAT-001', expected=1))

    def test_manual_completion_integrates_impact_gate_and_view(self):
        self.run_checks()
        self.accept_manual()
        self.run_script('validate-feature.py', '--stage', 'check', self.root, 'FEAT-001')
        self.run_script('verification.py', 'status', self.root, 'FEAT-001')
        self.run_script('render-workspace.py', self.root, 'FEAT-001')
        self.assertIn('Observed expected output', (self.folder / 'verification.md').read_text())

    def test_failed_and_unavailable_commands(self):
        self.gates([sys.executable, '-c', 'raise SystemExit(3)'])
        self.run_checks()
        self.assertEqual(self.plan()['items'][-1]['history'][-1]['status'], 'failed')
        self.gates(['fixture-command-that-does-not-exist'])
        self.run_checks()
        self.assertEqual(self.plan()['items'][-1]['history'][-1]['status'], 'unavailable')

    def test_source_and_mapping_changes_stale_results(self):
        self.run_checks(); self.accept_manual()
        (self.root / 'convert.py').write_text('changed implementation')
        stamp, _ = context(self.root, self.folder, self.plan())
        self.assertTrue(all(state(r, stamp) == 'stale' for r in self.plan()['items']))
        self.run_checks(); self.accept_manual()
        doc = self.plan(); doc['items'][0].update(mode='automatic', gates=['unit'], coverage='Assertion inspected for exact acceptance')
        self.write('verification.json', doc)
        stamp, _ = context(self.root, self.folder, self.plan())
        self.assertEqual(state(self.plan()['items'][0], stamp), 'stale')

    def test_explicit_mapping_automates_only_reviewed_items(self):
        doc = self.plan()
        doc['items'][0].update(mode='automatic', gates=['unit'], coverage='Fixture assertion covers this synthetic acceptance')
        self.write('verification.json', doc)
        self.run_checks()
        self.assertEqual(self.plan()['items'][0]['history'][-1]['status'], 'passed')
        self.assertFalse(self.plan()['items'][1]['history'])

    def test_old_identity_and_automatic_manual_override_rejected(self):
        doc = self.plan(); stamp, head = context(self.root, self.folder, doc)
        for item, token, revision in [(doc['items'][0], 'old', head), (doc['items'][0], stamp, 'bad'), (doc['items'][-1], stamp, head)]:
            with self.assertRaises(ValueError):
                record(self.root, self.folder, item['id'], 'passed', token, revision, 'observed', 'evidence')

    def test_failure_history_and_removed_items_preserved(self):
        doc = self.plan(); stamp, head = context(self.root, self.folder, doc)
        row = doc['items'][0]
        record(self.root, self.folder, row['id'], 'failed', stamp, head, 'Wrong output', 'Observed')
        record(self.root, self.folder, row['id'], 'passed', stamp, head, 'Correct output', 'Retest observed')
        req = json.loads((self.folder / 'spec/requirements.json').read_text())
        req['requirements'][0]['acceptance_criteria'][0] = 'New acceptance condition'
        self.write('spec/requirements.json', req)
        sync(self.root, self.folder)
        self.assertEqual(len(self.plan()['retired'][0]['history']), 2)
        self.assertFalse(self.plan()['items'][0]['history'])

    def test_drift_during_command_cannot_pass(self):
        self.gates([sys.executable, '-c', "from pathlib import Path; Path('convert.py').write_text('changed during test')"])
        self.run_checks()
        self.assertEqual(self.plan()['items'][-1]['history'][-1]['status'], 'unavailable')

    def test_no_gates_and_unknown_mapping_do_not_execute(self):
        (self.base / 'quality-gates.json').write_text('{"gates": []}')
        sync(self.root, self.folder)
        self.run_checks()
        self.assertTrue(any(r['source'] == 'system:no-gates' for r in self.plan()['items']))
        self.gates([sys.executable, '-c', "from pathlib import Path; Path('SHOULD_NOT_RUN').touch()"])
        sync(self.root, self.folder)
        doc = self.plan(); doc['items'][0].update(mode='automatic', gates=['unknown'], coverage='invalid')
        self.write('verification.json', doc)
        self.run_checks(expected=1)
        self.assertFalse((self.root / 'SHOULD_NOT_RUN').exists())

    def test_required_missing_and_legacy_compatibility(self):
        req = json.loads((self.folder / 'spec/requirements.json').read_text())
        (self.folder / 'verification.json').unlink()
        self.assertTrue(validate_verification(self.root, self.folder, req, 'check'))
        req['feature'].pop('verification_required')
        self.assertFalse(validate_verification(self.root, self.folder, req, 'check'))

    def test_stale_quality_report_cannot_be_reused(self):
        self.run_checks()
        self.gates([])
        # Invalid configuration must fail before it can borrow the earlier green report.
        self.run_checks(expected=1)

    def test_scoped_copy_change_retains_prior_navigation_observation_without_retest(self):
        (self.root / 'copy.txt').write_text('Original display copy')
        self.doc['allowed_paths'].append('copy.txt')
        self.doc['inspected_paths'].append('copy.txt')
        self.save()
        plan = self.plan()
        navigation = next(r for r in plan['items'] if r['source'] == 'impact:B-2')
        navigation['dependencies'] = ['convert.py', 'state.py']
        navigation['scope_reason'] = 'Navigation/shared-state behavior depends on these inspected implementation files'
        self.write('verification.json', plan)
        # Establish evidence after the copy file and reviewed impact boundary exist.
        self.run_checks(); self.accept_manual()
        navigation = next(r for r in self.plan()['items'] if r['source'] == 'impact:B-2')
        original = navigation['history'][-1]
        (self.root / 'copy.txt').write_text('New display copy')
        stamp, _ = context(self.root, self.folder, self.plan())
        self.assertEqual(state(navigation, stamp), 'stale')
        with self.assertRaisesRegex(ValueError, 'review every changed'):
            retain(self.root, self.folder, navigation['id'], stamp, ['convert.py'], 'Navigation does not read copy', 'Reviewed call path')
        retain(self.root, self.folder, navigation['id'], stamp, ['copy.txt'],
               'Copy is displayed as inert text; the navigation callback and shared state are unchanged',
               'Compared copy.txt diff and the registered navigation caller; no click handler reads this value')
        retained = next(r for r in self.plan()['items'] if r['id'] == navigation['id'])['history'][-1]
        self.assertEqual(retained['status'], 'retained')
        self.assertEqual(retained['tested_revision'], original['tested_revision'])
        self.assertNotEqual(retained['reviewed_revision'], '')
        self.assertEqual(state(next(r for r in self.plan()['items'] if r['id'] == navigation['id']), stamp), 'retained')
        visible = json.loads(self.run_script('verification.py', 'status', self.root, 'FEAT-001', expected=2))
        item = next(i for i in visible['items'] if i['id'] == navigation['id'])
        self.assertEqual((item['tested_revision'], item['reviewed_revision']), (retained['tested_revision'], retained['reviewed_revision']))
        self.assertEqual(state(self.plan()['items'][-1], stamp), 'stale')  # gate must rerun
        (self.root / 'copy.txt').write_text('Another copy change')
        next_stamp, _ = context(self.root, self.folder, self.plan())
        self.assertEqual(state(next(r for r in self.plan()['items'] if r['id'] == navigation['id']), next_stamp), 'stale')

    def test_scoped_relevance_unknown_or_semantic_change_cannot_carry_pass(self):
        plan = self.plan()
        row = next(r for r in plan['items'] if r['source'] == 'impact:B-2')
        row['dependencies'] = ['state.py']
        row['scope_reason'] = 'Preserved shared-state behavior uses state.py'
        self.write('verification.json', plan)
        self.accept_manual()
        (self.root / 'convert.py').write_text('changed shared implementation')
        stamp, _ = context(self.root, self.folder, self.plan())
        with self.assertRaisesRegex(ValueError, 'reasoning'):
            retain(self.root, self.folder, row['id'], stamp, ['convert.py'], '', '')
        req = json.loads((self.folder / 'spec/requirements.json').read_text())
        req['requirements'][0]['statement'] = 'Different business meaning'
        self.write('spec/requirements.json', req)
        stamp, _ = context(self.root, self.folder, self.plan())
        with self.assertRaisesRegex(ValueError, 'semantic'):
            retain(self.root, self.folder, row['id'], stamp, ['convert.py'], 'Looks unrelated', 'Reviewed diff')

    def test_clickable_copy_and_shared_code_dependencies_require_retest(self):
        (self.root / 'copy.txt').write_text('Clickable link copy')
        self.doc['allowed_paths'].extend(['copy.txt', 'state.py'])
        self.doc['inspected_paths'].append('copy.txt')
        self.save()
        plan = self.plan()
        row = next(r for r in plan['items'] if r['source'] == 'impact:B-2')
        row['dependencies'] = ['copy.txt', 'state.py']
        row['scope_reason'] = 'Click target and navigation state are both consumed by this behavior'
        self.write('verification.json', plan)
        self.accept_manual()
        (self.root / 'copy.txt').write_text('Changed clickable link copy')
        stamp, _ = context(self.root, self.folder, self.plan())
        with self.assertRaisesRegex(ValueError, 'dependency changed'):
            retain(self.root, self.folder, row['id'], stamp, ['copy.txt'], 'Unrelated', 'Reviewed')
        self.accept_manual()
        (self.root / 'state.py').write_text('changed navigation state')
        stamp, _ = context(self.root, self.folder, self.plan())
        with self.assertRaisesRegex(ValueError, 'dependency changed'):
            retain(self.root, self.folder, row['id'], stamp, ['state.py'], 'Unrelated', 'Reviewed')
