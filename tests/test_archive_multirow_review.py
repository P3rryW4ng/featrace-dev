import copy
import json
import sys
import unittest

import test_evidence_archive
import evidence_annotations as a
from evidence_carry import apply as carry_apply
from verification import load_plan, context, state, manual_evidence_stamp


class ArchiveMultirowReviewTests(unittest.TestCase):
    def test_supported_unknown_then_metadata_amendment_preserves_stale_history(self):
        fixture = test_evidence_archive.EvidenceArchiveTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        root, folder = fixture.root, fixture.folder
        doc = load_plan(folder)
        # Synthetic historical raw observation for the second manual row.
        doc['items'][1]['history'].append(copy.deepcopy(doc['items'][0]['history'][0]))
        (folder / 'verification.json').write_text(json.dumps(doc))
        helper = fixture.fixture.helper
        helper.item = doc['items'][1]['id']
        _, _, snapshot, review = helper.prepare()
        carry_apply(root, folder, snapshot, review)
        fixture.freeze()
        fixture.copy_archive()
        verdict = fixture.review()
        verdict['items'][1]['status'] = 'unknown'
        fixture.review_path.write_text(json.dumps(verdict))
        unknown_history = copy.deepcopy(load_plan(folder)['items'][1]['history'])
        tested = load_plan(folder)['items'][0]['history'][-1]['tested_revision']
        a.apply(root, folder, fixture.snapshot, fixture.review_path)

        def assert_states():
            doc = load_plan(folder)
            stamp, _ = context(root, folder, doc)
            self.assertEqual([state(row, stamp, manual_evidence_stamp(root, folder, row))
                              for row in doc['items'][:2]], ['retained', 'stale'])
            self.assertEqual(doc['items'][1]['history'], unknown_history)
            self.assertEqual(doc['items'][0]['history'][-1]['tested_revision'], tested)

        assert_states()
        frozen = a.capture(root, folder, [{'path': 'evidence/README.md', 'role': 'index'}])
        self.assertEqual(len(frozen['items']), 1)
        self.assertEqual(len(frozen['excluded_items']), 1)
        fixture.snapshot.write_text(json.dumps(frozen))
        (folder / 'evidence/README.md').write_text('Second correction: archive is historical; execution identity unchanged.\n')
        inputs = a.amend_inputs(root, folder, frozen)
        verdict.pop('archive_assessment')
        verdict['status'] = 'supported'
        verdict['input_digest'] = inputs['input_digest']
        verdict['items'] = [{'item_id': inputs['items'][0]['item_id'], 'status': 'supported',
                             'evidence': 'Index correction preserves this eligible row.'}]
        fixture.review_path.write_text(json.dumps(verdict))
        a.apply(root, folder, fixture.snapshot, fixture.review_path)
        assert_states()
        self.assertEqual(len(load_plan(folder)['annotation_reviews']), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
