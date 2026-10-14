import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path
import test_evidence_annotations
import evidence_annotations as a
from verification import load_plan, context, state, manual_evidence_stamp


class EvidenceArchiveTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_evidence_annotations.EvidenceAnnotationTests()
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.root, self.folder = self.fixture.root, self.fixture.folder
        (self.folder / 'evidence/README.md').write_text(self.fixture.frozen['before_text']['evidence/README.md'])
        self.scratch = self.root / '.agent-workflow/scratch/archive-fixture'
        self.scratch.mkdir(parents=True)
        (self.root / '.agent-workflow/.gitignore').write_text('/scratch/\n')
        self.origin = self.scratch / 'raw-run.txt'
        self.origin.write_text('CMD: fixture instrument\nOUT: 21 tests passed; device=private-fixture\n')
        self.additions = [{'path': 'evidence/new-run.txt',
                          'origin_path': self.origin.relative_to(self.root).as_posix(),
                          'transformation': 'verbatim', 'purpose': 'Archive prior unrelated fixture regression execution'}]
        self.snapshot = self.scratch / 'snapshot.json'; self.review_path = self.scratch / 'review.json'

    def freeze(self, metadata=None, additions=None):
        self.frozen = a.capture(self.root, self.folder, metadata or [], self.additions if additions is None else additions)
        self.snapshot.write_text(json.dumps(self.frozen))
        return self.frozen

    def copy_archive(self):
        (self.folder / 'evidence/new-run.txt').write_bytes(self.origin.read_bytes())

    def review(self, verdict='supported'):
        inputs = a.amend_inputs(self.root, self.folder, self.frozen)
        review = {'input_digest': inputs['input_digest'], 'status': 'reviewed', 'independent_context': True,
                  'reviewer': 'fixture fresh reviewer', 'classification_evidence': 'Declared new original archive plus bounded index correction only',
                  'raw_evidence_unchanged': 'All prior artifacts unchanged',
                  'claim_meaning_unchanged': 'Preserved supported rows retain their full original claim; unresolved rows do not get a new pass',
                  'counterexample': 'A new log contradicting the original claim must leave that row stale',
                  'archive_assessment': [{'path': r['path'], 'status': 'supported', 'provenance': 'Backed-up fixture original identity inspected',
                                         'transformation_evidence': 'Compared complete original with archive; any redaction only changes private identifiers',
                                         'relevance_evidence': 'This fixture log belongs to a separate regression'} for r in self.additions],
                  'items': [{'item_id': i['item_id'], 'status': verdict, 'evidence': 'Concrete fixture relevance review for this complete claim'} for i in inputs['items']]}
        self.review_path.write_text(json.dumps(review))
        return review

    def test_new_original_and_index_correction_keep_original_test_identity(self):
        self.freeze([{'path': 'evidence/README.md', 'role': 'index'}]); self.copy_archive()
        (self.folder / 'evidence/README.md').write_text('Corrected index: distinguish static and device observations.\n')
        previous = copy.deepcopy(load_plan(self.folder)['items'][0]['history'])
        self.review(); a.apply(self.root, self.folder, self.snapshot, self.review_path)
        doc = load_plan(self.folder); row = doc['items'][0]
        self.assertEqual(row['history'][:-1], previous)
        self.assertEqual(row['history'][-1]['tested_revision'], previous[-1]['tested_revision'])
        self.assertNotIn('re-executed on device', row['history'][-1]['method'])
        self.assertEqual(len(doc['annotation_reviews']), 1)
        stamp, _ = context(self.root, self.folder, doc)
        self.assertEqual(state(row, stamp, manual_evidence_stamp(self.root, self.folder, row)), 'retained')
        # Snapshot/review includes identities, not private original output bytes.
        self.assertNotIn('device=private-fixture', self.snapshot.read_text())

    def test_unknown_row_is_not_retained_or_rewritten(self):
        self.freeze(); self.copy_archive()
        original = copy.deepcopy(load_plan(self.folder)['items'][0]['history'])
        self.review('unknown'); a.apply(self.root, self.folder, self.snapshot, self.review_path)
        doc = load_plan(self.folder); row = doc['items'][0]
        self.assertEqual(row['history'], original)
        stamp, _ = context(self.root, self.folder, doc)
        self.assertEqual(state(row, stamp, manual_evidence_stamp(self.root, self.folder, row)), 'stale')

    def test_redacted_extract_requires_explicit_transformation_review(self):
        self.additions[0]['transformation'] = 'redacted_extract'
        self.freeze()
        (self.folder / 'evidence/new-run.txt').write_text('OUT: 21 tests passed; device=[redacted]\n')
        review = self.review(); del review['archive_assessment'][0]['transformation_evidence']
        self.review_path.write_text(json.dumps(review))
        with self.assertRaisesRegex(ValueError, 'origin/transformation'):
            a.apply(self.root, self.folder, self.snapshot, self.review_path)
        self.review(); a.apply(self.root, self.folder, self.snapshot, self.review_path)
        self.assertEqual(load_plan(self.folder)['items'][0]['history'][-1]['status'], 'retained')

    def test_original_mutation_verbatim_mismatch_and_existing_overwrite_reject(self):
        self.freeze(); self.copy_archive()
        self.origin.write_text('Changed backup')
        with self.assertRaisesRegex(ValueError, 'originals changed'):
            a.amend_inputs(self.root, self.folder, self.frozen)
        self.origin.write_bytes((self.folder / 'evidence/new-run.txt').read_bytes())
        (self.folder / 'evidence/new-run.txt').write_text('Wrong copied output')
        with self.assertRaisesRegex(ValueError, 'verbatim archive differs'):
            a.amend_inputs(self.root, self.folder, self.frozen)
        with self.assertRaisesRegex(ValueError, 'new destinations'):
            a.capture(self.root, self.folder, [], [dict(self.additions[0], path='evidence/origin.txt')])

    def test_old_raw_modification_extra_addition_and_code_change_reject(self):
        self.freeze(); self.copy_archive()
        (self.folder / 'evidence/undeclared.txt').write_text('undeclared archive')
        with self.assertRaisesRegex(ValueError, 'raw change'):
            a.amend_inputs(self.root, self.folder, self.frozen)
        (self.folder / 'evidence/undeclared.txt').unlink()
        old = (self.folder / 'evidence/origin.txt').read_bytes()
        (self.folder / 'evidence/origin.txt').write_text('rewritten existing original')
        with self.assertRaises(ValueError): a.amend_inputs(self.root, self.folder, self.frozen)
        (self.folder / 'evidence/origin.txt').write_bytes(old)
        (self.root / 'convert.py').write_text('changed business code')
        with self.assertRaisesRegex(ValueError, 'plan/code changed|business worktree'):
            a.amend_inputs(self.root, self.folder, self.frozen)

    def test_unignored_or_outside_original_refused(self):
        with self.assertRaises(ValueError):
            a.capture(self.root, self.folder, [], [dict(self.additions[0], origin_path='convert.py')])
        (self.root / '.agent-workflow/.gitignore').write_text('')
        with self.assertRaisesRegex(ValueError, 'Git ignored'):
            self.freeze()

    def test_new_file_change_after_review_or_result_tampering_refused(self):
        self.freeze(); self.copy_archive(); self.review()
        before = (self.folder / 'verification.json').read_bytes()
        (self.folder / 'evidence/new-run.txt').write_text('changed after review')
        with self.assertRaises(ValueError): a.apply(self.root, self.folder, self.snapshot, self.review_path)
        self.assertEqual(before, (self.folder / 'verification.json').read_bytes())
        self.copy_archive(); self.review(); a.apply(self.root, self.folder, self.snapshot, self.review_path)
        doc = load_plan(self.folder); doc['items'][0]['history'][-1]['actual'] = 'Fresh device observation'
        (self.folder / 'verification.json').write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, 'metadata-only'): load_plan(self.folder)

    def test_installed_cli_shape_capture_inputs_and_apply(self):
        scripts = Path(a.__file__).parent
        additions = self.scratch / 'additions.json'; additions.write_text(json.dumps(self.additions))
        def cli(*args):
            return subprocess.run([sys.executable, str(scripts / 'evidence_annotations.py'), *args, str(self.root), self.folder.name], capture_output=True, text=True)
        result = cli('capture', '--additions', str(additions)); self.assertEqual(result.returncode, 0, result.stderr)
        self.frozen = json.loads(result.stdout); self.snapshot.write_text(result.stdout)
        self.copy_archive(); self.review()
        result = cli('review-inputs', '--snapshot', str(self.snapshot)); self.assertEqual(result.returncode, 0, result.stderr)
        result = cli('apply', '--snapshot', str(self.snapshot), '--review', str(self.review_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('retained=1 unresolved=0', result.stdout)

    def test_recomputed_snapshot_cannot_revive_stale_predecessor(self):
        from impact import digest
        self.freeze(); self.copy_archive(); self.review('unknown')
        a.apply(self.root, self.folder, self.snapshot, self.review_path)
        doc = load_plan(self.folder); row = doc['items'][0]
        before_plan = (self.folder / 'verification.json').read_bytes()
        # Rebuild an edited snapshot claiming this now-stale row is eligible.
        frozen = copy.deepcopy(self.frozen)
        frozen['schema_version'] = 1; frozen.pop('archive_additions')
        frozen['metadata'] = [{'path': 'evidence/README.md', 'role': 'index'}]
        frozen['before_text'] = {'evidence/README.md': (self.folder / 'evidence/README.md').read_text()}
        from evidence_carry import source_identity
        frozen['source_inputs'] = source_identity(self.root, self.folder)
        frozen['plan_digest'] = digest(doc)
        frozen['items'][0]['semantic_digest'] = manual_evidence_stamp(self.root, self.folder, row)
        frozen['input_digest'] = digest({k: value for k, value in frozen.items() if k != 'input_digest'})
        (self.folder / 'evidence/README.md').write_text('Another harmless index correction')
        with self.assertRaisesRegex(ValueError, 'stale rows cannot be revived'):
            a.amend_inputs(self.root, self.folder, frozen)
        self.assertEqual(before_plan, (self.folder / 'verification.json').read_bytes())
