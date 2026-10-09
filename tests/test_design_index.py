import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from intake_helpers import CORE
import sys
sys.path.insert(0, str(CORE))
from design_index import figma_identity, match_state, validate_index


class DesignIndexTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name) / 'F-1'
        (self.folder / 'sources').mkdir(parents=True)
        (self.folder / 'spec').mkdir()
        self.source = 'sources/design-part-01.json'
        (self.folder / self.source).write_text('{"frames":["1:2","1:3"]}')
        digest = hashlib.sha256((self.folder / self.source).read_bytes()).hexdigest()
        self.req = {'feature': {'id': 'F-1', 'design_index_required': True},
                    'requirements': [{'id': 'R-1', 'status': 'confirmed'}]}
        self.intake = {'sources': [{'path': self.source, 'kind': 'design'}], 'units': [
            {'id': 'U-1', 'source': self.source, 'status': 'read',
             'figma_file_key': 'ABC123', 'figma_node_id': '1:2'},
            {'id': 'U-2', 'source': self.source, 'status': 'read',
             'figma_file_key': 'ABC123', 'figma_node_id': '1:3'}]}
        self.index = {'schema_version': 1, 'feature_id': 'F-1',
                      'scope': {'status': 'reviewed', 'evidence': 'Compared relevant frames with PRD R-1'},
                      'sources': [{'path': self.source, 'status': 'current'}],
                      'screens': [{'id': 'SCREEN-1', 'name': 'Payment', 'requirement_ids': ['R-1'],
                                   'states': [
                                       {'id': 'STATE-1', 'name': 'Initial', 'url': 'https://www.figma.com/design/ABC123/Payment?node-id=1-2',
                                        'source': self.source, 'source_sha256': digest, 'status': 'read', 'unit_ids': ['U-1']},
                                       {'id': 'STATE-2', 'name': 'Error', 'url': 'https://www.figma.com/design/ABC123/Payment?node-id=1-3',
                                        'source': self.source, 'source_sha256': digest, 'status': 'read', 'unit_ids': ['U-2']}]}]}
        self.save()

    def save(self):
        (self.folder / 'spec/prd-intake.json').write_text(json.dumps(self.intake))
        (self.folder / 'design-index.json').write_text(json.dumps(self.index))

    def test_same_logical_screen_multiple_states_and_exact_match(self):
        self.assertEqual(validate_index(self.folder, self.req, 'check'), ([], []))
        found = match_state(self.folder, url='https://figma.com/file/ABC123/anything?node-id=1%3A3')
        self.assertEqual(found['status'], 'exact_identity')
        self.assertEqual(found['match']['state_id'], 'STATE-2')
        self.assertTrue(found['content_review_required'])

    def test_new_node_and_description_never_auto_replace(self):
        found = match_state(self.folder, url='https://figma.com/design/ABC123/Payment?node-id=1-4', screen_name='Payment')
        self.assertEqual(found['status'], 'candidate_only')
        self.assertTrue(found['requires_confirmation'])
        self.assertEqual(len(found['candidates']), 2)
        described = match_state(self.folder, screen_name='Payment', state_name='Error')
        self.assertEqual(described['status'], 'candidate_only')
        self.assertEqual(described['candidates'][0]['state_id'], 'STATE-2')
        copied = match_state(self.folder, url='https://figma.com/design/NEW123/Copy?node-id=9-9', screen_name='Payment', state_name='Error')
        self.assertEqual(copied['status'], 'candidate_only')
        self.assertEqual(copied['candidates'][0]['state_id'], 'STATE-2')

    def test_source_bytes_and_exact_unit_identity_are_checked(self):
        supplied = self.folder / self.source
        self.assertEqual(match_state(self.folder, url=self.index['screens'][0]['states'][0]['url'], supplied=supplied)['match']['evidence_bytes'], 'same')
        supplied.write_text('{"frames":["1:2","1:3","1:4"]}')
        self.assertTrue(any('bytes changed' in x for x in validate_index(self.folder, self.req, 'check')[0]))
        self.assertEqual(match_state(self.folder, url=self.index['screens'][0]['states'][0]['url'], supplied=supplied)['match']['evidence_bytes'], 'different')
        self.intake['units'][0]['figma_node_id'] = '11:2'
        self.save()
        self.assertTrue(any('exact Figma file and node' in x for x in validate_index(self.folder, self.req, 'check')[0]))

    def test_unread_or_new_source_blocks_check(self):
        self.index['screens'][0]['states'][0]['status'] = 'indexed'
        self.intake['sources'].append({'path': 'sources/design-part-02.json', 'kind': 'design'})
        self.save()
        errors, _ = validate_index(self.folder, self.req, 'check')
        self.assertTrue(any('every registered design source' in x for x in errors))
        self.assertTrue(any('not read or explicitly excluded' in x for x in errors))

    def test_identity_must_include_file_and_node(self):
        self.assertEqual(figma_identity('https://figma.com/design/ABC123/a?node-id=1-2'), ('ABC123', '1:2'))
        with self.assertRaises(ValueError):
            figma_identity('https://figma.com/design/ABC123/a')
        with self.assertRaises(ValueError):
            figma_identity('https://other.example/design/ABC123/a?node-id=1-2')


if __name__ == '__main__':
    unittest.main()
