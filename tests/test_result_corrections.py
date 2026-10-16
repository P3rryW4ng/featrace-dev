import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
import test_verification
from impact import digest
import verification as v
from result_corrections import capture, apply, links


class ResultCorrectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_verification.VerificationTests()
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.root, self.folder = self.fixture.root, self.fixture.folder
        plan = v.load_plan(self.folder); self.item = plan['items'][0]['id']
        stamp, head = v.context(self.root, self.folder, plan)
        v.record(self.root, self.folder, self.item, 'passed', stamp, head,
                 'Fixture conversion observed', 'Text cited a temporary run artifact')
        (self.folder / 'evidence').mkdir()
        self.support = self.folder / 'evidence/run.txt'
        self.support.write_text('Archived synthetic executed conversion: abc becomes ABC\n')
        self.changes = [{'item_id': self.item, 'history_index': 0, 'field': 'evidence',
                         'replacement': 'Archived synthetic result at evidence/run.txt; no new execution',
                         'reason': 'Correct navigation to the existing archived result',
                         'support_refs': [self.support.relative_to(self.root).as_posix()]}]
        self.scratch = self.root / '.agent-workflow/scratch/corrections'; self.scratch.mkdir(parents=True)
        (self.root / '.agent-workflow/.gitignore').write_text('/scratch/\n')
        self.snapshot = self.scratch / 'snapshot.json'; self.review = self.scratch / 'review.json'

    def prepare(self):
        frozen = capture(self.root, self.folder, self.changes)
        review = {'input_digest': frozen['input_digest'], 'status': 'supported', 'independent_context': True,
                  'reviewer': 'synthetic new-context fixture; not a real Agent',
                  'scope_evidence': 'Archive path names existing conversion output, with original hash preserved',
                  'coverage_unchanged': 'Exact abc to ABC claim unchanged; no new observation is asserted',
                  'identity_unchanged': 'Original fixture result and tested revision kept',
                  'counterexample': 'A new observed input or broader promise would require ordinary Verify',
                  'corrections': [{k: c[k] for k in ('item_id', 'history_index', 'field')} | {
                      'status': 'metadata_only', 'evidence': 'Original archive and replacement inspected'} for c in self.changes]}
        self.snapshot.write_text(json.dumps(frozen)); self.review.write_text(json.dumps(review))
        return frozen, review

    def do_apply(self):
        self.prepare(); return apply(self.root, self.folder, self.snapshot, self.review)

    def effective(self):
        doc = v.load_plan(self.folder); stamp, _ = v.context(self.root, self.folder, doc); row = doc['items'][0]
        return v.state(row, stamp, v.manual_evidence_stamp(self.root, self.folder, row))

    def test_pass_history_identity_freshness_unchanged_and_notes_visible(self):
        before = v.load_plan(self.folder); state = self.effective()
        event = self.do_apply(); doc = v.load_plan(self.folder)
        self.assertEqual(doc['items'], before['items']); self.assertEqual(doc['retired'], before['retired'])
        self.assertEqual(doc['schema_version'], 2); self.assertEqual(self.effective(), state)
        note = links(self.root, doc, doc['items'][0])[0]
        self.assertTrue(note['support_current']); self.assertEqual(note['target'], 'latest_record')
        self.assertEqual(note['tested_revision'], before['items'][0]['history'][0]['tested_revision'])
        self.assertNotIn('Text cited a temporary run artifact', json.dumps(event))
        self.assertIn('Reviewed description corrections', (self.folder / 'verification.md').read_text())
        out = json.loads(self.fixture.run_script('verification.py', 'status', self.root, 'FEAT-001', expected=2))
        self.assertEqual(out['items'][0]['result_corrections'][0]['replacement'], note['replacement'])

    def test_stale_pass_stays_stale_with_pending_decision(self):
        d = json.loads((self.folder / 'decisions.json').read_text())
        d['decisions'].append({'id': 'D-PENDING', 'status': 'pending', 'question': 'Unrelated product choice'})
        (self.folder / 'decisions.json').write_text(json.dumps(d))
        self.assertEqual(self.effective(), 'stale'); self.do_apply()
        self.assertEqual(self.effective(), 'stale')

    def test_historical_correction_does_not_revive_later_withdrawal(self):
        doc = v.load_plan(self.folder); stamp, head = v.context(self.root, self.folder, doc)
        v.record(self.root, self.folder, self.item, 'unavailable', stamp, head, 'Later coverage withdrawal', 'Actual gap')
        self.do_apply(); self.assertEqual(self.effective(), 'unavailable')
        doc = v.load_plan(self.folder)
        self.assertEqual(links(self.root, doc, doc['items'][0])[0]['target'], 'historical_record')

    def test_partial_review_and_forbidden_field_refused_without_writes(self):
        _, review = self.prepare(); before = (self.folder / 'verification.json').read_bytes()
        review['status'] = 'partial'; self.review.write_text(json.dumps(review))
        with self.assertRaisesRegex(ValueError, 'partial/unknown'):
            apply(self.root, self.folder, self.snapshot, self.review)
        self.assertEqual((self.folder / 'verification.json').read_bytes(), before)
        self.changes[0]['field'] = 'tested_revision'
        with self.assertRaises(ValueError): capture(self.root, self.folder, self.changes)

    def test_source_and_plan_changes_after_freeze_refused(self):
        self.prepare(); before = (self.folder / 'verification.json').read_bytes()
        self.support.write_text('Changed original archive')
        with self.assertRaisesRegex(ValueError, 'stale'):
            apply(self.root, self.folder, self.snapshot, self.review)
        self.assertEqual((self.folder / 'verification.json').read_bytes(), before)
        self.prepare()
        (self.folder / 'delivery-report.md').write_text('New record input')
        with self.assertRaisesRegex(ValueError, 'stale'):
            apply(self.root, self.folder, self.snapshot, self.review)

    def test_repeat_correction_binds_prior_note_not_rewrite(self):
        first = self.do_apply(); doc = v.load_plan(self.folder)
        self.changes[0]['replacement'] += '; exact original input abc'
        second = self.do_apply(); after = v.load_plan(self.folder)
        self.assertEqual(after['items'], doc['items']); self.assertEqual(after['result_correction_reviews'][0], first)
        self.assertEqual(second['corrections'][0]['previous_correction_id'], first['id'])
        notes = links(self.root, after, after['items'][0])
        self.assertEqual([n['correction_state'] for n in notes], ['superseded_note', 'current_note'])

    def test_tampering_origin_or_ledger_and_false_rehash_rejected(self):
        self.do_apply(); doc = v.load_plan(self.folder)
        doc['items'][0]['history'][0]['actual'] = 'Invented observation'
        (self.folder / 'verification.json').write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, 'original corrected result'):
            v.load_plan(self.folder)

    def test_claim_review_and_stage_view_bind_corrections(self):
        import claim_review
        from stage_view import capture as stage_capture
        before = claim_review.identity(self.root, self.folder)
        self.do_apply(); after = claim_review.identity(self.root, self.folder)
        self.assertNotEqual(before['input_digest'], after['input_digest'])
        self.assertIn('result_corrections', after['claims'][0])
        view = stage_capture(self.root, 'FEAT-001', 'verify')
        self.assertTrue(view['claims'][0]['result_corrections'])
        self.support.write_text('Archive unexpectedly changed')
        newer = claim_review.identity(self.root, self.folder)
        self.assertNotEqual(after['input_digest'], newer['input_digest'])
        self.assertFalse(newer['claims'][0]['result_corrections'][0]['support_current'])

    def test_sync_preserves_corrections_and_moves_row_to_retired(self):
        event = self.do_apply(); req = json.loads((self.folder / 'spec/requirements.json').read_text())
        req['requirements'][0]['acceptance_criteria'][0] += ' changed'
        (self.folder / 'spec/requirements.json').write_text(json.dumps(req))
        v.sync(self.root, self.folder); doc = v.load_plan(self.folder)
        self.assertEqual(doc['result_correction_reviews'], [event]); self.assertEqual(doc['schema_version'], 2)
        self.assertTrue(any(r['id'] == self.item for r in doc['retired']))

    def test_missing_unsafe_scratch_and_duplicate_support_rejected(self):
        for refs in (['missing.txt'], ['../outside'], ['.agent-workflow/scratch/private.txt']):
            self.changes[0]['support_refs'] = refs
            with self.assertRaises(ValueError): capture(self.root, self.folder, self.changes)
        self.changes[0]['support_refs'] = [str(self.support.relative_to(self.root))] * 2
        with self.assertRaises(ValueError): capture(self.root, self.folder, self.changes)

    def test_multiple_corrections_exact_review_and_atomic_rejection(self):
        c = copy.deepcopy(self.changes[0]); c['field'] = 'actual'; c['replacement'] = 'Existing abc to ABC observation; precise archive citation'
        self.changes.append(c); frozen, review = self.prepare()
        review['corrections'].pop(); self.review.write_text(json.dumps(review))
        before = (self.folder / 'verification.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'every exact correction'):
            apply(self.root, self.folder, self.snapshot, self.review)
        self.assertEqual(before, (self.folder / 'verification.json').read_bytes())

    def test_save_time_change_does_not_write_candidate(self):
        import result_corrections
        self.prepare(); before = (self.folder / 'verification.json').read_bytes()
        real = result_corrections.capture; count = [0]
        def moving(*args):
            count[0] += 1
            if count[0] == 2: self.support.write_text('Changed during review application')
            return real(*args)
        with patch.object(result_corrections, 'capture', moving):
            with self.assertRaisesRegex(ValueError, 'changed before save'):
                apply(self.root, self.folder, self.snapshot, self.review)
        self.assertEqual(before, (self.folder / 'verification.json').read_bytes())


    def test_no_silent_schema_downgrade(self):
        self.do_apply()
        doc = v.load_plan(self.folder); doc['schema_version'] = 1
        (self.folder / 'verification.json').write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, 'schema 2'):
            v.load_plan(self.folder)

    def test_note_ledger_change_is_detected_and_noop_batch_refused(self):
        self.do_apply(); doc = v.load_plan(self.folder)
        doc['result_correction_reviews'][0]['corrections'][0]['replacement'] += ' invented'
        (self.folder / 'verification.json').write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, 'event changed'):
            v.load_plan(self.folder)

    def test_retained_result_correctable_without_new_retention(self):
        from test_evidence_carry import EvidenceCarryTests
        from evidence_carry import apply as carry_apply
        f = EvidenceCarryTests(); f.setUp(); self.addCleanup(f.doCleanups)
        _, _, a, b = f.prepare(); carry_apply(f.root, f.folder, a, b)
        doc = v.load_plan(f.folder); row = doc['items'][0]
        self.root, self.folder, self.item = f.root, f.folder, f.item
        self.support = self.folder / 'evidence/origin.txt'
        self.changes = [{'item_id': self.item, 'history_index': 1, 'field': 'evidence',
                         'replacement': 'Precise original relevance evidence reference; not a new run',
                         'reason': 'Correct source navigation', 'support_refs': [self.support.relative_to(self.root).as_posix()]}]
        self.scratch = self.root / '.agent-workflow/scratch/corrections'; self.scratch.mkdir(parents=True, exist_ok=True)
        (self.root / '.agent-workflow/.gitignore').write_text('/scratch/\n')
        self.snapshot = self.scratch / 'snapshot.json'; self.review = self.scratch / 'review.json'
        previous = self.effective(); self.do_apply()
        self.assertEqual(v.load_plan(self.folder)['items'], doc['items'])
        self.assertEqual(self.effective(), previous)


    def test_blocked_parent_does_not_prevent_historical_description_note(self):
        p = self.folder / 'spec/requirements.json'; req = json.loads(p.read_text())
        req['requirements'][0]['status'] = 'blocked'; p.write_text(json.dumps(req))
        before = v.load_plan(self.folder)['items']
        self.do_apply()
        self.assertEqual(v.load_plan(self.folder)['items'], before)
        self.assertEqual(json.loads(p.read_text())['requirements'][0]['status'], 'blocked')
