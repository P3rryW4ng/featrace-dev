import json
from pathlib import Path
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

    def test_version_one_record_remains_readable_and_sync_migrates_it(self):
        record, _ = sync(self.root, 'FEAT-001')
        candidate = record['candidates'][0]
        record['schema_version'] = 1
        record.pop('history')
        record['dispositions'] = [{'candidate_id': candidate['id'],
                                   'candidate_digest': candidate['candidate_digest'],
                                   'action': 'not_applicable',
                                   'reason': 'The current adapter does not invoke conversion state.'}]
        self.store(record)
        self.assertEqual(self.validate(), [])
        migrated, _ = sync(self.root, 'FEAT-001')
        self.assertEqual(migrated['schema_version'], 2)
        self.assertEqual(migrated['history'], [])
        self.assertEqual(len(migrated['dispositions']), 1)

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

    def test_sync_preserves_changed_disposition_and_result_as_audit_history(self):
        record, _ = sync(self.root, 'FEAT-001')
        candidate = record['candidates'][0]
        disposition = {'candidate_id': candidate['id'], 'candidate_digest': candidate['candidate_digest'],
                       'action': 'retest', 'reason': 'Touches the repaired conversion path.',
                       'planned_checks': ['Repeat OLD-REG against the current build'],
                       'result': {'status': 'passed', 'method': 'fixture regression',
                                  'evidence': 'OLD-REG passed', 'tested_revision': 'current-v2',
                                  'review_digest': record['review_digest']}}
        record['dispositions'] = [disposition]
        self.store(record)
        fixes = json.loads((self.historical / 'fixes.json').read_text())
        fixes['fixes'][0]['description'] = 'Conversion and retries must remain side-effect free'
        (self.historical / 'fixes.json').write_text(json.dumps(fixes))

        updated, _ = sync(self.root, 'FEAT-001')
        self.assertEqual(updated['schema_version'], 2)
        self.assertEqual(updated['dispositions'], [])
        self.assertEqual(len(updated['history']), 1)
        archived = updated['history'][0]
        self.assertEqual(archived['superseded_reason'], 'candidate_changed')
        self.assertEqual(archived['candidate']['description'], 'Conversion loses preserved state')
        self.assertEqual(archived['disposition'], disposition)
        self.assertTrue(any('needs disposition' in error for error in self.validate()))

        first_bytes = (self.folder / 'regression-review.json').read_bytes()
        repeated, _ = sync(self.root, 'FEAT-001')
        self.assertEqual(repeated['history'], updated['history'])
        self.assertEqual((self.folder / 'regression-review.json').read_bytes(), first_bytes)
        repeated['history'][0]['disposition']['result']['evidence'] = 'edited after archival'
        self.store(repeated)
        self.assertTrue(any('invalid' in error for error in self.validate()))
        with self.assertRaisesRegex(ValueError, 'invalid or duplicate history'):
            sync(self.root, 'FEAT-001')

    def test_sync_preserves_removed_candidate_disposition_as_audit_history(self):
        record, _ = sync(self.root, 'FEAT-001')
        candidate = record['candidates'][0]
        record['dispositions'] = [{'candidate_id': candidate['id'],
                                   'candidate_digest': candidate['candidate_digest'],
                                   'action': 'not_applicable',
                                   'reason': 'The current adapter does not invoke conversion state.'}]
        self.store(record)
        fixes = json.loads((self.historical / 'fixes.json').read_text())
        fixes['fixes'][0]['status'] = 'closed'
        (self.historical / 'fixes.json').write_text(json.dumps(fixes))

        updated, _ = sync(self.root, 'FEAT-001')
        self.assertEqual(updated['candidates'], [])
        self.assertEqual(updated['dispositions'], [])
        self.assertEqual(updated['history'][0]['superseded_reason'], 'candidate_removed')
        self.assertEqual(updated['history'][0]['superseded_by_candidate_digest'], '')
        self.assertEqual(self.validate('check'), [])

    def test_sync_rejects_malformed_history_instead_of_erasing_it(self):
        record, _ = sync(self.root, 'FEAT-001')
        record['history'] = [{'candidate_id': 'broken'}]
        self.store(record)
        with self.assertRaisesRegex(ValueError, 'invalid or duplicate history'):
            sync(self.root, 'FEAT-001')

    def test_agent_instructions_preserve_explicit_sync_only_scope(self):
        repository = Path(__file__).resolve().parents[1]
        reference = (repository / 'skills/dev/core/references/historical-regression.md').read_text()
        entrypoint = (repository / 'skills/dev/SKILL.md').read_text()
        self.assertIn('Sync is discovery, not disposition.', reference)
        self.assertIn('only sync, list, inspect, stop, or not choose', reference)
        self.assertIn('leave new candidates pending and stop', entrypoint)

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
