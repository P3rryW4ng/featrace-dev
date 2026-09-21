import json
import unittest

import test_impact
from regression_review import sync, validate_review


class HistoricalRegressionReviewTests(unittest.TestCase):
    write = test_impact.ImpactTests.write
    save = test_impact.ImpactTests.save
    git = test_impact.ImpactTests.git

    def setUp(self):
        test_impact.ImpactTests.setUp(self)
        self.req['feature']['modules'] = ['wallet']
        self.write('spec/requirements.json', self.req)
        historical = self.root / '.agent-workflow/features/HIST-001'
        (historical / 'spec').mkdir(parents=True)
        (historical / 'spec/requirements.json').write_text(json.dumps({
            'feature': {'id': 'HIST-001', 'status': 'complete', 'modules': ['wallet']},
            'requirements': [{'id': 'R-OLD'}],
        }))
        (historical / 'traceability.json').write_text(json.dumps({
            'feature_id': 'HIST-001',
            'links': [{'requirement_id': 'R-OLD', 'code': ['convert.py'], 'tests': ['OLD-REG']}],
        }))
        (historical / 'fixes.json').write_text(json.dumps({
            'feature_id': 'HIST-001',
            'fixes': [{'id': 'FIX-009', 'status': 'verified', 'kind': 'implementation_defect',
                       'description': 'Conversion loses preserved state', 'requirement_ids': ['R-OLD'],
                       'code_refs': ['convert.py:12'], 'regression_test_ids': ['OLD-REG'],
                       'tested_revision': 'historical-v1'}],
        }))
        self.historical = historical

    def record(self):
        return json.loads((self.folder / 'regression-review.json').read_text())

    def store(self, record):
        (self.folder / 'regression-review.json').write_text(json.dumps(record))

    def validate(self, stage='develop'):
        req = json.loads((self.folder / 'spec/requirements.json').read_text())
        return validate_review(self.root, self.folder, req, stage)[0]

    def test_sync_finds_verified_fix_and_requires_explicit_disposition(self):
        record, warnings = sync(self.root, 'FEAT-001')
        self.assertEqual(warnings, [])
        self.assertEqual([row['id'] for row in record['candidates']], ['HIST-001:FIX-009'])
        self.assertEqual(record['candidates'][0]['matched_modules'], ['wallet'])
        self.assertEqual(record['candidates'][0]['matched_paths'], ['convert.py'])
        self.assertTrue(any('needs disposition' in error for error in self.validate()))
        candidate = record['candidates'][0]
        record['dispositions'] = [{'candidate_id': candidate['id'], 'candidate_digest': candidate['candidate_digest'],
                                   'action': 'not_applicable', 'reason': 'Current edit does not change conversion state.'}]
        self.store(record)
        self.assertEqual(self.validate(), [])

    def test_retest_needs_current_result_and_stales_when_history_changes(self):
        record, _ = sync(self.root, 'FEAT-001')
        candidate = record['candidates'][0]
        record['dispositions'] = [{'candidate_id': candidate['id'], 'candidate_digest': candidate['candidate_digest'],
                                   'action': 'retest', 'reason': 'Touches the repaired conversion path.',
                                   'planned_checks': ['Repeat OLD-REG against the current build']}]
        self.store(record)
        self.assertEqual(self.validate(), [])
        self.assertTrue(any('passed/waived result' in error for error in self.validate('check')))
        record['dispositions'][0]['result'] = {
            'status': 'passed', 'method': 'fixture regression', 'evidence': 'OLD-REG passed',
            'tested_revision': 'current-v2', 'review_digest': record['review_digest'],
        }
        self.store(record)
        self.assertEqual(self.validate('check'), [])
        fixes = json.loads((self.historical / 'fixes.json').read_text())
        fixes['fixes'][0]['description'] = 'Updated historical repair description'
        (self.historical / 'fixes.json').write_text(json.dumps(fixes))
        self.assertTrue(any('stale' in error for error in self.validate('check')))

    def test_closed_report_is_not_a_regression_candidate(self):
        self.req['feature']['modules'] = ['chat']
        self.write('spec/requirements.json', self.req)
        fixes = json.loads((self.historical / 'fixes.json').read_text())
        fixes['fixes'][0]['status'] = 'closed'
        (self.historical / 'fixes.json').write_text(json.dumps(fixes))
        record, _ = sync(self.root, 'FEAT-001')
        self.assertEqual(record['candidates'], [])
        self.assertEqual(validate_review(self.root, self.folder,
                                         json.loads((self.folder / 'spec/requirements.json').read_text()), 'check')[0], [])

    def test_verified_fix_in_current_feature_is_also_protected(self):
        fixes = {'feature_id': 'FEAT-001', 'fixes': [{
            'id': 'FIX-SELF', 'status': 'verified', 'kind': 'implementation_defect',
            'description': 'Preserve the current feature repair', 'requirement_ids': ['R-1'],
            'code_refs': ['convert.py'], 'regression_test_ids': ['UT-1'],
            'tested_revision': 'current-v1',
        }]}
        self.write('fixes.json', fixes)
        record, _ = sync(self.root, 'FEAT-001')
        self.assertIn('FEAT-001:FIX-SELF', [row['id'] for row in record['candidates']])


if __name__ == '__main__':
    unittest.main()
