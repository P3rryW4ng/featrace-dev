"""Do not rewrite already compacted tasks; preserve cleanup ownership guards."""
import unittest
from unittest.mock import patch
import test_task_workflow as fixture
w=fixture.w
class MaintenanceIdempotenceTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.TaskWorkflowTests(methodName='runTest');self.f.setUp();self.addCleanup(self.f.doCleanups)
        f=self.f;p=w.task_policy.load(f.root);p['cleanup']='compact';w.task_policy.prepare(f.root,p,w.git);f.refresh();f.execute();f.support();w.close(f.root,f.ident,[]);f.age()
    def test_second_compact_is_read_only_and_maintenance_counts_real_changes(self):
        f=self.f;self.assertEqual(w.maintain(f.root)['cleaned'],1);before=w.task_path(f.root,f.ident).read_bytes()
        with patch.object(w,'save',wraps=w.save) as save:
            preview=w.cleanup(f.root,f.ident);again=w.cleanup(f.root,f.ident,True);maintenance=w.maintain(f.root)
            save.assert_not_called()
        self.assertFalse(preview['changes_required']);self.assertFalse(again['changed']);self.assertEqual(maintenance['cleaned'],0);self.assertEqual(maintenance['processed'],1);self.assertEqual(before,w.task_path(f.root,f.ident).read_bytes())
    def test_compacted_task_can_still_be_explicitly_forgotten(self):
        f=self.f;w.cleanup(f.root,f.ident,True);result=w.cleanup(f.root,f.ident,True,forget=True)
        self.assertTrue(result['changed']);self.assertFalse(w.task_path(f.root,f.ident).exists());self.assertTrue((f.root/'app.py').exists())
    def test_interrupted_compaction_still_finishes_owned_outputs(self):
        f=self.f;original=w.Path.unlink
        def interrupt(path,*a,**kw):
            if path.suffix=='.log':raise OSError('Synthetic interruption before owned log deletion')
            return original(path,*a,**kw)
        with patch.object(w.Path,'unlink',interrupt):
            with self.assertRaisesRegex(OSError,'Synthetic interruption'):w.cleanup(f.root,f.ident,True)
        self.assertNotIn('facts',f.doc());self.assertTrue(list((f.root/'.featrace/artifacts'/f.ident).glob('*.log')))
        result=w.cleanup(f.root,f.ident,True);self.assertTrue(result['changed']);self.assertFalse((f.root/'.featrace/artifacts'/f.ident).exists());self.assertFalse(w.cleanup(f.root,f.ident,True)['changed'])
    def test_compacted_record_does_not_bypass_unknown_file_checks(self):
        f=self.f;w.cleanup(f.root,f.ident,True);folder=f.root/'.featrace/artifacts'/f.ident;folder.mkdir();unknown=folder/'keep.txt';unknown.write_text('Do not delete')
        before=w.task_path(f.root,f.ident).read_bytes()
        with self.assertRaisesRegex(ValueError,'CLEANUP_UNKNOWN_ARTIFACT'):w.cleanup(f.root,f.ident,True)
        self.assertEqual(before,w.task_path(f.root,f.ident).read_bytes());self.assertTrue(unknown.exists())
