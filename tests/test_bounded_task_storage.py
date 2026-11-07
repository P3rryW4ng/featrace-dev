"""Contract 8 encoding and ownership counterexamples on synthetic tasks."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import test_task_workflow as fixture

w = fixture.w
storage = w.task_storage


class EncodingTests(unittest.TestCase):
    def envelope(self):
        definition={'argv':['x'*1600]}
        doc={'task_contract':8,'facts':{'a':{'execution_definition':definition},
                                       'b':{'execution_definition':definition}}}
        return doc,json.loads(storage.encode(doc,w.fail))

    def rehash(self,envelope):
        envelope['storage_checksum']=storage.digest({k:v for k,v in envelope.items() if k!='storage_checksum'})

    def test_shared_blocks_are_lossless_and_do_not_alias(self):
        doc,envelope=self.envelope()
        self.assertEqual(len(envelope['blocks']),1)
        restored=storage.decode(envelope,w.fail)
        self.assertEqual(restored,doc)
        restored['facts']['a']['execution_definition']['argv'].append('new')
        self.assertEqual(restored['facts']['b'],doc['facts']['b'])

    def test_missing_corrupted_or_misplaced_reference_refuses(self):
        _,envelope=self.envelope()
        for kind in ('missing','corrupt','misplaced','unused'):
            with self.subTest(kind=kind):
                invalid=copy.deepcopy(envelope)
                key=next(iter(invalid['blocks']))
                if kind=='missing':invalid['blocks'].clear()
                elif kind=='corrupt':invalid['blocks'][key]['argv']=['wrong']
                elif kind=='misplaced':invalid['task']['request']={'$block':key}
                else:invalid['task']['facts']['b']={}
                self.rehash(invalid)
                with self.assertRaisesRegex(ValueError,'TASK_STORAGE_INVALID'):storage.decode(invalid,w.fail)

    def test_expansion_limit_before_materializing_many_references(self):
        _,envelope=self.envelope()
        with patch.object(storage,'MAX_EXPANDED',3000):
            with self.assertRaisesRegex(ValueError,'TASK_SIZE_LIMIT_EXPANDED'):storage.decode(envelope,w.fail)


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.TaskWorkflowTests(methodName='runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.r=self.f.root

    def test_storage_source_only_change_does_not_run_command_again(self):
        first=self.f.execute()
        source=self.r/'codec.py'
        source.write_text(Path(storage.__file__).read_text()+'\n# Different storage bytes\n')
        with patch.object(storage,'__file__',str(source)):
            self.assertTrue(self.f.execute()['reused'])
            self.assertNotEqual(w.task_execution.producer(w.__file__)['storage_sha256'],
                                self.f.execution()['producer']['storage_sha256'])
        self.assertEqual((self.r/'run-count').read_text(),'1')
        self.assertEqual(first['execution'],self.f.execution()['id'])

    def test_atomic_write_failure_preserves_record(self):
        path=w.task_path(self.r,self.f.ident);before=path.read_bytes()
        doc=self.f.doc();doc['request']='new'
        with patch.object(storage.os,'replace',side_effect=OSError('synthetic')):
            with self.assertRaises(OSError):w.save(self.r,doc)
        self.assertEqual(path.read_bytes(),before)
        self.assertFalse(list(path.parent.glob('.write-*')))

    def proof(self):
        f=self.f
        f.plan['review']={'independent':True,'criteria':['C1'],'reason':'Scoped fixture review'}
        f.refresh();f.execute()
        proof=w.review_input(self.r,f.ident,'C1')
        proof.update(verdict='supported',fresh_context=True,host='fixture',context_id='reviewer',
                     reviewer='fixture',reason='Fixture verdict')
        p=self.r/'.featrace/review.json';p.write_text(json.dumps(proof))
        return p,proof

    def test_managed_proof_survives_source_and_prune_keeps_prior_correction(self):
        p,proof=self.proof();f=self.f
        w.assess(self.r,f.ident,'C1','supported','fixture',True,'.featrace/review.json',proof['facts'])
        previous=f.doc()['assessments']['C1']['provenance']
        p.unlink()
        self.assertTrue(w.view(self.r,f.ident)['eligible'])
        w.close(self.r,f.ident,[])
        w.correct(self.r,f.ident,['C1'],'Scope correction','fixture')
        w.prune(self.r,f.ident,True)
        self.assertTrue((self.r/previous['path']).exists())
        proof['context_id']='verified-host-context'
        proof['correction']={'original':previous,'authority':'fixture','host_basis':'synthetic host trace'}
        p.write_text(json.dumps(proof))
        w.assess(self.r,f.ident,'C1','supported','fixture',True,'.featrace/review.json',proof['facts'])
        self.assertEqual(f.doc()['assessments']['C1']['provenance']['issuer'],'coordinator_correction')
        self.assertTrue(w.view(self.r,f.ident)['eligible'])
        (self.r/previous['path']).write_text('changed')
        self.assertFalse(w.view(self.r,f.ident)['eligible'])

    def test_invalid_proof_and_full_attachment_budget_leave_no_verdict(self):
        p,proof=self.proof();f=self.f
        p.write_text(json.dumps({**proof,'facts':[]}))
        before=w.task_path(self.r,f.ident).read_bytes()
        with self.assertRaisesRegex(ValueError,'REVIEW_PROVENANCE_INVALID'):
            w.assess(self.r,f.ident,'C1','supported','fixture',True,'.featrace/review.json',proof['facts'])
        self.assertEqual(w.task_path(self.r,f.ident).read_bytes(),before)
        self.assertEqual(len(f.doc().get('attachments',{})),0)
        self.assertFalse(list((self.r/'.featrace/artifacts'/f.ident).glob('*.json')))
        for _ in range(32):w.attach(self.r,f.ident,'app.py')
        p.write_text(json.dumps(proof))
        with self.assertRaisesRegex(ValueError,'ATTACHMENT_COUNT_LIMIT'):
            w.assess(self.r,f.ident,'C1','supported','fixture',True,'.featrace/review.json',proof['facts'])
        self.assertNotIn('C1',f.doc()['assessments'])
