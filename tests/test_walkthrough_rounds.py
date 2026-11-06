import json
import unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
import test_task_workflow as fixture
w=fixture.w

class WalkthroughTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.TaskWorkflowTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.r=self.f.root;self.f.plan['checks']=[];self.f.plan['criteria'][0]['proof']={'any_of':[['runtime_observation']],'reason':'Actual fixture'}
        self.f.refresh()

    def start(self):
        a=w.task_walkthrough.start(w,self.r,self.f.ident,'C1','fixture device original artifact')
        p=a['output_directory']+'/view.txt';(self.r/p).write_text('observed output')
        return a,p

    def seal(self,a,p,status='passed'):
        return w.task_walkthrough.seal(w,self.r,self.f.ident,a['attempt'],w.now(),'actual fixture rendering',[p],status,{'case':'original'})

    def test_new_round_does_not_overwrite_and_open_blocks(self):
        a,p=self.start();b,q=self.start()
        self.assertNotEqual(p,q);self.assertEqual((self.r/p).read_text(),'observed output')
        self.assertFalse(w.view(self.r,self.f.ident)['eligible'])
        self.assertTrue(any(x.startswith('WALK_UNSEALED') for x in w.view(self.r,self.f.ident)['blockers']))

    def test_failed_round_survives_later_control_pass(self):
        a,p=self.start();failed=self.seal(a,p,'failed')['fact']
        b,q=self.start();self.seal(b,q)
        self.assertIn(failed,w.task_failures.pending(self.f.doc()))
        self.assertTrue((self.r/p).exists())
        self.assertFalse(w.view(self.r,self.f.ident)['eligible'])

    def test_source_drift_refuses_without_deleting_output(self):
        a,p=self.start();(self.r/'app.py').write_text('changed');self.f.refresh()
        with self.assertRaisesRegex(ValueError,'WALK_INPUT_CHANGED'):self.seal(a,p)
        self.assertTrue((self.r/p).exists())

    def test_copy_interruption_leaves_unsealed_and_retries_without_duplicates(self):
        a,p=self.start()
        with patch.object(w,'attach',side_effect=OSError('synthetic')):
            with self.assertRaises(OSError):self.seal(a,p)
        self.assertEqual(self.f.doc()['walkthroughs'][a['attempt']]['state'],'sealing')
        intent=self.f.doc()['walkthroughs'][a['attempt']]['seal_intent']
        result=w.task_walkthrough.seal(w,self.r,self.f.ident,a['attempt'],intent['observed_at'],intent['actual'],[p],'passed',{'case':'original'})
        self.assertIn(result['fact'],self.f.doc()['facts'])
        self.assertEqual(len(self.f.doc()['attachments']),1)

    def test_modified_or_external_output_refuses(self):
        a,p=self.start()
        with self.assertRaisesRegex(ValueError,'OUTSIDE_ROUND'):self.seal(a,'app.py')
        self.assertTrue((self.r/p).exists())

    def test_cleanup_owned_rounds_and_reject_modified_files(self):
        a,p=self.start();result=self.seal(a,p)
        w.assess(self.r,self.f.ident,'C1','supported','Actual round',fact_ids=[result['fact']]);w.close(self.r,self.f.ident,[])
        d=self.f.doc();d['receipt']['completed_at']=(datetime.now(timezone.utc)-timedelta(days=8)).isoformat();w.save(self.r,d)
        (self.r/p).write_text('tampered')
        with self.assertRaisesRegex(ValueError,'WALK_OUTPUT_CHANGED'):w.cleanup(self.r,self.f.ident,True)
        (self.r/p).write_text('observed output');w.cleanup(self.r,self.f.ident,True)
        self.assertFalse((self.r/p).exists())

    def test_fact_budget_preserves_open_round(self):
        a,p=self.start()
        with patch.object(w,'MAX_FACTS',0):
            with self.assertRaisesRegex(ValueError,'FACT_LIMIT'):self.seal(a,p)
        self.assertTrue((self.r/p).exists())
        self.assertNotEqual(self.f.doc()['walkthroughs'][a['attempt']]['state'],'sealed')

    def test_symlink_and_concurrent_seal_refuse(self):
        a,p=self.start();folder=self.r/a['output_directory'];(folder/'.seal-lock').write_text('other writer')
        with self.assertRaisesRegex(ValueError,'SEAL_BUSY'):self.seal(a,p)
        (folder/'.seal-lock').unlink();(folder/'escape').symlink_to(self.r/'rules.md')
        with self.assertRaisesRegex(ValueError,'SYMLINK'):self.seal(a,p)

    def test_retirement_hands_off_unsealed_round_before_cleanup(self):
        a,p=self.start();context=w.retirement_context(self.r,self.f.doc(),'ISSUES.md')
        at=w.now()
        (self.r/'ISSUES.md').write_text('Stop synthetic work\nExplicit fixture authority\n'+at+'\n'+w.canonical(context).decode())
        receipt=w.retire(self.r,self.f.ident,'Stop synthetic work','Explicit fixture authority',at,'ISSUES.md')
        self.assertEqual(receipt['unresolved']['walkthroughs'],1)
        d=self.f.doc();self.assertEqual(d['walkthroughs'][a['attempt']]['state'],'abandoned')
        d['retirement']['retired_at']=(datetime.now(timezone.utc)-timedelta(days=8)).isoformat()
        d['retirement']['decision_at']=d['retirement']['retired_at'];w.save(self.r,d)
        w.cleanup(self.r,self.f.ident,True)
        self.assertFalse((self.r/p).exists())

    def test_compacted_round_cleanup_retry_preserves_ownership(self):
        a,p=self.start();result=self.seal(a,p)
        w.assess(self.r,self.f.ident,'C1','supported','Fixture',fact_ids=[result['fact']]);w.close(self.r,self.f.ident,[])
        d=self.f.doc();d['receipt']['completed_at']=(datetime.now(timezone.utc)-timedelta(days=8)).isoformat();w.save(self.r,d)
        original=w.save;calls=[0]
        def interrupted(root,doc):
            calls[0]+=1
            if calls[0]==2:raise OSError('synthetic interruption after deletion')
            return original(root,doc)
        with patch.object(w,'save',side_effect=interrupted):
            with self.assertRaises(OSError):w.cleanup(self.r,self.f.ident,True)
        w.cleanup(self.r,self.f.ident,True)
        self.assertFalse((self.r/p).exists())
