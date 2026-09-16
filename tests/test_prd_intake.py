import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

from intake_helpers import attach_intake, CORE
from prd_intake import validate_intake
import subprocess


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / '.agent-workflow/features/FEAT-001'
        (self.folder / 'sources').mkdir(parents=True); (self.folder / 'spec').mkdir()
        (self.folder / 'sources/prd-original.txt').write_text('Only the first login shows onboarding. Later logins never show it.')
        self.req = {'feature': {'id': 'FEAT-001'}, 'requirements': [{'id': 'R-1', 'status': 'confirmed', 'statement': 'Show onboarding on first login only', 'acceptance_criteria': ['Later logins do not show onboarding'], 'assumptions': []}]}
        self.doc = attach_intake(self.folder, self.req)
        self.doc['items'][0]['aspects'][0]['text'] = 'Only first login'
        self.doc['items'][0]['aspects'].append({'kind': 'exception', 'text': 'Later logins never show it', 'requirement_id': 'R-1', 'field': 'acceptance_criteria/0', 'target_text': 'Later logins do not show onboarding', 'review': 'verified'})
        self.save(); self.review()

    def save(self):
        (self.folder / 'spec/prd-intake.json').write_text(json.dumps(self.doc))
        (self.folder / 'spec/requirements.json').write_text(json.dumps(self.req))

    def review(self, expected=0):
        run = subprocess.run([sys.executable, str(CORE / 'review-prd.py'), str(self.root), 'FEAT-001', '--reviewer', 'fixture-author', '--notes', 'Checked first-login condition and later-login exception against original'], capture_output=True, text=True)
        self.assertEqual(run.returncode, expected, run.stdout + run.stderr)
        self.doc = json.loads((self.folder / 'spec/prd-intake.json').read_text())

    def errors(self):
        return validate_intake(self.folder, self.req, 'develop')[0]

    def test_reviewed_condition_and_exception_pass(self):
        self.assertEqual(self.errors(), [])
        self.assertIn('Later logins', (self.folder / 'spec/prd-analysis.md').read_text())

    def test_reading_gap_blocks_review(self):
        self.doc['units'].append({'id': 'U-2', 'source': 'sources/prd-original.txt', 'locator': 'linked diagram', 'kind': 'image', 'status': 'unreadable', 'reason': 'not supplied', 'impact': 'cannot know navigation'})
        self.save(); self.assertTrue(self.errors()); self.review(expected=1)

    def test_pending_inventory_warns_in_draft_blocks_develop(self):
        self.doc['inventory_complete'] = False; self.save()
        errors, warnings = validate_intake(self.folder, self.req, 'draft')
        self.assertFalse(errors); self.assertTrue(warnings); self.assertTrue(self.errors())

    def test_missing_unit_item_detected(self):
        self.doc['units'].append({'id': 'U-2', 'source': 'sources/prd-original.txt', 'locator': 'footnote', 'kind': 'note', 'status': 'read'})
        self.save(); self.assertTrue(self.errors())

    def test_source_cannot_escape_sources(self):
        (self.folder / 'outside.txt').write_text('external')
        self.doc['units'][0]['source'] = 'sources/../outside.txt'
        self.save(); self.assertTrue(self.errors())

    def test_rule_cannot_be_excluded_as_background(self):
        self.doc['items'][0].update(disposition='excluded', reason='irrelevant')
        self.save(); self.assertTrue(self.errors())

    def test_stale_requirements_and_source_invalidate_review(self):
        self.req['requirements'][0]['acceptance_criteria'].append('Invented retry after 30 seconds')
        self.save(); self.assertTrue(any('stale' in e for e in self.errors()))
        self.req['requirements'][0]['acceptance_criteria'].pop(); self.save()
        self.assertFalse(self.errors())
        (self.folder / 'sources/prd-original.txt').write_text('Every login shows onboarding.')
        self.assertTrue(any('stale' in e for e in self.errors()))

    def test_progress_changes_do_not_invalidate_semantic_review(self):
        self.req['feature']['status'] = 'provisional'
        self.req['requirements'][0]['tasks'] = ['T-2']
        self.save(); self.assertFalse(self.errors())

    def test_empty_or_broken_mapping_blocks(self):
        self.doc['items'][0]['aspects'] = []; self.save(); self.assertTrue(self.errors())

    def test_reverse_link_required(self):
        self.req['requirements'][0]['source_item_ids'] = ['S-UNKNOWN']
        self.save(); self.assertTrue(self.errors())

    def test_changed_coverage_target_blocks(self):
        self.req['requirements'][0]['statement'] = 'Every login shows onboarding'
        self.save(); self.assertTrue(any('target' in e for e in self.errors()))

    def test_missing_legacy_intake_is_not_silently_approved(self):
        (self.folder / 'spec/prd-intake.json').unlink()
        self.assertTrue(self.errors())
        errors, warnings = validate_intake(self.folder, self.req, 'draft')
        self.assertFalse(errors); self.assertTrue(warnings)

    def test_invalid_container_types_return_errors(self):
        for field, bad in [('units', {}), ('items', None), ('inventory_complete', 'yes')]:
            with self.subTest(field=field):
                original = copy.deepcopy(self.doc)
                self.doc[field] = bad; self.save(); self.assertTrue(self.errors())
                self.doc = original

    def test_nested_malformed_aspects_return_errors(self):
        for bad in (None, {}, [None], [{'kind': 'exception', 'text': 'x', 'requirement_id': [], 'field': 'statement'}]):
            with self.subTest(bad=bad):
                original = copy.deepcopy(self.doc)
                self.doc['items'][0]['aspects'] = bad
                self.save(); self.assertTrue(self.errors())
                self.doc = original

    def test_minimal_semantic_pair_invalidates_review(self):
        from prd_intake import review_digest
        for first, second in [('每日最多三次', '每次最多三条'), ('仅管理员可修改', '管理员也可修改')]:
            with self.subTest(first=first):
                self.req['requirements'][0]['statement'] = first
                self.doc['items'][0]['aspects'][0]['target_text'] = first
                before = review_digest(self.folder, self.doc, self.req)
                self.req['requirements'][0]['statement'] = second
                # Even if a caller updates mapping text, an old review cannot be reused.
                self.doc['items'][0]['aspects'][0]['target_text'] = second
                self.assertNotEqual(before, review_digest(self.folder, self.doc, self.req))

    def test_unreviewed_exception_blocks(self):
        self.doc['items'][0]['aspects'][1]['review'] = 'pending'
        self.save(); self.assertTrue(self.errors()); self.review(expected=1)

if __name__ == '__main__':
    unittest.main()
