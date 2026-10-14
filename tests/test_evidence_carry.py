import copy
import json
import unittest
from pathlib import Path
import test_verification
from evidence_carry import input_snapshot, apply
from verification import context, record, load_plan, manual_evidence_stamp, state


class EvidenceCarryTests(unittest.TestCase):
    def setUp(self):
        self.helper = test_verification.VerificationTests(methodName='test_generate_defaults_and_idempotence')
        self.helper.setUp()
        self.addCleanup(self.helper.doCleanups)
        self.root, self.folder = self.helper.root, self.helper.folder
        (self.root / 'other.py').write_text('unrelated = 1\n')
        self.helper.doc['allowed_paths'].append('other.py')
        self.helper.save()
        self.helper.git('add', '-A')
        self.helper.git('-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'baseline with contract')
        doc = load_plan(self.folder)
        self.item = doc['items'][0]['id']
        stamp, head = context(self.root, self.folder, doc)
        record(self.root, self.folder, self.item, 'passed', stamp, head, 'Observed abc becomes ABC', 'Fixture observation at original commit')
        self.original = copy.deepcopy(load_plan(self.folder)['items'][0]['history'][-1])
        (self.folder / 'evidence').mkdir()
        (self.folder / 'evidence/origin.txt').write_text('Synthetic executed fixture was clean at ' + head)
        decisions = json.loads((self.folder / 'decisions.json').read_text())
        decisions['decisions'].append({'id': 'D-2', 'status': 'approved', 'question': 'unrelated format', 'chosen': 'yes', 'approval_ref': 'fixture owner'})
        (self.folder / 'decisions.json').write_text(json.dumps(decisions))
        (self.root / 'other.py').write_text('unrelated = 2\n')
        self.helper.git('add', '-A')
        self.helper.git('-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'unrelated local change')

    def prepare(self):
        snap = input_snapshot(self.root, self.folder, self.item)
        review = {'input_digest': snap['input_digest'], 'item_id': self.item, 'status': 'supported',
                  'original_identity': {'revision': snap['source_revision'], 'worktree_verified': True,
                                        'evidence_refs': ['evidence/origin.txt'], 'explanation': 'Original fixture log confirms clean tested tree at source commit'},
                  'independent_context': True, 'reviewer': 'fixture fresh reviewer', 'method': 'source and original evidence review',
                  'claim_evidence': 'Original observation covers exact uppercase input/output',
                  'dependency_evidence': 'convert.py owns this pure conversion; other.py has no import or caller relationship',
                  'contract_evidence': 'D-2 describes unrelated formatting; parent and row unchanged',
                  'environment_evidence': 'No external input or runtime setup dependency; same fixture environment',
                  'counterexample': 'Shared converter could invalidate observation; actual changed diff is confined to unrelated file',
                  'dependencies': ['convert.py'],
                  'changes': [{'path': p, 'relationship': 'unaffected', 'evidence': 'Inspected unrelated assignment, no callers'} for p in snap['changed_paths']],
                  'record_changes': [{'path': p, 'relationship': 'unaffected', 'evidence': 'Compared before/current, no effect on full uppercase claim'} for p in snap['changed_records']]}
        snapshot, result = self.root / '.agent-workflow/snapshot.json', self.root / '.agent-workflow/review.json'
        snapshot.write_text(json.dumps(snap)); result.write_text(json.dumps(review))
        return snap, review, snapshot, result

    def test_old_unscoped_requirement_can_carry_without_rewriting_original(self):
        snap, _, snapshot, review = self.prepare()
        entry = apply(self.root, self.folder, snapshot, review)
        row = load_plan(self.folder)['items'][0]
        self.assertEqual(row['history'][0], self.original)
        self.assertEqual(entry['status'], 'retained')
        self.assertEqual(entry['tested_revision'], self.original['tested_revision'])
        self.assertNotEqual(entry['tested_revision'], entry['reviewed_revision'])
        stamp, _ = context(self.root, self.folder, load_plan(self.folder))
        self.assertEqual(state(row, stamp, manual_evidence_stamp(self.root, self.folder, row)), 'retained')
        # Workflow-only commits do not pretend to change business behavior.
        self.helper.git('add', '.agent-workflow'); self.helper.git('-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'receipt')
        self.assertEqual(state(row, stamp, manual_evidence_stamp(self.root, self.folder, row)), 'retained')

    def test_relevant_dependency_and_unknown_change_rejected_no_writes(self):
        _, review, snapshot, output = self.prepare()
        before = (self.folder / 'verification.json').read_bytes()
        review['dependencies'].append('other.py')
        output.write_text(json.dumps(review))
        with self.assertRaisesRegex(ValueError, 'dependency changed'):
            apply(self.root, self.folder, snapshot, output)
        review['dependencies'] = ['convert.py']; review['changes'][0]['relationship'] = 'unknown'
        output.write_text(json.dumps(review))
        with self.assertRaisesRegex(ValueError, 'affected/unknown'):
            apply(self.root, self.folder, snapshot, output)
        self.assertEqual(before, (self.folder / 'verification.json').read_bytes())

    def test_partial_self_context_wrong_identity_or_omitted_record_rejected(self):
        _, review, snapshot, output = self.prepare()
        for patch in ({'status': 'partial'}, {'independent_context': False}, {'input_digest': 'old'}, {'record_changes': []}):
            bad = dict(review, **patch); output.write_text(json.dumps(bad))
            with self.assertRaises(ValueError):
                apply(self.root, self.folder, snapshot, output)

    def test_source_or_code_changes_after_capture_reject(self):
        _, _, snapshot, output = self.prepare()
        (self.root / 'convert.py').write_text('changed converter')
        with self.assertRaises(ValueError):
            apply(self.root, self.folder, snapshot, output)

    def test_full_parent_change_and_latest_failure_do_not_revive_pass(self):
        req = json.loads((self.folder / 'spec/requirements.json').read_text())
        req['requirements'][0]['statement'] += ' and lowercase'
        (self.folder / 'spec/requirements.json').write_text(json.dumps(req))
        with self.assertRaisesRegex(ValueError, 'parent claim changed'):
            input_snapshot(self.root, self.folder, self.item)
        req['requirements'][0]['statement'] = self.helper.req['requirements'][0]['statement']
        (self.folder / 'spec/requirements.json').write_text(json.dumps(req))
        doc = load_plan(self.folder); stamp, head = context(self.root, self.folder, doc)
        record(self.root, self.folder, self.item, 'failed', stamp, head, 'Observed wrong conversion', 'failure evidence')
        with self.assertRaisesRegex(ValueError, 'latest passed'):
            input_snapshot(self.root, self.folder, self.item)

    def test_receipt_tampering_and_later_commit_stale(self):
        _, _, snapshot, output = self.prepare(); apply(self.root, self.folder, snapshot, output)
        doc = load_plan(self.folder); row = doc['items'][0]
        (self.root / 'other.py').write_text('unrelated = 3\n')
        self.helper.git('add', 'other.py'); self.helper.git('-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'later')
        stamp, _ = context(self.root, self.folder, doc)
        self.assertEqual(state(row, stamp, manual_evidence_stamp(self.root, self.folder, row)), 'stale')
        row['history'][-1]['carry_receipt']['review']['claim_evidence'] = 'tampered'
        (self.folder / 'verification.json').write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, 'receipt digest'):
            load_plan(self.folder)

    def test_automatic_gate_not_eligible(self):
        doc = load_plan(self.folder); gate = doc['items'][-1]
        self.assertEqual(gate['mode'], 'automatic')
        with self.assertRaisesRegex(ValueError, 'manual'):
            input_snapshot(self.root, self.folder, gate['id'])

    def test_cli_capture_and_apply(self):
        snap, _, snapshot, output = self.prepare()
        actual = self.helper.run_script('evidence_carry.py', 'capture', self.root, 'FEAT-001', '--item', self.item)
        self.assertEqual(json.loads(actual)['input_digest'], snap['input_digest'])
        text = self.helper.run_script('evidence_carry.py', 'apply', self.root, 'FEAT-001', '--snapshot', snapshot, '--review', output)
        self.assertIn('EVIDENCE_CARRIED', text)

    def test_ignored_original_source_change_expires_capture_and_carried_result(self):
        _, _, snapshot, output = self.prepare()
        apply(self.root, self.folder, snapshot, output)
        doc = load_plan(self.folder); row = doc['items'][0]
        source = next((self.folder / 'sources').iterdir())
        source.write_bytes(source.read_bytes() + b' changed source')
        stamp, _ = context(self.root, self.folder, doc)
        self.assertEqual(state(row, stamp, manual_evidence_stamp(self.root, self.folder, row)), 'stale')

    def test_unknown_metadata_and_same_context_review_reject_without_writes(self):
        _, review, snapshot, output = self.prepare()
        before = (self.folder / 'verification.json').read_bytes()
        review['record_changes'][0]['relationship'] = 'unknown'
        output.write_text(json.dumps(review))
        with self.assertRaisesRegex(ValueError, 'unknown contract'):
            apply(self.root, self.folder, snapshot, output)
        self.assertEqual((self.folder / 'verification.json').read_bytes(), before)

    def test_incomplete_receipt_cannot_be_accepted_even_with_recomputed_hash(self):
        from impact import digest
        _, _, snapshot, output = self.prepare(); apply(self.root, self.folder, snapshot, output)
        doc = load_plan(self.folder); entry = doc['items'][0]['history'][-1]
        entry['carry_receipt']['review'].pop('counterexample')
        entry['carry_receipt_digest'] = digest(entry['carry_receipt'])
        (self.folder / 'verification.json').write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, 'counterexample'):
            load_plan(self.folder)

    def test_traceability_change_stales_carry_without_code_change(self):
        _, _, snapshot, output = self.prepare(); apply(self.root, self.folder, snapshot, output)
        doc = load_plan(self.folder); row = doc['items'][0]
        p = self.folder / 'traceability.json'; data = json.loads(p.read_text()); data['note'] = 'changed interpretation'
        p.write_text(json.dumps(data)); stamp, _ = context(self.root, self.folder, doc)
        self.assertEqual(state(row, stamp, manual_evidence_stamp(self.root, self.folder, row)), 'stale')

    def test_concurrent_other_row_failure_is_not_overwritten(self):
        from unittest.mock import patch
        import evidence_carry
        _, _, snapshot, output = self.prepare()
        original_guard = evidence_carry.input_snapshot_from_previous
        def concurrent(root, folder, item_id):
            doc = load_plan(folder); stamp, head = context(root, folder, doc)
            other = doc['items'][1]['id']
            changed = load_plan(folder)
            changed['items'][1]['history'].append(dict(self.original, status='failed', actual='actual failure'))
            # Simulate an editor not participating in the helper lock.
            (folder / 'verification.json').write_text(json.dumps(changed))
            return original_guard(root, folder, item_id)
        with patch.object(evidence_carry, 'input_snapshot_from_previous', concurrent):
            with self.assertRaisesRegex(ValueError, 'plan/results changed'):
                apply(self.root, self.folder, snapshot, output)
        self.assertEqual(load_plan(self.folder)['items'][1]['history'][-1]['status'], 'failed')
        self.assertEqual(len(load_plan(self.folder)['items'][0]['history']), 1)

    def test_unbound_original_observation_or_missing_artifact_is_rejected(self):
        _, review, snapshot, output = self.prepare()
        before = (self.folder / 'verification.json').read_bytes()
        review['original_identity']['worktree_verified'] = False
        output.write_text(json.dumps(review))
        with self.assertRaisesRegex(ValueError, 'proved code/worktree'):
            apply(self.root, self.folder, snapshot, output)
        review['original_identity']['worktree_verified'] = True
        review['original_identity']['evidence_refs'] = ['evidence/not-found.txt']
        output.write_text(json.dumps(review))
        with self.assertRaisesRegex(ValueError, 'accessible archived'):
            apply(self.root, self.folder, snapshot, output)
        self.assertEqual((self.folder / 'verification.json').read_bytes(), before)

    def test_nested_helper_mutation_refuses_busy_lock(self):
        from verification import plan_mutation
        @plan_mutation
        def attempt(root, folder):
            doc = load_plan(folder); stamp, head = context(root, folder, doc)
            record(root, folder, self.item, 'passed', stamp, head, 'new observation', 'new evidence')
        with self.assertRaisesRegex(ValueError, 'plan busy'):
            attempt(self.root, self.folder)
