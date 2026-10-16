import copy
import json
import unittest
from unittest.mock import patch

import test_verification
import verification as v
import evidence_adoption as a
from impact import digest
from evidence_carry import parent


class EvidenceAdoptionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_verification.VerificationTests()
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.root, self.folder = self.fixture.root, self.fixture.folder
        (self.root / '.agent-workflow/.gitignore').write_text('/scratch/\n')
        self.scratch = self.root / '.agent-workflow/scratch/adoption'
        self.scratch.mkdir(parents=True)
        self.snapshot, self.review_path = self.scratch / 'input.json', self.scratch / 'review.json'
        doc = v.load_plan(self.folder)
        stamp, head = v.context(self.root, self.folder, doc)
        self.old_id = doc['items'][0]['id']
        v.record(self.root, self.folder, self.old_id, 'passed', stamp, head,
                 'Observed abc becomes ABC in synthetic fixture', 'Synthetic original observation')
        old = v.load_plan(self.folder)['items'][0]
        self.observation = copy.deepcopy(old['history'][-1])
        evidence = self.folder / 'evidence'; evidence.mkdir()
        self.origin = evidence / 'origin.txt'
        self.origin.write_text('Synthetic original clean tree/package log; abc -> ABC, not new execution')
        self.contract_path = evidence / 'original-contract.json'
        self.contract_path.write_text(json.dumps({
            'feature_id': self.folder.name, 'row_contract': a.contract(old),
            'result_hash': digest(self.observation), 'tested_revision': head, 'observed_at': self.observation['at'],
            'parent_claim': parent(self.fixture.req, self.fixture.doc, old),
            'provenance_refs': [self.rel(self.origin)]}))
        # Workflow records are deliberately never committed in this fixture.
        req = v.read(self.folder / 'spec/requirements.json')
        req['requirements'][0]['acceptance_criteria'][0] = 'Supplied lowercase abc is returned as ABC'
        v.save(self.folder / 'spec/requirements.json', req)
        v.save(self.folder / 'decisions.json', {'feature_id': self.folder.name, 'decisions': [
            {'id': 'D-CORRECT', 'status': 'approved', 'approval_ref': 'Synthetic owner correction',
             'question': 'Correct interpretation, preserve uppercase behavior'}]})
        v.sync(self.root, self.folder)
        self.item = v.load_plan(self.folder)['items'][0]['id']
        self.requests = [{'item_id': self.item, 'source': {'collection': 'retired', 'item_id': self.old_id, 'history_index': 0},
                          'contract_ref': self.rel(self.contract_path), 'decision_id': 'D-CORRECT',
                          'evidence_refs': [self.rel(self.origin)]}]

    def rel(self, path): return path.relative_to(self.root).as_posix()

    def prepare(self):
        frozen = a.capture(self.root, self.folder, self.requests)
        review = {'input_digest': frozen['input_digest'], 'status': 'supported', 'independent_context': True,
                  'reviewer': 'Synthetic protocol fixture; not a real independent reviewer', 'rows': []}
        for row in frozen['rows']:
            review['rows'].append({'item_id': row['item_id'], 'status': 'supported',
                'change_kind': 'interpretation_correction', 'coverage_expanded': False, 'contradictions': [],
                'claim_evidence': 'abc -> ABC original observation supports corrected wording completely',
                'contract_provenance': 'Synthetic archived contract traced to original workflow state',
                'decision_scope': 'Owner corrects reading; no new behavior',
                'source_status_explanation': 'Original passed observation, no withdrawal',
                'history_review': 'Entire source/target histories inspected, no contradictory observation',
                'environment_evidence': 'Same pure synthetic converter and environment',
                'counterexample': 'A lowercase-output demand would require new evidence',
                'original_identity': {'revision': self.observation['tested_revision'], 'worktree_verified': True,
                                      'explanation': 'Fixture origin log, clean original tree', 'evidence_refs': [self.rel(self.origin)]},
                'dependencies': ['convert.py'],
                'changes': [{'path': p, 'relationship': 'unaffected', 'evidence': 'Inspected independent change'} for p in row['changed_paths']]})
        v.save(self.snapshot, frozen); v.save(self.review_path, review)
        return frozen, review

    def adopt(self):
        self.prepare(); return a.apply(self.root, self.folder, self.snapshot, self.review_path)

    def state(self):
        doc = v.load_plan(self.folder); row = next(r for r in doc['items'] if r['id'] == self.item)
        stamp, _ = v.context(self.root, self.folder, doc)
        return v.state(row, stamp, v.manual_evidence_stamp(self.root, self.folder, row))

    def test_retired_uncommitted_observation_adopted_without_reexecution(self):
        before = v.load_plan(self.folder)
        out = self.adopt(); doc = v.load_plan(self.folder)
        self.assertEqual(out, {'adopted': [self.item], 'new_execution': False})
        self.assertEqual(doc['schema_version'], 3)
        self.assertEqual(doc['retired'], before['retired'])
        self.assertEqual(doc['items'][1:], before['items'][1:])
        entry = doc['items'][0]['history'][-1]
        self.assertEqual(entry['tested_revision'], self.observation['tested_revision'])
        self.assertEqual(entry['observed_at'], self.observation['at'])
        self.assertEqual(self.state(), 'retained')
        self.assertNotIn(self.observation['actual'], json.dumps(doc['adoption_reviews']))
        self.assertIn('Reviewed interpretation adoption', (self.folder / 'verification.md').read_text())
        self.fixture.run_script('verification.py', 'status', self.root, self.folder.name, expected=2)
        from claim_review import identity
        claims = identity(self.root, self.folder)['claims']
        self.assertEqual(claims[0]['evidence_adoptions'][0]['observed_at'], self.observation['at'])

    def test_partial_unknown_self_review_expansion_conflict_rejected(self):
        _, review = self.prepare(); before = (self.folder / 'verification.json').read_bytes()
        for changes in ({'status': 'partial'}, {'status': 'unknown'}, {'independent_context': False}):
            bad = copy.deepcopy(review); bad.update(changes); v.save(self.review_path, bad)
            with self.assertRaises(ValueError): a.apply(self.root, self.folder, self.snapshot, self.review_path)
        for changes in ({'coverage_expanded': True}, {'contradictions': ['Later failed']},
                        {'change_kind': 'new_behavior'}, {'contract_provenance': ''}, {'dependencies': []}):
            bad = copy.deepcopy(review); bad['rows'][0].update(changes); v.save(self.review_path, bad)
            with self.assertRaises(ValueError): a.apply(self.root, self.folder, self.snapshot, self.review_path)
        self.assertEqual((self.folder / 'verification.json').read_bytes(), before)

    def test_failed_waived_derived_or_skipped_withdrawal_source_rejected(self):
        original = v.load_plan(self.folder)
        for status in ('failed', 'waived', 'retained'):
            doc = copy.deepcopy(original); doc['retired'][0]['history'][0]['status'] = status
            v.save(self.folder / 'verification.json', doc)
            with self.assertRaises(ValueError): a.capture(self.root, self.folder, self.requests)
        doc = copy.deepcopy(original)
        doc['retired'][0]['history'].append(dict(self.observation, status='unavailable', actual='Later coverage withdrawal'))
        v.save(self.folder / 'verification.json', doc)
        with self.assertRaisesRegex(ValueError, 'latest'): a.capture(self.root, self.folder, self.requests)

    def test_unavailable_expected_value_correction_requires_explicit_supported_review(self):
        doc = v.load_plan(self.folder); observation = doc['retired'][0]['history'][0]
        observation.update(status='unavailable', actual='ABC observed, old expectation mistakenly required lowercase')
        v.save(self.folder / 'verification.json', doc)
        archive = v.read(self.contract_path); archive['result_hash'] = digest(observation); v.save(self.contract_path, archive)
        self.adopt(); self.assertEqual(self.state(), 'retained')
        self.assertEqual(v.load_plan(self.folder)['retired'][0]['history'][0]['status'], 'unavailable')

    def test_pending_decision_missing_provenance_wrong_identity_rejected(self):
        original = v.read(self.folder / 'decisions.json')
        doc = copy.deepcopy(original); doc['decisions'][0]['status'] = 'pending'; v.save(self.folder / 'decisions.json', doc)
        with self.assertRaises(ValueError): a.capture(self.root, self.folder, self.requests)
        v.save(self.folder / 'decisions.json', original)
        archive = v.read(self.contract_path); archive['provenance_refs'] = []; v.save(self.contract_path, archive)
        with self.assertRaisesRegex(ValueError, 'provenance'): a.capture(self.root, self.folder, self.requests)

    def test_archive_or_config_or_plan_change_after_freeze_rejected(self):
        self.prepare(); self.origin.write_text('Changed source')
        with self.assertRaisesRegex(ValueError, 'stale'): a.apply(self.root, self.folder, self.snapshot, self.review_path)
        self.prepare(); config_path = self.fixture.base / 'quality-gates.json'
        config = v.read(config_path); config['selection_reason'] = 'Changed after freeze'; v.save(config_path, config)
        with self.assertRaisesRegex(ValueError, 'stale'): a.apply(self.root, self.folder, self.snapshot, self.review_path)
        self.prepare(); doc = v.load_plan(self.folder); doc['items'][1]['coverage'] = 'New input'; v.save(self.folder / 'verification.json', doc)
        with self.assertRaisesRegex(ValueError, 'stale'): a.apply(self.root, self.folder, self.snapshot, self.review_path)

    def test_wrong_original_identity_and_changed_dependency_rejected(self):
        _, review = self.prepare(); review['rows'][0]['original_identity']['worktree_verified'] = False
        v.save(self.review_path, review)
        with self.assertRaisesRegex(ValueError, 'identity'): a.apply(self.root, self.folder, self.snapshot, self.review_path)
        (self.root / 'convert.py').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'business'): a.capture(self.root, self.folder, self.requests)
        self.fixture.git('add', 'convert.py')
        self.fixture.git('-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'changed dependency')
        self.prepare()
        with self.assertRaisesRegex(ValueError, 'dependency'): a.apply(self.root, self.folder, self.snapshot, self.review_path)

    def test_support_change_stales_and_source_tamper_rejected(self):
        self.adopt(); self.origin.write_text('New source content'); self.assertEqual(self.state(), 'stale')
        doc = v.load_plan(self.folder); doc['retired'][0]['history'][0]['actual'] = 'Invented'
        v.save(self.folder / 'verification.json', doc)
        with self.assertRaisesRegex(ValueError, 'observation'): v.load_plan(self.folder)

    def test_sync_preserves_ledger_and_corrections_do_not_downgrade_schema(self):
        self.adopt(); before = v.load_plan(self.folder)
        v.sync(self.root, self.folder); self.assertEqual(v.load_plan(self.folder), before)
        from result_corrections import apply, capture
        changes = [{'item_id': self.item, 'history_index': 0, 'field': 'evidence',
                    'replacement': 'Precise archived fixture provenance', 'reason': 'Clarify archive path',
                    'support_refs': [self.rel(self.origin)]}]
        frozen = capture(self.root, self.folder, changes)
        review = {'input_digest': frozen['input_digest'], 'status': 'supported', 'independent_context': True,
                  'reviewer': 'Synthetic fixture', 'scope_evidence': 'Path only', 'coverage_unchanged': 'No behavior',
                  'identity_unchanged': 'Same source', 'counterexample': 'No expanded claim',
                  'corrections': [{'item_id': self.item, 'history_index': 0, 'field': 'evidence',
                                   'status': 'metadata_only', 'evidence': 'Inspected fixture archive'}]}
        v.save(self.snapshot, frozen); v.save(self.review_path, review)
        apply(self.root, self.folder, self.snapshot, self.review_path)
        self.assertEqual(v.load_plan(self.folder)['schema_version'], 3)
        self.assertEqual(self.state(), 'retained')

    def test_batch_duplicate_and_wrong_slot_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            a.capture(self.root, self.folder, self.requests * 2)
        self.requests[0]['item_id'] = v.load_plan(self.folder)['items'][1]['id']
        with self.assertRaisesRegex(ValueError, 'same requirement'): a.capture(self.root, self.folder, self.requests)

    def test_batch_adopts_retired_and_active_sources_without_staling_gate_or_each_other(self):
        doc = v.load_plan(self.folder); stamp, head = v.context(self.root, self.folder, doc)
        active = doc['items'][1]
        v.record(self.root, self.folder, active['id'], 'passed', stamp, head, 'Synthetic preserved behavior observed', 'Synthetic execution')
        doc = v.load_plan(self.folder); active = doc['items'][1]; origin = active['history'][-1]
        path = self.folder / 'evidence/active-contract.json'
        path.write_text(json.dumps({'feature_id': self.folder.name, 'row_contract': a.contract(active),
            'result_hash': digest(origin), 'tested_revision': head, 'observed_at': origin['at'],
            'parent_claim': parent(v.read(self.folder / 'spec/requirements.json'), self.fixture.doc, active),
            'provenance_refs': [self.rel(self.origin)]}))
        decisions = v.read(self.folder / 'decisions.json'); decisions['decisions'][0]['note'] = 'Finalized interpretation'
        v.save(self.folder / 'decisions.json', decisions)
        self.requests.append({'item_id': active['id'], 'source': {'collection': 'items', 'item_id': active['id'], 'history_index': 0},
                              'contract_ref': self.rel(path), 'decision_id': 'D-CORRECT', 'evidence_refs': [self.rel(self.origin)]})
        # A current automatic result must survive adoption: no selection/contract changes hereafter.
        doc = v.load_plan(self.folder); stamp, head = v.context(self.root, self.folder, doc)
        doc['items'][-1]['history'].append(v.result('passed', stamp, head, 'Synthetic gate executed', 'Synthetic gate log', 'automatic'))
        v.save(self.folder / 'verification.json', doc); gate_before = copy.deepcopy(doc['items'][-1])
        self.prepare(); out = a.apply(self.root, self.folder, self.snapshot, self.review_path)
        after = v.load_plan(self.folder)
        self.assertEqual(len(out['adopted']), 2); self.assertEqual(len(after['adoption_reviews']), 1)
        self.assertEqual(after['items'][-1], gate_before)
        current, _ = v.context(self.root, self.folder, after)
        self.assertEqual(v.state(after['items'][-1], current), 'passed')
        for row in after['items'][:2]:
            self.assertEqual(v.state(row, current, v.manual_evidence_stamp(self.root, self.folder, row)), 'retained')

    def test_cli_capture_apply_and_replay_refusal_in_isolated_project(self):
        self.prepare(); request_path = self.scratch / 'requests.json'; v.save(request_path, self.requests)
        self.fixture.run_script('evidence_adoption.py', 'capture', self.root, self.folder.name,
                                '--requests', request_path, '--output', self.snapshot)
        out = self.fixture.run_script('evidence_adoption.py', 'apply', self.root, self.folder.name,
                                      '--snapshot', self.snapshot, '--review', self.review_path)
        self.assertEqual(json.loads(out)['new_execution'], False)
        self.fixture.run_script('evidence_adoption.py', 'apply', self.root, self.folder.name,
                                '--snapshot', self.snapshot, '--review', self.review_path, expected=2)

    def test_cli_project_path_alias_is_normalized_before_output_guard(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as name:
            alias = Path(name) / 'project-alias'; alias.symlink_to(self.root, target_is_directory=True)
            request_path = self.scratch / 'requests.json'; v.save(request_path, self.requests)
            output = alias / self.snapshot.relative_to(self.root)
            self.fixture.run_script('evidence_adoption.py', 'capture', alias, self.folder.name,
                                    '--requests', request_path, '--output', output)
            self.assertEqual(v.read(self.snapshot)['feature_id'], self.folder.name)

    def test_later_source_withdrawal_stales_adopted_result(self):
        self.adopt(); doc = v.load_plan(self.folder)
        doc['retired'][0]['history'].append(dict(self.observation, status='unavailable', actual='New conflicting evidence'))
        v.save(self.folder / 'verification.json', doc)
        self.assertEqual(self.state(), 'stale')

    def test_recovered_contract_in_receipt_preserves_other_current_retained_evidence(self):
        doc = v.load_plan(self.folder); stamp, head = v.context(self.root, self.folder, doc)
        other = doc['items'][1]
        v.record(self.root, self.folder, other['id'], 'passed', stamp, head, 'Other synthetic behavior observed', 'Original log')
        other = v.load_plan(self.folder)['items'][1]; observation = other['history'][-1]
        decisions = v.read(self.folder / 'decisions.json'); decisions['decisions'][0]['note'] = 'Final authority before adoption'
        v.save(self.folder / 'decisions.json', decisions)
        self.adopt(); self.assertEqual(self.state(), 'retained')
        before_files = a.source_identity(self.root, self.folder)
        path = self.root / '.agent-workflow/scratch' / self.folder.name / 'recovered-contract.json'
        path.parent.mkdir(parents=True)
        v.save(path, {'feature_id': self.folder.name, 'row_contract': a.contract(other),
            'result_hash': digest(observation), 'tested_revision': head, 'observed_at': observation['at'],
            'parent_claim': parent(v.read(self.folder / 'spec/requirements.json'), self.fixture.doc, other),
            'provenance_refs': [self.rel(self.origin)]})
        self.requests = [{'item_id': other['id'], 'source': {'collection': 'items', 'item_id': other['id'], 'history_index': 0},
                          'contract_ref': self.rel(path), 'decision_id': 'D-CORRECT', 'evidence_refs': [self.rel(self.origin)]}]
        self.adopt(); path.unlink()
        after = v.load_plan(self.folder); stamp, _ = v.context(self.root, self.folder, after)
        self.assertEqual(a.source_identity(self.root, self.folder), before_files)
        for row in after['items'][:2]:
            self.assertEqual(v.state(row, stamp, v.manual_evidence_stamp(self.root, self.folder, row)), 'retained')

    def test_tampered_receipt_identity_and_old_schema_rejected(self):
        self.adopt(); original = v.load_plan(self.folder)
        for patch_fields in ({'tested_revision': '0' * 40}, {'observed_at': 'Invented time'}, {'adoption_receipt': '0' * 64}):
            doc = copy.deepcopy(original); doc['items'][0]['history'][-1].update(patch_fields)
            v.save(self.folder / 'verification.json', doc)
            with self.assertRaises(ValueError): v.load_plan(self.folder)
        doc = copy.deepcopy(original); doc['schema_version'] = 2; v.save(self.folder / 'verification.json', doc)
        with self.assertRaises(ValueError): v.load_plan(self.folder)

    def test_save_time_change_rejected_no_plan_write(self):
        self.prepare(); before = (self.folder / 'verification.json').read_bytes()
        real = a.capture; count = [0]
        def changing(*args):
            count[0] += 1
            if count[0] == 2: self.origin.write_text('Concurrent source edit')
            return real(*args)
        with patch.object(a, 'capture', side_effect=changing):
            with self.assertRaisesRegex(ValueError, 'before save'):
                a.apply(self.root, self.folder, self.snapshot, self.review_path)
        self.assertEqual((self.folder / 'verification.json').read_bytes(), before)


if __name__ == '__main__': unittest.main()
