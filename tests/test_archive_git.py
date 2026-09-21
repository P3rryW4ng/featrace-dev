import unittest
import test_impact
from archive_git import report


class ArchiveGitTests(unittest.TestCase):
    write = test_impact.ImpactTests.write
    save = test_impact.ImpactTests.save
    git = test_impact.ImpactTests.git

    def setUp(self):
        test_impact.ImpactTests.setUp(self)

    def test_untracked_records_and_sources_excluded_without_mutation(self):
        before = self.git('status', '--porcelain')
        result = report(self.root, 'FEAT-001', [])
        self.assertEqual(result['state'], 'needs_git_review')
        self.assertTrue(any(f['path'].endswith('requirements.json') and f['state']=='untracked' for f in result['files']))
        self.assertFalse(any('/sources/' in f['path'] for f in result['files']))
        self.assertEqual(before, self.git('status', '--porcelain'))
        self.assertFalse(result['remote_tracking']['network_checked'])

    def test_committed_then_modified_records(self):
        self.git('add', '.agent-workflow')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'records')
        self.assertEqual(report(self.root, 'FEAT-001', [])['state'], 'tracked_scope_clean')
        (self.folder / 'tasks.json').write_text('{}')
        self.assertEqual(report(self.root, 'FEAT-001', [])['files'][0]['state'], 'uncommitted')

    def test_ignored_shared_record_is_reported_not_force_added(self):
        (self.root / '.gitignore').write_text('.agent-workflow/\n')
        result = report(self.root, 'FEAT-001', [])
        self.assertTrue(any(f['state']=='ignored_by_policy' for f in result['files']))
        self.assertEqual(self.git('ls-files', '.agent-workflow'), '')
