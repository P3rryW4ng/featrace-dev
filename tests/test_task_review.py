import json
from pathlib import Path
import unittest

import test_fix_flow
from task_review import review, sync, validate_task_review


class TaskSemanticReviewTests(unittest.TestCase):
    write = test_fix_flow.FixFlowTests.write
    run_script = test_fix_flow.FixFlowTests.run_script

    def setUp(self):
        test_fix_flow.FixFlowTests.setUp(self)
        self.req['feature']['task_review_required'] = True
        self.write('spec/requirements.json', self.req)

    def tasks(self):
        return json.loads((self.folder / 'tasks.json').read_text())['tasks']

    def save_tasks(self, tasks):
        self.write('tasks.json', {'feature_id': 'FEAT-001', 'tasks': tasks})

    def errors(self, stage='develop'):
        return validate_task_review(self.folder, self.req, self.tasks(), stage)[0]

    def accept(self, task_ids=('T-1',), requirement_ids=('R-1',)):
        return review(self.root, 'FEAT-001', 'fixture-reviewer',
                      'Compared changed task wording with linked requirement and acceptance criteria.',
                      list(task_ids), list(requirement_ids), ['R-1 statement and acceptance criteria'])

    def test_missing_required_blocks_but_legacy_only_warns(self):
        errors, warnings = validate_task_review(self.folder, self.req, self.tasks(), 'develop')
        self.assertTrue(errors); self.assertFalse(warnings)
        del self.req['feature']['task_review_required']
        errors, warnings = validate_task_review(self.folder, self.req, self.tasks(), 'develop')
        self.assertFalse(errors); self.assertTrue(warnings)

    def test_initial_sync_requires_focused_review(self):
        record, changed = sync(self.root, 'FEAT-001')
        self.assertEqual(changed, ['T-1'])
        self.assertEqual(record['review'], {})
        self.assertTrue(any('T-1' in error for error in self.errors()))
        accepted = self.accept()
        self.assertEqual(accepted['review']['changed_task_ids'], ['T-1'])
        self.assertEqual(accepted['review']['requirement_ids'], ['R-1'])
        self.assertEqual(self.errors(), [])

    def test_progress_and_execution_evidence_do_not_stale_review(self):
        sync(self.root, 'FEAT-001'); self.accept()
        tasks = self.tasks()
        tasks[0]['status'] = 'in_progress'
        tasks[0]['test_evidence'] = ['new run passed']
        tasks[0]['assignee'] = 'fixture owner'
        self.save_tasks(tasks)
        record, changed = sync(self.root, 'FEAT-001')
        self.assertEqual(changed, [])
        self.assertEqual(record['review']['digest'], record['current']['digest'])
        self.assertEqual(self.errors(), [])

    def test_wording_change_blocks_until_exact_local_review(self):
        sync(self.root, 'FEAT-001'); first = self.accept()
        tasks = self.tasks(); tasks[0]['title'] = 'Implement lowercase conversion'; self.save_tasks(tasks)
        record, changed = sync(self.root, 'FEAT-001')
        self.assertEqual(changed, ['T-1'])
        self.assertNotEqual(record['review']['digest'], record['current']['digest'])
        self.assertTrue(any('T-1' in error for error in self.errors()))
        with self.assertRaisesRegex(ValueError, 'exactly match changed tasks'):
            review(self.root, 'FEAT-001', 'fixture', 'Compared wording', [], ['R-1'], ['R-1'])
        accepted = self.accept()
        self.assertEqual(len(accepted['history']), 1)
        self.assertEqual(accepted['history'][0]['review']['digest'], first['review']['digest'])
        self.assertEqual(self.errors(), [])

    def test_requirement_link_change_requires_old_and_new_requirements(self):
        sync(self.root, 'FEAT-001'); self.accept()
        self.req['requirements'].append({'id': 'R-2'})
        tasks = self.tasks(); tasks[0]['requirement_ids'] = ['R-2']; self.save_tasks(tasks)
        sync(self.root, 'FEAT-001')
        with self.assertRaisesRegex(ValueError, 'R-1, R-2'):
            self.accept(requirement_ids=('R-2',))
        accepted = self.accept(requirement_ids=('R-1', 'R-2'))
        self.assertEqual(accepted['review']['requirement_ids'], ['R-1', 'R-2'])

    def test_unknown_semantic_field_changes_digest(self):
        sync(self.root, 'FEAT-001'); self.accept()
        tasks = self.tasks(); tasks[0]['navigation_contract'] = 'Back returns to wallet'; self.save_tasks(tasks)
        _, changed = sync(self.root, 'FEAT-001')
        self.assertEqual(changed, ['T-1'])
        self.assertTrue(self.errors())

    def test_tampered_history_is_rejected(self):
        sync(self.root, 'FEAT-001'); self.accept()
        tasks = self.tasks(); tasks[0]['title'] = 'Changed'; self.save_tasks(tasks)
        sync(self.root, 'FEAT-001'); record = self.accept()
        record['history'][0]['review']['notes'] = 'tampered'
        self.write('task-review.json', record)
        self.assertTrue(any('invalid' in error for error in self.errors()))
        with self.assertRaisesRegex(ValueError, 'invalid or duplicate'):
            sync(self.root, 'FEAT-001')

    def test_current_review_scope_or_content_cannot_be_edited_by_hand(self):
        sync(self.root, 'FEAT-001'); record = self.accept()
        record['review']['notes'] = 'changed without a new review'
        self.write('task-review.json', record)
        self.assertTrue(any('needs reviewer' in error for error in self.errors()))

    def test_generated_view_status_and_agent_routing_are_integrated(self):
        sync(self.root, 'FEAT-001'); self.accept()
        self.run_script('render-workspace.py', self.root, 'FEAT-001')
        self.assertIn('Pending task IDs: none', (self.folder / 'task-review.md').read_text())
        self.assertIn('TASK_SEMANTICS: current', self.run_script('feature-status.py', self.root, 'FEAT-001'))
        tasks = self.tasks(); tasks[0]['description'] = 'Changed behavior'; self.save_tasks(tasks)
        sync(self.root, 'FEAT-001')
        self.assertIn('TASK_SEMANTICS: pending', self.run_script('feature-status.py', self.root, 'FEAT-001'))
        repository = Path(__file__).resolve().parents[1]
        reference = (repository / 'skills/dev/core/references/task-semantic-review.md').read_text()
        entrypoint = (repository / 'skills/dev/SKILL.md').read_text()
        self.assertIn('Progress and meaning are separate.', reference)
        self.assertIn('only their linked requirements and evidence', entrypoint)


if __name__ == '__main__':
    unittest.main()
