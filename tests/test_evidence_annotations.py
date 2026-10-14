import copy
import json
import unittest
import test_evidence_carry
import evidence_annotations as a
from evidence_carry import apply as carry_apply
from verification import load_plan, context, manual_evidence_stamp, state, sync


class EvidenceAnnotationTests(unittest.TestCase):
    def setUp(self):
        self.helper = test_evidence_carry.EvidenceCarryTests()
        self.helper.setUp(); self.addCleanup(self.helper.doCleanups)
        self.root, self.folder = self.helper.root, self.helper.folder
        (self.folder / 'evidence/README.md').write_text('Index: all results were device observations.\n')
        _, _, snap, review = self.helper.prepare(); carry_apply(self.root, self.folder, snap, review)
        self.original = copy.deepcopy(load_plan(self.folder))
        self.frozen = a.capture(self.root, self.folder, [{'path': 'evidence/README.md', 'role': 'index'}])
        self.snapshot = self.folder / 'annotation-snapshot.json'; self.snapshot.write_text(json.dumps(self.frozen))
        (self.folder / 'evidence/README.md').write_text('Index: device observations and static inspections are different. See original artifacts.\n')

    def review(self):
        inputs = a.amend_inputs(self.root, self.folder, self.frozen)
        verdict = {'input_digest': inputs['input_digest'], 'status': 'supported', 'independent_context': True,
                   'reviewer': 'fixture fresh metadata reviewer', 'classification_evidence': 'README is an index, not raw output; corrected overly broad method wording',
                   'raw_evidence_unchanged': 'Original run/source binding artifacts identical',
                   'claim_meaning_unchanged': 'No acceptance or original observed result changes; classification matches existing limitations',
                   'counterexample': 'A result log edit would change proof; actual patch edits only index text',
                   'items': [{'item_id': i['item_id'], 'status': 'supported', 'evidence': 'Previous supported claim remains supported with narrower accurate index description'} for i in inputs['items']]}
        output = self.folder / 'annotation-review.json'; output.write_text(json.dumps(verdict))
        return verdict, output

    def test_index_correction_appends_history_preserves_raw_and_test_identity(self):
        verdict, output = self.review(); a.apply(self.root, self.folder, self.snapshot, output)
        doc = load_plan(self.folder); row = doc['items'][0]
        self.assertEqual(row['history'][:-1], self.original['items'][0]['history'])
        self.assertEqual(row['history'][-1]['tested_revision'], row['history'][-2]['tested_revision'])
        stamp, _ = context(self.root, self.folder, doc)
        self.assertEqual(state(row, stamp, manual_evidence_stamp(self.root, self.folder, row)), 'retained')
        self.assertEqual(len(doc['annotation_reviews']), 1)
        sync(self.root, self.folder)
        self.assertEqual(load_plan(self.folder)['annotation_reviews'], doc['annotation_reviews'])

    def test_raw_evidence_code_authority_or_parent_change_refuses(self):
        (self.folder / 'evidence/origin.txt').write_text('changed original proof')
        with self.assertRaisesRegex(ValueError, 'raw change'): a.amend_inputs(self.root, self.folder, self.frozen)

    def test_unknown_partial_wrong_digest_and_missing_row_refuse(self):
        verdict, output = self.review()
        for patch in ({'status': 'partial'}, {'independent_context': False}, {'input_digest': 'bad'}, {'items': []}):
            output.write_text(json.dumps(dict(verdict, **patch)))
            with self.assertRaises(ValueError): a.apply(self.root, self.folder, self.snapshot, output)
        self.assertEqual(load_plan(self.folder), self.original)

    def test_new_failure_or_semantic_change_cannot_be_overwritten(self):
        req = json.loads((self.folder / 'spec/requirements.json').read_text())
        req['requirements'][0]['statement'] += ' new requirement'
        (self.folder / 'spec/requirements.json').write_text(json.dumps(req))
        with self.assertRaises(ValueError): a.amend_inputs(self.root, self.folder, self.frozen)

    def test_raw_transcript_cannot_be_declared_index(self):
        (self.folder / 'evidence/raw.txt').write_text('CMD: device test\nOUT: passed\n')
        with self.assertRaisesRegex(ValueError, 'raw command/output'):
            a.capture(self.root, self.folder, [{'path': 'evidence/raw.txt', 'role': 'index'}])

    def test_receipt_tampering_or_later_metadata_edit_invalidates(self):
        _, output = self.review(); a.apply(self.root, self.folder, self.snapshot, output)
        doc = load_plan(self.folder); row = doc['items'][0]
        (self.folder / 'evidence/README.md').write_text('another metadata change')
        stamp, _ = context(self.root, self.folder, doc)
        self.assertEqual(state(row, stamp, manual_evidence_stamp(self.root, self.folder, row)), 'stale')
        doc['annotation_reviews'][0]['review']['items'] = []
        (self.folder / 'verification.json').write_text(json.dumps(doc))
        with self.assertRaises(ValueError): load_plan(self.folder)

    def test_result_cannot_claim_reexecution_or_new_observed_outcome(self):
        _, output = self.review(); a.apply(self.root, self.folder, self.snapshot, output)
        original = load_plan(self.folder)
        for key, value in (('actual', 'New device result observed'), ('method', 'Real device rerun'),
                           ('evidence', 'New observation'), ('reason', 'New behavior accepted')):
            doc = copy.deepcopy(original); doc['items'][0]['history'][-1][key] = value
            (self.folder / 'verification.json').write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError, 'metadata-only'):
                load_plan(self.folder)
