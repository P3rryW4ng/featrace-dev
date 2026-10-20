"""Read-only reentry decisions on synthetic checks; no Android acceptance claims."""
import json
import sys
import unittest
from unittest.mock import patch
import test_verification as fixtures
import verification as v
import test_acceptance_continuation as entry_fixture
from intake_helpers import attach_intake


class VerifyReentryTests(unittest.TestCase):
    def inventory(self, root, folder):
        return entry_fixture.AcceptanceContinuationTests.inventory(self, root.resolve(), folder.resolve())

    def fixture(self):
        x = fixtures.VerificationTests()
        x.setUp()
        self.addCleanup(x.doCleanups)
        return x

    def test_sync_required_has_bounded_reentry_then_new_claim_remains_unproved(self):
        x = self.fixture()
        req = v.read(x.folder / 'spec/requirements.json')
        req['requirements'][0]['acceptance_criteria'].append('New icon presentation must match the approved reference')
        attach_intake(x.folder, req)
        before = (x.folder / 'verification.json').read_bytes()
        with patch.object(v.subprocess, 'run', wraps=v.subprocess.run) as commands:
            first = self.inventory(x.root, x.folder)
        self.assertEqual(first['next_step']['action'], 'sync_then_reinspect')
        self.assertEqual(first['continuation']['blocker_code'], 'plan_sync_required')
        self.assertEqual(before, (x.folder / 'verification.json').read_bytes())
        self.assertFalse((x.base / 'quality-report.json').exists())
        self.assertFalse(any('project.py' in str(c.args) for c in commands.call_args_list))
        v.sync(x.root, x.folder)
        second = self.inventory(x.root, x.folder)
        new = next(r for r in v.load_plan(x.folder)['items'] if r['expected'].startswith('New icon'))
        self.assertIn(new['id'], second['continuation']['manual_applicability']['new_or_adverse_claims'])
        self.assertNotEqual(second['next_step']['action'], 'review_delivery')
        self.assertNotIn('manual_scope_contract', v.load_plan(x.folder))

    def test_current_legacy_result_routes_to_review_without_execution_after_record_commit(self):
        x = self.fixture()
        x.run_checks()
        before = (x.base / 'quality-report.json').read_bytes()
        (x.folder / 'note.md').write_text('Synthetic workflow-only follow-up')
        x.git('add', '.agent-workflow')
        x.git('commit', '-qm', 'save synthetic records')
        guide = self.inventory(x.root, x.folder)
        self.assertEqual(guide['next_step']['action'], 'review_delivery')
        self.assertEqual(guide['continuation']['legacy_execution']['state'], 'current')
        self.assertTrue(guide['continuation']['manual_pending'])
        self.assertEqual(before, (x.base / 'quality-report.json').read_bytes())
        self.assertEqual(guide['continuation']['contract'], 'legacy')
        self.assertEqual(guide['continuation']['execution_state'], 'not_evaluated')

    def test_latest_failure_never_uses_an_older_success(self):
        x = self.fixture()
        x.run_checks()
        x.gates([sys.executable, '-c', 'raise SystemExit(7)'])
        x.run_checks()
        guide = self.inventory(x.root, x.folder)
        self.assertEqual(guide['next_step']['action'], 'investigate_execution')
        self.assertEqual(guide['continuation']['legacy_execution']['state'], 'unavailable')
        self.assertIn('failed', guide['continuation']['reason'])
        self.assertNotIn('claim_review_targets', guide['continuation'])

    def test_changed_business_inputs_never_route_to_delivery(self):
        x = self.fixture()
        x.run_checks()
        (x.root / 'convert.py').write_text('new runtime input')
        guide = self.inventory(x.root, x.folder)
        self.assertEqual(guide['next_step']['action'], 'investigate_execution')
        self.assertEqual(guide['continuation']['legacy_execution']['state'], 'unavailable')

    def test_current_report_does_not_rebind_changed_legacy_claims(self):
        x = self.fixture()
        x.run_checks()
        req = v.read(x.folder / 'spec/requirements.json')
        req['requirements'][0]['statement'] += '; clarified display target'
        attach_intake(x.folder, req)
        before = (x.folder / 'verification.json').read_bytes()
        guide = self.inventory(x.root, x.folder)
        self.assertEqual(guide['next_step']['action'], 'review_legacy_binding')
        self.assertEqual(guide['continuation']['legacy_execution']['state'], 'current')
        self.assertTrue(guide['continuation']['automatic_pending'])
        self.assertEqual(before, (x.folder / 'verification.json').read_bytes())

    def test_incomplete_or_unknown_execution_and_invalid_mapping_stay_blocked(self):
        x = self.fixture()
        x.run_checks()
        report = x.base / 'quality-report.json'
        original = v.read(report)
        for mutate in (lambda d: d.update(results=[]),
                       lambda d: d.update(input_comparison={'state': 'unknown'})):
            d = json.loads(json.dumps(original)); mutate(d)
            report.write_text(json.dumps(d))
            self.assertEqual(self.inventory(x.root, x.folder)['next_step']['action'], 'investigate_execution')
        report.write_text(json.dumps(original))
        plan = v.load_plan(x.folder)
        plan['items'][0].update(mode='automatic', gates=['missing'], coverage='Invalid fixture mapping')
        v.save(x.folder / 'verification.json', plan)
        guide = self.inventory(x.root, x.folder)
        self.assertEqual(guide['next_step']['action'], 'resolve_blocker')
        self.assertNotEqual(guide['continuation'].get('blocker_code'), 'plan_sync_required')
