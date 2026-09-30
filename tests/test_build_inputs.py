import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'skills/dev/core/scripts/build-inputs.py'
spec = importlib.util.spec_from_file_location('build_inputs', SCRIPT)
build_inputs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_inputs)


class BuildInputsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'inputs'
        self.folder = self.root / '.agent-workflow/features/FEAT-1'
        (self.folder / 'spec').mkdir(parents=True)
        self.write('spec/requirements.json', {'feature': {'id': 'FEAT-1'}, 'requirements': [
            {'id': 'R-A', 'status': 'confirmed', 'statement': 'Change A',
             'sources': [{'ref': 'sources/prd.txt'}]},
            {'id': 'R-B', 'status': 'confirmed', 'statement': 'Change B'}]})
        self.write('tasks.json', {'feature_id': 'FEAT-1', 'tasks': [
            {'id': 'T-A', 'requirement_ids': ['R-A'], 'status': 'planned'},
            {'id': 'T-B', 'requirement_ids': ['R-B'], 'status': 'planned'}]})
        self.write('decisions.json', {'feature_id': 'FEAT-1', 'decisions': [
            {'id': 'D-A', 'requirement_ids': ['R-A'], 'chosen': 'A'},
            {'id': 'D-B', 'requirement_ids': ['R-B'], 'chosen': 'B'},
            {'id': 'D-GLOBAL', 'chosen': 'Preserve old behavior'}]})
        self.write('impact.json', {'feature_id': 'FEAT-1', 'base_revision': 'old',
                   'allowed_paths': ['a.py', 'b.py'], 'mechanisms': {'callers': {'status': 'reviewed'}},
                   'behaviors': [
                       {'id': 'B-A', 'kind': 'change', 'requirement_ids': ['R-A']},
                       {'id': 'B-B', 'kind': 'change', 'requirement_ids': ['R-B']},
                       {'id': 'B-OLD', 'kind': 'preserve', 'requirement_ids': ['R-B']}]})
        self.write('traceability.json', {'feature_id': 'FEAT-1', 'links': [
            {'requirement_id': 'R-A', 'code': ['a.py']},
            {'requirement_id': 'R-B', 'code': ['b.py']}]})
        self.write('task-review.json', {'current': {'digest': 'same'}, 'review': {'digest': 'same'}})
        self.write('regression-review.json', {'candidates': [{'id': 'FIX-1'}],
                                               'dispositions': [{'candidate_id': 'FIX-1'}]})

    def write(self, name, value):
        path = self.folder / name
        path.write_text(json.dumps(value))

    def test_task_view_selects_local_authority_and_keeps_cross_cutting_rules(self):
        before = {p: p.read_bytes() for p in self.folder.rglob('*.json')}
        view = build_inputs.collect(self.root, 'FEAT-1', 'T-A')
        self.assertEqual(view['task']['id'], 'T-A')
        self.assertEqual([r['id'] for r in view['requirements']], ['R-A'])
        self.assertEqual([d['id'] for d in view['decisions']], ['D-A', 'D-GLOBAL'])
        self.assertEqual([b['id'] for b in view['impact']['behaviors']], ['B-A', 'B-OLD'])
        self.assertEqual([t['requirement_id'] for t in view['traceability']], ['R-A'])
        self.assertEqual(view['omitted_explicitly_unrelated']['tasks'], 1)
        self.assertEqual(view['review_index']['task_semantics']['reviewed_digest'], 'same')
        self.assertEqual(len(view['record_sha256']), 7)
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_requirement_record_change_changes_view_digest(self):
        first = build_inputs.collect(self.root, 'FEAT-1', 'T-A')
        doc = json.loads((self.folder / 'spec/requirements.json').read_text())
        doc['requirements'][0]['statement'] = 'Changed A'
        self.write('spec/requirements.json', doc)
        second = build_inputs.collect(self.root, 'FEAT-1', 'T-A')
        self.assertNotEqual(first['input_digest'], second['input_digest'])

    def test_missing_requirement_and_symlink_authority_are_rejected(self):
        task_file = self.folder / 'tasks.json'
        doc = json.loads(task_file.read_text())
        doc['tasks'][0]['requirement_ids'] = ['R-MISSING']
        self.write('tasks.json', doc)
        with self.assertRaisesRegex(ValueError, 'missing requirement'):
            build_inputs.collect(self.root, 'FEAT-1', 'T-A')
        doc['tasks'][0]['requirement_ids'] = ['R-A']
        self.write('tasks.json', doc)
        target = self.folder / 'decisions.json'
        target.unlink()
        target.symlink_to(self.folder / 'traceability.json')
        with self.assertRaisesRegex(ValueError, 'symlink authority'):
            build_inputs.collect(self.root, 'FEAT-1', 'T-A')

    def test_invalid_review_index_is_not_silently_treated_as_current(self):
        self.write('task-review.json', {'current': 'bad', 'review': {'digest': 'same'}})
        with self.assertRaisesRegex(ValueError, 'invalid task-review'):
            build_inputs.collect(self.root, 'FEAT-1', 'T-A')


if __name__ == '__main__':
    unittest.main()
