import json
import fcntl
import signal
import subprocess
import sys
from pathlib import Path
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
        a,p=self.start();folder=self.r/a['output_directory'];lock=w.task_walkthrough.seal_lock(w,self.r,a['attempt'])
        with lock.open('a+b') as stream:
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError,'SEAL_BUSY'):self.seal(a,p)
        (folder/'escape').symlink_to(self.r/'rules.md')
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

    def test_sigkill_during_copy_releases_seal_lock_and_retry_works(self):
        a,p=self.start();core=str(Path(w.__file__).parent)
        script="import sys,os,signal;sys.path.insert(0,sys.argv[1]);import task_workflow as w;from pathlib import Path;r=Path(sys.argv[2]);w.attach=lambda *a,**k:os.kill(os.getpid(),signal.SIGKILL);w.task_walkthrough.seal(w,r,sys.argv[3],sys.argv[4],w.now(),'actual fixture rendering',[sys.argv[5]],'passed',{'case':'original'})"
        run=subprocess.run([sys.executable,'-c',script,core,str(self.r),self.f.ident,a['attempt'],p],capture_output=True)
        self.assertEqual(run.returncode,-signal.SIGKILL)
        intent=self.f.doc()['walkthroughs'][a['attempt']]['seal_intent']
        result=w.task_walkthrough.seal(w,self.r,self.f.ident,a['attempt'],intent['observed_at'],intent['actual'],[p],'passed',intent['conditions'])
        self.assertIn(result['fact'],self.f.doc()['facts'])

    def test_unknown_empty_directory_is_not_deleted(self):
        a,p=self.start();result=self.seal(a,p)
        w.assess(self.r,self.f.ident,'C1','supported','Fixture',fact_ids=[result['fact']]);w.close(self.r,self.f.ident,[])
        d=self.f.doc();d['receipt']['completed_at']=(datetime.now(timezone.utc)-timedelta(days=8)).isoformat();w.save(self.r,d)
        extra=self.r/a['output_directory']/'unknown';extra.mkdir()
        with self.assertRaisesRegex(ValueError,'WALK_OUTPUT_CHANGED'):w.cleanup(self.r,self.f.ident,True)
        self.assertTrue(extra.is_dir());self.assertTrue((self.r/p).exists())

    def test_sealed_retry_rejects_changed_conditions_or_evidence(self):
        a,p=self.start();self.seal(a,p)
        intent=self.f.doc()['walkthroughs'][a['attempt']]['seal_intent']
        for evidence,conditions in [([p],{'case':'other'}),(['other.txt'],intent['conditions'])]:
            with self.assertRaisesRegex(ValueError,'WALK_ALREADY_SEALED'):
                w.task_walkthrough.seal(w,self.r,self.f.ident,a['attempt'],intent['observed_at'],intent['actual'],evidence,'passed',conditions)

    def historical(self,a,p,at,status='failed',basis='Fixture original capture log',conditions=None):
        return w.task_walkthrough.seal(w,self.r,self.f.ident,a['attempt'],at,'Original observed result',
                                      [p],status,conditions or {'case':'original'},True,basis)

    def test_historical_failure_survives_code_drift_and_a_different_control(self):
        a,p=self.start();at=w.now()
        original=self.f.doc()['walkthroughs'][a['attempt']]
        (self.r/'app.py').write_text('repair');self.f.refresh()
        with self.assertRaisesRegex(ValueError,'HISTORICAL_PASS_REFUSED'):self.historical(a,p,at,'passed')
        failed=self.historical(a,p,at)['fact']
        fact=self.f.doc()['facts'][failed]
        self.assertEqual(fact['input_digest'],original['input_digest'])
        self.assertEqual(fact['observed_at'],at)
        self.assertNotIn('C1',self.f.doc()['observations'])
        b,q=self.start()
        control=w.task_walkthrough.seal(w,self.r,self.f.ident,b['attempt'],w.now(),'control',[q],'passed',{'case':'different'})['fact']
        self.assertIn('RUNTIME_FAILURE:'+failed,w.view(self.r,self.f.ident)['blockers'])
        with self.assertRaisesRegex(ValueError,'FAILURE_CONDITIONS_MISMATCH'):
            w.failure_action(self.r,self.f.ident,failed,'resolve','fixture',[control])
        c,r=self.start();fixed=self.seal(c,r)['fact']
        w.failure_action(self.r,self.f.ident,failed,'resolve','Targeted runtime fixture',[fixed])
        self.assertNotIn(failed,w.task_failures.pending(self.f.doc()))

    def test_missing_capture_basis_keeps_discovery_and_original_output(self):
        a,p=self.start();at=w.now()
        (self.r/'app.py').write_text('repair');self.f.refresh()
        out=self.historical(a,p,None,basis=None)
        self.assertEqual(out['state'],'discovery')
        self.assertIsNone(out['fact'])
        self.assertFalse(self.f.doc()['facts'])
        self.assertIn('WALK_UNSEALED:'+a['attempt'],w.view(self.r,self.f.ident)['blockers'])
        self.assertEqual((self.r/p).read_text(),'observed output')
        with self.assertRaisesRegex(ValueError,'WALK_NEGATIVE_PENDING'):self.seal(a,p)
        with self.assertRaisesRegex(ValueError,'WALK_DISCOVERY_INTENT_CHANGED'):self.historical(a,p,at,'unavailable')
        sealed=self.historical(a,p,at)
        self.assertTrue(sealed['historical_negative'])
        self.assertTrue(self.historical(a,p,at)['reused'])

    def test_removed_criterion_does_not_discard_its_historical_failure(self):
        a,p=self.start();at=w.now()
        self.f.plan['criteria'][0]['id']='C2';self.f.refresh()
        failed=self.historical(a,p,at)['fact']
        self.assertEqual(self.f.doc()['facts'][failed]['criterion'],'C1')
        self.assertIn('RUNTIME_FAILURE:'+failed,w.view(self.r,self.f.ident)['blockers'])

    def test_historical_unavailable_retry_preserves_copies_and_original(self):
        a,p=self.start();at=w.now()
        (self.r/'app.py').write_text('repair');self.f.refresh()
        with patch.object(w,'MAX_FACTS',0):
            with self.assertRaisesRegex(ValueError,'FACT_LIMIT'):self.historical(a,p,at,'unavailable')
        self.assertEqual(len(self.f.doc()['attachments']),1)
        w.prune(self.r,self.f.ident,True)
        self.assertEqual(len(self.f.doc()['attachments']),1)
        fact=self.historical(a,p,at,'unavailable')['fact']
        self.assertEqual(self.f.doc()['facts'][fact]['status'],'unavailable')
        self.assertEqual(len(self.f.doc()['attachments']),1)
        self.assertTrue((self.r/p).exists())
