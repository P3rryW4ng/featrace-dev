import json
import unittest

import test_verification as fixture
from claim_review import identity, validate


class ClaimReviewTests(unittest.TestCase):
    write = fixture.VerificationTests.write
    run_script = fixture.VerificationTests.run_script
    git = fixture.VerificationTests.git
    save = fixture.VerificationTests.save
    gates = fixture.VerificationTests.gates
    plan = fixture.VerificationTests.plan
    run_checks = fixture.VerificationTests.run_checks
    accept_manual = fixture.VerificationTests.accept_manual

    def setUp(self):
        fixture.VerificationTests.setUp(self)
        self.run_checks()
        self.accept_manual()

    def review(self, verdict='supported'):
        captured = identity(self.root, self.folder)
        return {'feature_id': self.folder.name, 'input_digest': captured['input_digest'],
                'reviewer': 'fresh-context fixture reviewer',
                'findings': [{'id': row['id'], 'verdict': verdict,
                              'source_basis': 'Reviewed source and requirement statement',
                              'required_scope': 'All three APIs, exact configured locales, same build',
                              'observed_scope': 'Three assertions on exact locales in current fixture',
                              'evidence_ref': 'tests/fixture.py:test_all_apis',
                              'counterexample_check': 'A fourth locale would violate the criterion; exact-list assertions exclude it'}
                             for row in captured['claims']]}

    def save_review(self, review):
        (self.folder / 'claim-review.json').write_text(json.dumps(review))

    def test_missing_partial_and_supported_review(self):
        self.assertIn('missing', ' '.join(validate(self.root, self.folder)))
        captured = json.loads(self.run_script('claim_review.py', 'capture', self.root, 'FEAT-001'))
        self.assertEqual(captured['feature_id'], 'FEAT-001')
        review = self.review('partial')
        review['findings'][0]['observed_scope'] = 'Only getHostUserInfo on a nearby locale pair'
        self.save_review(review)
        self.assertIn('unresolved', ' '.join(validate(self.root, self.folder)))
        self.save_review(self.review())
        self.assertEqual(validate(self.root, self.folder), [])
        self.assertIn('CLAIM_REVIEW_CURRENT', self.run_script('claim_review.py', 'check', self.root, 'FEAT-001'))

    def test_changed_source_or_result_invalidates_review(self):
        self.save_review(self.review())
        self.assertEqual(validate(self.root, self.folder), [])
        (self.root / 'convert.py').write_text('new implementation')
        self.assertIn('stale', ' '.join(validate(self.root, self.folder)))

    def test_missing_row_and_waiver_without_matching_result_rejected(self):
        review = self.review()
        review['findings'].pop()
        self.save_review(review)
        self.assertIn('every active', ' '.join(validate(self.root, self.folder)))
        review = self.review('approved_waiver')
        self.save_review(review)
        self.assertIn('unresolved', ' '.join(validate(self.root, self.folder)))


if __name__ == '__main__':
    unittest.main()
