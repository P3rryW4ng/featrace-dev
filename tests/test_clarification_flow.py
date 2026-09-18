import json
import unittest
import test_fix_flow
from clarifications import validate_clarifications


class ClarificationTests(unittest.TestCase):
    setUp = test_fix_flow.FixFlowTests.setUp
    write = test_fix_flow.FixFlowTests.write
    run_script = test_fix_flow.FixFlowTests.run_script

    def record(self, question='Should retries preserve the supplied text?', expected=0):
        return self.run_script('record-clarification.py', self.root, 'FEAT-001', question, expected=expected)

    def decisions(self):
        return json.loads((self.folder / 'decisions.json').read_text())['decisions']

    def save(self, decisions):
        self.write('decisions.json', {'feature_id': 'FEAT-001', 'decisions': decisions})

    def approve(self, kind='change'):
        self.record()
        d = self.decisions()[0]
        d.update(status='approved', chosen='Preserve the text')
        d['clarification'].update(resolution_kind=kind, evidence=['fixture PRD and user reply'],
                                  impact_review='R-1, T-1 and UT-1; preserve existing uppercase behavior',
                                  confirmation_ref='fixture user reply 1')
        return d

    def test_registration_preserves_meaning_deduplicates_and_numbers(self):
        self.save([{'id': 'D-007', 'status': 'approved', 'chosen': 'existing option'}])
        original = (self.folder / 'spec/requirements.json').read_bytes()
        self.assertIn('D-008', self.record())
        self.assertIn('ALREADY_RECORDED', self.record())
        self.assertEqual(len(self.decisions()), 2)
        self.assertEqual(original, (self.folder / 'spec/requirements.json').read_bytes())
        self.assertIn('Should retries preserve', (self.folder / 'decisions.md').read_text())

    def test_pending_blocks_develop_and_check_but_allows_draft(self):
        self.record()
        self.run_script('validate-feature.py', '--stage', 'draft', self.root, 'FEAT-001')
        for stage in ('develop', 'check'):
            output = self.run_script('validate-feature.py', '--stage', stage, self.root, 'FEAT-001', expected=1)
            self.assertIn('unresolved decision', output)

    def test_complete_returns_to_provisional(self):
        self.req['feature']['status'] = 'complete'
        self.write('spec/requirements.json', self.req)
        self.record()
        self.assertEqual(json.loads((self.folder / 'spec/requirements.json').read_text())['feature']['status'], 'provisional')

    def test_confirmation_does_not_mean_applied(self):
        d = self.approve()
        self.save([d])
        self.run_script('validate-feature.py', '--stage', 'develop', self.root, 'FEAT-001')
        output = self.run_script('validate-feature.py', '--stage', 'check', self.root, 'FEAT-001', expected=1)
        self.assertIn('not yet applied', output)
        d['clarification']['application'] = {'status': 'applied', 'evidence': ['R-1/T-1 updated; UT-1 passed on fixture revision']}
        self.save([d])
        self.run_script('validate-feature.py', '--stage', 'check', self.root, 'FEAT-001')

    def test_missing_evidence_or_confirmation_rejected(self):
        for field in ('evidence', 'impact_review', 'confirmation_ref'):
            d = self.approve()
            d['clarification'][field] = [] if field == 'evidence' else ''
            self.assertTrue(validate_clarifications([d], 'develop')[0], field)

    def test_existing_rule_can_resolve_without_new_user_confirmation(self):
        d = self.approve('existing_rule')
        d['clarification']['confirmation_ref'] = ''
        d['clarification']['application'] = {'status': 'not_needed', 'evidence': ['existing PRD and implementation already agree']}
        self.save([d])
        self.run_script('validate-feature.py', '--stage', 'check', self.root, 'FEAT-001')

    def test_change_cannot_claim_no_application_needed(self):
        d = self.approve()
        d['clarification']['application'] = {'status': 'not_needed', 'evidence': ['skip changes']}
        self.assertTrue(validate_clarifications([d], 'check')[0])

    def test_malformed_records_preserved(self):
        for doc in ({'feature_id': 'OTHER', 'decisions': []}, {'feature_id': 'FEAT-001', 'decisions': [None]}):
            self.write('decisions.json', doc)
            before = (self.folder / 'decisions.json').read_bytes()
            self.record(expected=2)
            self.assertEqual(before, (self.folder / 'decisions.json').read_bytes())
        self.record(' ', expected=2)

    def test_supersession_requires_approved_replacement_and_unique_ids(self):
        self.record()
        d = self.decisions()[0]
        d.update(status='superseded', superseded_by='D-002')
        self.assertTrue(validate_clarifications([d], 'check')[0])
        replacement = {'id': 'D-002', 'status': 'approved', 'chosen': 'keep original behavior'}
        self.assertFalse(validate_clarifications([d, replacement], 'check')[0])
        self.assertTrue(validate_clarifications([replacement, replacement], 'check')[0])

    def test_status_and_render_show_pending_application(self):
        self.save([self.approve()])
        output = self.run_script('feature-status.py', self.root, 'FEAT-001')
        self.assertIn('confirmed_unapplied=1', output)
        self.run_script('render-workspace.py', self.root, 'FEAT-001')
        self.assertIn('impact_review', (self.folder / 'decisions.md').read_text())

    def test_legacy_decisions_and_fix_links_remain_compatible(self):
        self.save([{'id': 'D-OLD', 'status': 'approved', 'chosen': 'existing rule', 'custom': 'keep'}])
        self.record()
        self.assertEqual(self.decisions()[0]['custom'], 'keep')
        self.assertFalse(validate_clarifications(self.decisions()[:1], 'check')[0])
