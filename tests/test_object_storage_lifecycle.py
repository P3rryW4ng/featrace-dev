"""Contract-9 storage lifecycle, capacity and managed-note regressions."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import test_task_workflow as fixture
w=fixture.w
s=w.task_storage

class ObjectStorageTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.TaskWorkflowTests(methodName='runTest');self.f.setUp()
        self.addCleanup(self.f.doCleanups);self.r=self.f.root;self.id=self.f.ident
        self.path=w.task_path(self.r,self.id)
        doc=self.f.doc();doc['plan']['reason']='fixture reason '*100;w.save(self.r,doc)
    def test_objects_missing_tampered_and_symlink_are_not_trusted(self):
        env=json.loads(self.path.read_bytes());key=next(iter(env['objects']))
        p=s.directory(self.path,w.fail)/(key+'.json');original=p.read_bytes()
        p.unlink()
        with self.assertRaisesRegex(ValueError,'OBJECT_UNAVAILABLE'):self.f.doc()
        p.write_bytes(b'x'*len(original))
        with self.assertRaisesRegex(ValueError,'OBJECT_CHANGED'):self.f.doc()
        p.unlink();target=self.r/'elsewhere';target.write_bytes(original);p.symlink_to(target)
        with self.assertRaisesRegex(ValueError,'OBJECT_UNAVAILABLE'):self.f.doc()
    def test_interrupted_publication_retains_old_index_and_retry_works(self):
        before=self.path.read_bytes();doc=self.f.doc();doc['plan']['reason']='new '*1000
        original=s.write
        def interrupt(p,data):
            if p==self.path:raise OSError('interrupted index commit')
            original(p,data)
        with patch.object(s,'write',side_effect=interrupt):
            with self.assertRaises(OSError):w.save(self.r,doc)
        self.assertEqual(self.path.read_bytes(),before)
        self.assertNotEqual(self.f.doc()['plan']['reason'],doc['plan']['reason'])
        w.save(self.r,doc);self.assertEqual(self.f.doc()['plan']['reason'],doc['plan']['reason'])
    def test_metadata_disk_limit_prevents_command(self):
        with patch.object(s,'MAX_STORED',1):
            with self.assertRaisesRegex(ValueError,'TASK_STORAGE_DISK_LIMIT'):self.f.execute()
        self.assertFalse((self.r/'run-count').exists())
    def test_large_task_supports_multiple_real_correction_cycles(self):
        self.f.execute();self.f.support();w.close(self.r,self.id,[])
        doc=self.f.doc()
        # Many individually distinct bounded facts; no real project data.
        for i in range(40):
            key='fixture-'+str(i)
            doc['facts'][key]={'id':key,'kind':'static_analysis','criterion':'C1',
                              'status':'passed','actual':str(i)+' x'*3000}
        w.save(self.r,doc)
        self.assertGreater(len(w.canonical(self.f.doc())),240000)
        self.assertLess(self.path.stat().st_size,65536)
        for i in range(3):
            w.correct(self.r,self.id,['C1'],'specific correction '+str(i),'fixture')
            self.f.support();w.close(self.r,self.id,[])
        self.assertEqual(len(self.f.doc()['corrections']),3)
        self.assertEqual(len(self.f.doc()['facts']),41)
        self.assertEqual((self.r/'run-count').read_text(),'1')
    def test_static_note_is_managed_and_survives_deleted_original(self):
        note=self.r/'.featrace/scratch'/self.id/'proof.md';note.parent.mkdir(parents=True)
        note.write_text('Inspected exact local rendering and unchanged callbacks.')
        item=w.observe(self.r,self.id,'C1','static_analysis',w.now(),'selected proof',[str(note.relative_to(self.r))])
        fact=self.f.doc()['facts'][item['fact']];managed=next(iter(fact['evidence']))
        self.assertTrue(managed.startswith('.featrace/artifacts/'))
        note.unlink()
        self.f.execute()
        self.f.assess('C1','supported','proof',fact_ids=[item['fact']])
        w.prune(self.r,self.id,True)
        w.close(self.r,self.id,[])
        self.assertTrue((self.r/managed).exists())
        self.assertEqual(w.view(self.r,self.id)['state'],'complete')
    def test_invalid_observation_does_not_publish_attachment(self):
        note=self.r/'note.md';note.write_text('note')
        before=self.path.read_bytes()
        with self.assertRaisesRegex(ValueError,'CONDITIONS_REQUIRE_RUNTIME'):
            w.observe(self.r,self.id,'C1','static_analysis',w.now(),'proof',['note.md'],conditions={})
        self.assertEqual(before,self.path.read_bytes())
        self.assertFalse(list((self.r/'.featrace/artifacts'/self.id).glob('*')))
    def test_known_obsolete_objects_collected_unknown_files_preserved(self):
        folder=s.directory(self.path,w.fail);old=set(folder.iterdir())
        unknown=folder/'user-note.txt';unknown.write_text('do not remove')
        doc=self.f.doc();doc['plan']['reason']='replacement '*300;w.save(self.r,doc)
        current=set(json.loads(self.path.read_bytes())['objects'])
        for p in old:
            self.assertEqual(p.exists(),p.stem in current)
        self.assertEqual(unknown.read_text(),'do not remove')
    def test_contract8_is_refused_without_mutation(self):
        env=json.loads(self.path.read_bytes());env['task_contract']=8
        self.path.write_text(json.dumps(env));before=self.path.read_bytes()
        with self.assertRaisesRegex(ValueError,'PINNED_TOOL'):self.f.doc()
        self.assertEqual(before,self.path.read_bytes())

    def test_repeated_note_registration_reuses_one_intact_copy(self):
        note=self.r/'analysis.md';note.write_text('causal reasoning')
        first=w.observe(self.r,self.id,'C1','static_analysis',w.now(),'proof',['analysis.md'])
        second=w.observe(self.r,self.id,'C1','static_analysis',w.now(),'proof',['analysis.md'])
        doc=self.f.doc()
        self.assertEqual(doc['facts'][first['fact']]['evidence'],doc['facts'][second['fact']]['evidence'])
        self.assertEqual(len(doc['attachments']),1)
    def test_expanded_limit_does_not_publish_partial_state(self):
        before=self.path.read_bytes();doc=self.f.doc()
        doc['plan']['reason']='x'*(s.MAX_EXPANDED+1)
        with self.assertRaisesRegex(ValueError,'TASK_SIZE_LIMIT_EXPANDED'):w.save(self.r,doc)
        self.assertEqual(before,self.path.read_bytes())
    def test_object_count_limit_is_separate_from_index_size(self):
        doc={'task_contract':9,'facts':{str(i):{'body':str(i)+'x'*1400} for i in range(12)}}
        with patch.object(s,'MAX_OBJECTS',5):
            with self.assertRaisesRegex(ValueError,'TASK_STORAGE_OBJECT_LIMIT'):s.prepare(doc,w.fail)
    def test_cleanup_reclaims_owned_metadata_and_keeps_unknown(self):
        from datetime import datetime,timezone,timedelta
        self.f.execute();self.f.support();w.close(self.r,self.id,[])
        doc=self.f.doc();doc['receipt']['completed_at']=(datetime.now(timezone.utc)-timedelta(days=9)).isoformat()
        w.save(self.r,doc);folder=s.directory(self.path,w.fail)
        unknown=folder/'unpublished.txt';unknown.write_text('preserve')
        w.cleanup(self.r,self.id,True)
        self.assertEqual(self.f.doc()['state'],'complete')
        refs=set(json.loads(self.path.read_bytes())['objects'])
        self.assertEqual({p.stem for p in folder.glob('*.json')},refs)
        self.assertTrue(unknown.exists())
    def test_observation_keeps_live_source_identity_when_code_is_evidence(self):
        item=w.observe(self.r,self.id,'C1','static_analysis',w.now(),'inspected source',['app.py'])
        self.assertEqual(list(self.f.doc()['facts'][item['fact']]['evidence']),['app.py'])
        (self.r/'app.py').write_text('changed=1')
        self.assertFalse(w.fact_available(self.r,self.f.doc(),self.f.plan['criteria'][0],self.f.doc()['facts'][item['fact']]))

    def test_input_change_during_note_capture_does_not_sign_new_inputs(self):
        from contextlib import contextmanager
        note=self.r/'note.md';note.write_text('original inspected inputs')
        before=self.path.read_bytes();original=w.staged_attachment
        @contextmanager
        def moving(*args,**kwargs):
            with original(*args,**kwargs) as asset:
                (self.r/'app.py').write_text('uninspected change')
                yield asset
        with patch.object(w,'staged_attachment',moving):
            with self.assertRaisesRegex(ValueError,'INPUT_MOVED'):
                w.observe(self.r,self.id,'C1','static_analysis',w.now(),'proof',['note.md'])
        self.assertEqual(before,self.path.read_bytes())
        self.assertFalse(list((self.r/'.featrace/artifacts'/self.id).glob('*')))
