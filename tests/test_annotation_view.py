import contextlib
import copy
import io
import json
import unittest

import test_evidence_annotations
import test_evidence_archive
import evidence_annotations as annotations
from verification import annotation_links, context, load_plan, manual_evidence_stamp, record, render, state, summary


class AnnotationViewTests(unittest.TestCase):
    def setUp(self):
        self.helper = test_evidence_annotations.EvidenceAnnotationTests()
        self.helper.setUp(); self.addCleanup(self.helper.doCleanups)
        self.root, self.folder = self.helper.root, self.helper.folder

    def apply(self):
        _, review = self.helper.review()
        annotations.apply(self.root, self.folder, self.helper.snapshot, review)

    def view(self):
        before = (self.folder / 'verification.json').read_bytes()
        output = io.StringIO()
        with contextlib.redirect_stdout(output): summary(self.root, self.folder)
        self.assertEqual(before, (self.folder / 'verification.json').read_bytes())
        return json.loads(output.getvalue())

    def test_current_link_displays_exact_row_assessment_and_scope_without_rewriting(self):
        self.apply(); original = copy.deepcopy(load_plan(self.folder))
        item = self.view()['items'][0]; link = item['annotation_links'][0]
        event = original['annotation_reviews'][0]
        self.assertEqual(item['status'], 'retained')
        self.assertEqual(link['applicability'], 'current_receipt')
        self.assertEqual(link['item_assessment'], event['review']['items'][0]['evidence'])
        self.assertEqual(link['scope'], [{'path':'evidence/README.md','role':'index'}])
        self.assertEqual(link['source_result_hash'], original['items'][0]['history'][-1]['annotation_receipt']['source_result_hash'])
        self.assertEqual(item['tested_revision'], original['items'][0]['history'][0]['tested_revision'])
        render(self.folder)
        self.assertIn(link['item_assessment'], (self.folder / 'verification.md').read_text())
        self.assertEqual(load_plan(self.folder), original)

    def test_other_rows_do_not_inherit_shared_correction(self):
        self.apply(); items = self.view()['items']
        self.assertTrue(items[0]['annotation_links'])
        self.assertTrue(all(not r['annotation_links'] for r in items[1:]))

    def test_later_evidence_edit_marks_notes_historical_and_keeps_stale(self):
        self.apply()
        (self.folder / 'evidence/README.md').write_text('Unreviewed later replacement')
        item = self.view()['items'][0]
        self.assertEqual(item['status'], 'stale')
        self.assertEqual(item['annotation_links'][0]['applicability'], 'historical_only')
        render(self.folder)
        self.assertIn('historical_only', (self.folder / 'verification.md').read_text())

    def test_new_observation_does_not_turn_old_note_into_current_correction(self):
        self.apply(); doc = load_plan(self.folder); stamp, head = context(self.root, self.folder, doc)
        record(self.root,self.folder,doc['items'][0]['id'],'passed',stamp,head,'New synthetic observation','Fixture execution at current input')
        item = self.view()['items'][0]
        self.assertEqual(item['status'],'passed')
        self.assertEqual(item['annotation_links'][0]['applicability'],'historical_only')

    def test_two_amendments_preserve_history_and_distinguish_latest(self):
        self.apply(); original = copy.deepcopy(load_plan(self.folder)['items'][0]['history'])
        self.helper.frozen = annotations.capture(self.root,self.folder,[{'path':'evidence/README.md','role':'index'}])
        self.helper.snapshot.write_text(json.dumps(self.helper.frozen))
        (self.folder / 'evidence/README.md').write_text('Index correction two: no new observation.\n')
        self.apply(); item = self.view()['items'][0]
        self.assertEqual([n['applicability'] for n in item['annotation_links']],['historical_only','current_receipt'])
        self.assertEqual(load_plan(self.folder)['items'][0]['history'][:-1], original)

    def test_loose_note_text_is_not_a_machine_link(self):
        # No applied receipt: text naming an item cannot establish a reviewed association.
        (self.folder / 'evidence/loose-notes.md').write_text('requirement:R-1:0 corrected: fixture note\n')
        self.assertTrue(all(not r['annotation_links'] for r in self.view()['items']))

    def test_tampered_shared_assessment_is_rejected_before_display(self):
        self.apply(); doc = load_plan(self.folder)
        doc['annotation_reviews'][0]['review']['items'][0]['evidence'] = 'unreviewed replacement'
        (self.folder / 'verification.json').write_text(json.dumps(doc))
        with self.assertRaises(ValueError): self.view()

    def test_readonly_summary_does_not_change_input_digest(self):
        self.apply(); before = context(self.root,self.folder,load_plan(self.folder))
        self.view(); render(self.folder)
        self.assertEqual(before,context(self.root,self.folder,load_plan(self.folder)))

    def test_scoped_stage_view_includes_linked_notes_without_loading_all_history(self):
        from stage_view import capture
        self.apply(); before = (self.folder / 'verification.json').read_bytes()
        row = load_plan(self.folder)['items'][0]
        view = capture(self.root,self.folder.name,'verify',[],[row['id']])
        claim = next(r for r in view['claims'] if r['id']==row['id'])
        self.assertEqual(claim['annotation_links'][0]['applicability'],'current_receipt')
        self.assertTrue(claim['provenance_readback_required'])
        self.assertNotIn('history',claim)
        self.assertEqual(before,(self.folder / 'verification.json').read_bytes())

    def test_unapplied_adverse_verdict_is_pending_not_approved(self):
        helper = test_evidence_archive.EvidenceArchiveTests(); helper.setUp(); self.addCleanup(helper.doCleanups)
        helper.freeze(); helper.copy_archive(); helper.review(verdict='unknown')
        annotations.apply(helper.root,helper.folder,helper.snapshot,helper.review_path)
        doc = load_plan(helper.folder); row = doc['items'][0]
        stamp,_ = context(helper.root,helper.folder,doc)
        status = state(row,stamp,manual_evidence_stamp(helper.root,helper.folder,row))
        links = annotation_links(doc,row,status)
        self.assertEqual(status,'stale')
        self.assertEqual(links[0]['applicability'],'needs_review')
        self.assertNotIn('source_result_hash',links[0])
