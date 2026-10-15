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


class DelayedContractTests(unittest.TestCase):
    """Real ordering: code commit -> observation -> record commit -> unrelated change."""
    def setUp(self):
        self.helper = test_verification.VerificationTests(methodName='test_generate_defaults_and_idempotence')
        self.helper.setUp()
        self.addCleanup(self.helper.doCleanups)
        self.root, self.folder = self.helper.root, self.helper.folder
        (self.root / 'other.py').write_text('unrelated = 1\n')
        self.helper.doc['allowed_paths'].append('other.py'); self.helper.save()
        self.helper.git('add', '-A')
        self.commit('code and authority')
        self.base = self.helper.git('rev-parse', 'HEAD').strip()
        # No verification plan in the tested commit, as in the reported defect.
        self.helper.git('rm', str((self.folder / 'verification.json').relative_to(self.root)))
        self.commit('code checkpoint before observations')
        self.base = self.helper.git('rev-parse', 'HEAD').strip()
        from verification import sync
        sync(self.root, self.folder)
        doc = load_plan(self.folder); self.item = doc['items'][0]['id']
        stamp, head = context(self.root, self.folder, doc)
        record(self.root, self.folder, self.item, 'passed', stamp, head,
               'Observed abc becomes ABC', 'Original fixture observation')
        self.original = copy.deepcopy(load_plan(self.folder)['items'][0]['history'][-1])
        (self.folder / 'evidence').mkdir()
        (self.folder / 'evidence/origin.txt').write_text('Archived synthetic observation and code identity ' + self.base)
        self.helper.git('add', '.agent-workflow'); self.commit('first saved original contract and observation')
        self.records = self.helper.git('rev-parse', 'HEAD').strip()
        self.make_stale()

    def commit(self, message):
        self.helper.git('-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid', 'commit', '-m', message)

    def make_stale(self):
        decisions = json.loads((self.folder / 'decisions.json').read_text())
        decisions['decisions'].append({'id': 'D-2', 'status': 'approved', 'question': 'unrelated', 'chosen': 'yes', 'approval_ref': 'fixture'})
        (self.folder / 'decisions.json').write_text(json.dumps(decisions))
        (self.root / 'other.py').write_text('unrelated = 2\n')
        self.helper.git('add', '-A'); self.commit('later unrelated change')

    def prepare(self):
        snap = input_snapshot(self.root, self.folder, self.item, self.records)
        review = {'input_digest': snap['input_digest'], 'item_id': self.item, 'status': 'supported',
                  'independent_context': True, 'reviewer': 'synthetic reviewer', 'method': 'archived evidence review',
                  'claim_evidence': 'Original exact uppercase observation',
                  'dependency_evidence': 'Inspected unchanged convert.py, no relationship to other.py',
                  'contract_evidence': 'Full parent and row match, unrelated decision only',
                  'environment_evidence': 'Same synthetic runtime',
                  'counterexample': 'A later contract could invent an observation; exact result is in the record commit',
                  'original_identity': {'revision': self.base, 'worktree_verified': True,
                                        'evidence_refs': ['evidence/origin.txt'], 'explanation': 'Archived synthetic clean tree identity'},
                  'contract_record': {'revision': self.records, 'tested_revision': self.base,
                                      'explanation': 'Original result was saved after execution, code unchanged across interval'},
                  'dependencies': ['convert.py'],
                  'changes': [{'path': p, 'relationship': 'unaffected', 'evidence': 'Inspected unrelated diff'} for p in snap['changed_paths']],
                  'record_changes': [{'path': p, 'relationship': 'unaffected', 'evidence': 'Unrelated decision'} for p in snap['changed_records']]}
        a = self.root / '.agent-workflow/snapshot.json'; b = self.root / '.agent-workflow/review.json'
        a.write_text(json.dumps(snap)); b.write_text(json.dumps(review))
        return snap, review, a, b

    def test_explicit_record_revision_carries_and_keeps_test_identity(self):
        with self.assertRaisesRegex(ValueError, 'historical contract unavailable'):
            input_snapshot(self.root, self.folder, self.item)
        snap, _, a, b = self.prepare()
        entry = apply(self.root, self.folder, a, b)
        self.assertEqual(entry['tested_revision'], self.base)
        self.assertEqual(entry['carry_receipt']['contract_record']['revision'], self.records)
        self.assertEqual(load_plan(self.folder)['items'][0]['history'][0], self.original)
        row = load_plan(self.folder)['items'][0]
        stamp, _ = context(self.root, self.folder, load_plan(self.folder))
        self.assertEqual(state(row, stamp, manual_evidence_stamp(self.root, self.folder, row)), 'retained')
        self.assertNotEqual(snap['contract_record']['revision'], snap['source_revision'])

    def test_cli_explicit_record_revision(self):
        snap, _, _, _ = self.prepare()
        out = self.helper.run_script('evidence_carry.py', 'capture', self.root, 'FEAT-001',
                                     '--item', self.item, '--contract-revision', self.records)
        self.assertEqual(json.loads(out), snap)

    def test_later_business_tree_or_short_revision_rejected(self):
        for rev in (self.records[:8], self.helper.git('rev-parse', 'HEAD').strip()):
            with self.assertRaisesRegex(ValueError, 'full commit|business tree changed'):
                input_snapshot(self.root, self.folder, self.item, rev)

    def test_changed_and_reverted_business_tree_rejected(self):
        self.helper.git('reset', '--hard', self.records)
        (self.root / 'convert.py').write_text('different implementation')
        self.helper.git('add', 'convert.py'); self.commit('temporary business change')
        self.helper.git('checkout', self.base, '--', 'convert.py')
        self.commit('restore implementation')
        self.records = self.helper.git('rev-parse', 'HEAD').strip(); self.make_stale()
        with self.assertRaisesRegex(ValueError, 'business tree changed'):
            self.prepare()

    def test_result_not_in_record_commit_and_changed_claim_rejected(self):
        self.helper.git('reset', '--hard', self.records)
        data = load_plan(self.folder); data['items'][0]['history'] = []
        (self.folder / 'verification.json').write_text(json.dumps(data))
        self.helper.git('add', '.agent-workflow'); self.commit('contract without observation')
        self.records = self.helper.git('rev-parse', 'HEAD').strip()
        data['items'][0]['history'] = [self.original]
        (self.folder / 'verification.json').write_text(json.dumps(data))
        self.make_stale()
        with self.assertRaisesRegex(ValueError, 'exact original result'):
            self.prepare()
        req = json.loads((self.folder / 'spec/requirements.json').read_text())
        req['requirements'][0]['statement'] += ' changed claim'
        (self.folder / 'spec/requirements.json').write_text(json.dumps(req))
        with self.assertRaisesRegex(ValueError, 'parent claim changed'):
            self.prepare()

    def test_unreviewed_binding_or_stale_snapshot_no_writes(self):
        _, review, a, b = self.prepare()
        before = (self.folder / 'verification.json').read_bytes()
        review.pop('contract_record'); b.write_text(json.dumps(review))
        with self.assertRaisesRegex(ValueError, 'chronology'):
            apply(self.root, self.folder, a, b)
        self.assertEqual((self.folder / 'verification.json').read_bytes(), before)
        _, review, a, b = self.prepare()
        p = self.folder / 'evidence/origin.txt'; p.write_text('changed archived identity')
        with self.assertRaisesRegex(ValueError, 'stale'):
            apply(self.root, self.folder, a, b)
        self.assertEqual((self.folder / 'verification.json').read_bytes(), before)

    def test_withdrawal_cannot_be_revived(self):
        data = load_plan(self.folder); stamp, head = context(self.root, self.folder, data)
        record(self.root, self.folder, self.item, 'unavailable', stamp, head, 'Withdrawn observation', 'No coverage')
        with self.assertRaisesRegex(ValueError, 'latest passed'):
            self.prepare()

    def test_existing_test_time_claim_cannot_be_replaced_by_later_contract(self):
        self.helper.git('reset', '--hard', self.records)
        req = json.loads((self.folder / 'spec/requirements.json').read_text())
        req['requirements'][0]['statement'] += ' invented after testing'
        (self.folder / 'spec/requirements.json').write_text(json.dumps(req))
        self.helper.git('add', '.agent-workflow'); self.commit('changed authority after test')
        self.records = self.helper.git('rev-parse', 'HEAD').strip(); self.make_stale()
        with self.assertRaisesRegex(ValueError, 'tested revision differs'):
            self.prepare()

    def test_record_with_later_withdrawal_is_rejected(self):
        self.helper.git('reset', '--hard', self.records)
        data = load_plan(self.folder)
        data['items'][0]['history'].append(dict(self.original, status='unavailable', actual='Withdrawn'))
        (self.folder / 'verification.json').write_text(json.dumps(data))
        self.helper.git('add', '.agent-workflow'); self.commit('withdraw old observation')
        self.records = self.helper.git('rev-parse', 'HEAD').strip()
        data['items'][0]['history'].pop()
        (self.folder / 'verification.json').write_text(json.dumps(data)); self.make_stale()
        with self.assertRaisesRegex(ValueError, 'exact original result'):
            self.prepare()

    def test_forged_snapshot_record_binding_rejected(self):
        snap, _, a, b = self.prepare()
        before = (self.folder / 'verification.json').read_bytes()
        snap['contract_record']['records_digest'] = '0' * 64
        from impact import digest
        snap.pop('input_digest'); snap['input_digest'] = digest(snap)
        a.write_text(json.dumps(snap))
        with self.assertRaisesRegex(ValueError, 'stale'):
            apply(self.root, self.folder, a, b)
        self.assertEqual((self.folder / 'verification.json').read_bytes(), before)


class CarryContinuityTests(unittest.TestCase):
    setUp = DelayedContractTests.setUp
    commit = DelayedContractTests.commit
    make_stale = DelayedContractTests.make_stale
    prepare = DelayedContractTests.prepare

    def seed(self):
        _, _, a, b = self.prepare()
        return apply(self.root, self.folder, a, b)

    def next_change(self, text='unrelated = 3\n'):
        (self.root / 'other.py').write_text(text)
        self.helper.git('add', 'other.py'); self.commit('later independent change')

    def test_dirty_status_is_stale_without_mutating_history_or_head(self):
        self.seed()
        before = (self.folder / 'verification.json').read_bytes()
        head = self.helper.git('rev-parse', 'HEAD')
        (self.root / 'other.py').write_text('uncommitted = 3\n')
        for staged in (False, True):
            if staged:
                self.helper.git('add', 'other.py')
            status = json.loads(self.helper.run_script('verification.py', 'status', self.root, 'FEAT-001', expected=2))
            self.assertEqual(status['items'][0]['status'], 'stale')
            self.assertEqual((self.folder / 'verification.json').read_bytes(), before)
            self.assertEqual(self.helper.git('rev-parse', 'HEAD'), head)
        with self.assertRaisesRegex(ValueError, 'before carry capture'):
            input_snapshot(self.root, self.folder, self.item)

    def test_dirty_tree_allows_actual_gates_and_new_manual_result(self):
        self.seed()
        (self.root / 'other.py').write_text('uncommitted = 3\n')
        self.helper.run_checks()
        doc = load_plan(self.folder)
        self.assertEqual(doc['items'][-1]['history'][-1]['status'], 'passed')
        self.assertEqual(doc['items'][0]['history'][-1]['status'], 'retained')
        stamp, head = context(self.root, self.folder, doc)
        other = doc['items'][1]['id']
        record(self.root, self.folder, other, 'passed', stamp, head, 'New fixture observation', 'Newly executed fixture')
        self.assertEqual(load_plan(self.folder)['items'][1]['history'][-1]['actual'], 'New fixture observation')
        row = load_plan(self.folder)['items'][0]
        self.assertEqual(state(row, stamp, manual_evidence_stamp(self.root, self.folder, row)), 'stale')

    def test_untracked_file_and_dirty_after_freeze_do_not_allow_carry(self):
        self.seed(); self.next_change()
        _, _, a, b = self.prepare()
        before = (self.folder / 'verification.json').read_bytes()
        (self.root / 'untracked.py').write_text('new business file')
        status = json.loads(self.helper.run_script('verification.py', 'status', self.root, 'FEAT-001', expected=2))
        self.assertEqual(status['items'][0]['status'], 'stale')
        with self.assertRaisesRegex(ValueError, 'before carry capture'):
            apply(self.root, self.folder, a, b)
        self.assertEqual((self.folder / 'verification.json').read_bytes(), before)

    def test_three_carries_keep_original_observation_and_record_locator(self):
        self.seed()
        for count in range(3, 6):
            self.next_change('unrelated = ' + str(count) + '\n')
            snap, _, a, b = self.prepare()
            inherited = input_snapshot(self.root, self.folder, self.item)
            self.assertEqual(snap, inherited)
            self.assertEqual(snap['original_observation'], self.original)
            entry = apply(self.root, self.folder, a, b)
            self.assertEqual(entry['tested_revision'], self.base)
            self.assertEqual(entry['carry_receipt']['contract_record']['revision'], self.records)
            self.assertEqual(entry['carry_receipt']['original_observation'], self.original)
            row = load_plan(self.folder)['items'][0]; stamp, _ = context(self.root, self.folder, load_plan(self.folder))
            self.assertEqual(state(row, stamp, manual_evidence_stamp(self.root, self.folder, row)), 'retained')
        self.assertEqual(load_plan(self.folder)['items'][0]['history'][0], self.original)

    def test_old_review_not_reused_for_new_carry(self):
        self.seed(); self.next_change()
        _, _, a, b = self.prepare()
        self.next_change('unrelated = 4\n')
        before = (self.folder / 'verification.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'stale'):
            apply(self.root, self.folder, a, b)
        self.assertEqual((self.folder / 'verification.json').read_bytes(), before)

    def test_repeat_carry_rejects_changed_dependency_and_claim(self):
        self.seed()
        (self.root / 'convert.py').write_text('changed dependency')
        self.helper.git('add', 'convert.py'); self.commit('changed converter')
        _, _, a, b = self.prepare()
        with self.assertRaisesRegex(ValueError, 'dependency changed'):
            apply(self.root, self.folder, a, b)
        req = json.loads((self.folder / 'spec/requirements.json').read_text())
        req['requirements'][0]['statement'] += ' changed'
        (self.folder / 'spec/requirements.json').write_text(json.dumps(req))
        with self.assertRaisesRegex(ValueError, 'parent claim changed'):
            self.prepare()

    def test_failure_after_carry_cannot_be_skipped(self):
        self.seed(); self.next_change()
        doc = load_plan(self.folder); stamp, head = context(self.root, self.folder, doc)
        record(self.root, self.folder, self.item, 'unavailable', stamp, head, 'Withdrawn', 'Coverage insufficient')
        with self.assertRaisesRegex(ValueError, 'latest passed'):
            self.prepare()

    def test_corrupted_original_chain_is_rejected_even_with_new_receipt_hash(self):
        from impact import digest
        self.seed(); self.next_change()
        _, _, a, b = self.prepare(); apply(self.root, self.folder, a, b)
        doc = load_plan(self.folder); entry = doc['items'][0]['history'][-1]
        entry['carry_receipt']['original_observation']['actual'] = 'Invented original observation'
        entry['carry_receipt_digest'] = digest(entry['carry_receipt'])
        (self.folder / 'verification.json').write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, 'original observation chain'):
            load_plan(self.folder)

    def test_0134_receipt_without_new_origin_field_can_continue(self):
        from impact import digest
        self.seed()
        doc = load_plan(self.folder); entry = doc['items'][0]['history'][-1]
        # The 0.13.4 receipt binds its immediate passed predecessor, with no
        # separate original_observation field; do not migrate that old receipt.
        entry['carry_receipt'].pop('original_observation')
        entry['carry_receipt_digest'] = digest(entry['carry_receipt'])
        (self.folder / 'verification.json').write_text(json.dumps(doc))
        original_legacy = copy.deepcopy(entry)
        self.next_change()
        _, _, a, b = self.prepare(); apply(self.root, self.folder, a, b)
        self.assertEqual(load_plan(self.folder)['items'][0]['history'][1], original_legacy)

    def test_repeat_partial_review_stays_stale_without_writes(self):
        self.seed(); self.next_change()
        _, review, a, b = self.prepare()
        before = (self.folder / 'verification.json').read_bytes()
        review['status'] = 'partial'; b.write_text(json.dumps(review))
        with self.assertRaisesRegex(ValueError, 'partial/unknown'):
            apply(self.root, self.folder, a, b)
        self.assertEqual((self.folder / 'verification.json').read_bytes(), before)

    def test_annotation_between_carries_keeps_same_original_observation(self):
        import evidence_annotations as annotations
        p = self.folder / 'evidence/README.md'; p.write_text('Index of original fixture evidence.\n')
        self.seed()
        frozen = annotations.capture(self.root, self.folder, [{'path': 'evidence/README.md', 'role': 'index'}])
        a = self.folder / 'amend-snapshot.json'; a.write_text(json.dumps(frozen))
        p.write_text('Index: original fixture observation, not a fresh execution.\n')
        inputs = annotations.amend_inputs(self.root, self.folder, frozen)
        review = {'input_digest': inputs['input_digest'], 'status': 'supported', 'independent_context': True,
                  'reviewer': 'synthetic annotation reviewer', 'classification_evidence': 'Only index explanation changed',
                  'raw_evidence_unchanged': 'Original identity file unchanged', 'claim_meaning_unchanged': 'Same uppercase claim',
                  'counterexample': 'Raw result edits would invalidate; this patch only changes the index',
                  'items': [{'item_id': x['item_id'], 'status': 'supported', 'evidence': 'Index has no new observation'} for x in inputs['items']]}
        b = self.folder / 'amend-review.json'; b.write_text(json.dumps(review))
        annotations.apply(self.root, self.folder, a, b)
        self.next_change()
        snap, _, a, b = self.prepare()
        self.assertEqual(snap['original_observation'], self.original)
        apply(self.root, self.folder, a, b)
        self.assertEqual(load_plan(self.folder)['items'][0]['history'][-1]['tested_revision'], self.base)

    def test_non_dirty_git_errors_are_not_silenced(self):
        from unittest.mock import patch
        import evidence_carry
        self.seed(); row = load_plan(self.folder)['items'][0]
        with patch.object(evidence_carry, 'project_files', side_effect=ValueError('Git unavailable')):
            with self.assertRaisesRegex(ValueError, 'Git unavailable'):
                manual_evidence_stamp(self.root, self.folder, row)
