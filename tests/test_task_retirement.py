"""Non-delivery termination retains unresolved facts and owns only eligible cleanup."""
import copy
from datetime import datetime,timezone,timedelta
import json
import subprocess
import sys
import unittest
from unittest.mock import patch
import test_task_workflow as fixture
w=fixture.w

class TaskRetirementTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.TaskWorkflowTests(methodName='runTest');self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.reason='Synthetic owner stops this task, not delivery';self.authority='Synthetic scoped stop approval';self.at=w.now()
    def handoff(self,name='ISSUES.md'):
        f=self.f;context=w.retirement_context(f.root,f.doc(),name)
        (f.root/name).write_text('\n'.join([self.reason,self.authority,self.at,w.canonical(context).decode(),'Code remains unmerged; no failure is fixed by stopping.']))
        return name
    def retire(self,handoff=True):
        f=self.f
        return w.retire(f.root,f.ident,self.reason,self.authority,self.at,self.handoff() if handoff else None)
    def age(self):
        f=self.f;d=f.doc();d['retirement']['retired_at']=(datetime.now(timezone.utc)-timedelta(days=8)).isoformat();d['retirement']['decision_at']=d['retirement']['retired_at'];w.save(f.root,d)
    def capture_failure(self):
        return self.f.observe('C1','runtime_observation',w.now(),'Synthetic first-launch failure',['app.py'],'failed',conditions={'session':'first launch'})['fact']
    def test_retirement_never_delivers_or_resolves_and_is_idempotent(self):
        f=self.f;fid=self.capture_failure();facts=copy.deepcopy(f.doc()['facts']);retired=self.retire()
        self.assertFalse(retired['delivery_certified']);self.assertEqual(retired['unresolved']['runtime_failures'],1)
        self.assertEqual(f.doc()['facts'],facts);self.assertIn(fid,w.task_failures.pending(f.doc()));self.assertEqual(w.view(f.root,f.ident)['state'],'retired');self.assertFalse(w.view(f.root,f.ident)['eligible'])
        before=w.task_path(f.root,f.ident).read_bytes();self.assertEqual(self.retire(handoff=False),retired);self.assertEqual(before,w.task_path(f.root,f.ident).read_bytes())
        with self.assertRaisesRegex(ValueError,'TASK_RETIRED'):w.close(f.root,f.ident,[])
    def test_missing_authority_or_future_decision_refuses_without_write(self):
        f=self.f;before=w.task_path(f.root,f.ident).read_bytes()
        for reason,authority,at in [('',self.authority,self.at),(self.reason,'',self.at),(self.reason,self.authority,None)]:
            with self.assertRaisesRegex(ValueError,'RETIREMENT_DECISION_REQUIRED'):w.retire(f.root,f.ident,reason,authority,at)
        with self.assertRaisesRegex(ValueError,'FUTURE_DECISION'):w.retire(f.root,f.ident,self.reason,self.authority,(datetime.now(timezone.utc)+timedelta(days=1)).isoformat())
        self.assertEqual(before,w.task_path(f.root,f.ident).read_bytes())
    def test_code_changes_require_exact_surviving_handoff(self):
        f=self.f
        with self.assertRaisesRegex(ValueError,'RETIREMENT_HANDOFF_REQUIRED'):self.retire(False)
        (f.root/'ISSUES.md').write_text('Generic stop summary')
        with self.assertRaisesRegex(ValueError,'RETIREMENT_HANDOFF_INCOMPLETE'):w.retire(f.root,f.ident,self.reason,self.authority,self.at,'ISSUES.md')
        original=(f.root/'app.py').read_bytes();self.retire();self.assertEqual(original,(f.root/'app.py').read_bytes())
    def test_empty_draft_requires_no_permanent_issue(self):
        f=self.f;w.begin(f.root,'EMPTY','Investigate only; no code changes yet')
        # Begin after fixture changes; HEAD already contains the before version, so commit the current code first.
        f.git('add','app.py');f.git('commit','-qm','current code')
        w.begin(f.root,'CLEAN','No changes after this baseline')
        receipt=w.retire(f.root,'CLEAN',self.reason,self.authority,self.at)
        self.assertIsNone(receipt['handoff']);self.assertEqual(sum(receipt['unresolved'].values()),0)
    def test_completed_delivery_cannot_be_retired(self):
        f=self.f;f.close();before=w.task_path(f.root,f.ident).read_bytes()
        with self.assertRaisesRegex(ValueError,'TASK_ALREADY_COMPLETE'):self.retire(False)
        self.assertEqual(before,w.task_path(f.root,f.ident).read_bytes())
    def test_busy_task_refuses_and_does_not_kill_process(self):
        f=self.f;script='import sys;sys.path.insert(0,sys.argv[1]);import task_workflow as w;from pathlib import Path;w.retire(Path(sys.argv[2]),sys.argv[3],"stop","owner",w.now())'
        before=w.task_path(f.root,f.ident).read_bytes()
        with w.locked(f.root,f.ident):
            proc=subprocess.run([sys.executable,'-c',script,str(fixture.CORE),str(f.root),f.ident],capture_output=True,text=True)
        self.assertNotEqual(proc.returncode,0);self.assertIn('TASK_BUSY',proc.stderr);self.assertEqual(before,w.task_path(f.root,f.ident).read_bytes())
    def test_all_normal_writers_refuse_retired_record(self):
        f=self.f;self.capture_failure();self.retire();before=w.task_path(f.root,f.ident).read_bytes();expires=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
        calls=[lambda:f.refresh(),lambda:f.execute(),lambda:f.support(),lambda:f.observe('C1','static_analysis',w.now(),'no write',['app.py']),lambda:w.attach(f.root,f.ident,'app.py'),lambda:w.prune(f.root,f.ident,True),lambda:w.authorize(f.root,f.ident,'target','once',self.authority,self.at,expires,self.reason),lambda:w.failure_action(f.root,f.ident,next(iter(w.task_failures.pending(f.doc()))),'reopen',self.reason),lambda:w.defer_claim(f.root,f.ident,'C1',self.reason,self.authority,self.at,'ISSUES.md',exclude=True),lambda:w.correct(f.root,f.ident,['C1'],self.reason,self.authority),lambda:w.review_input(f.root,f.ident,'C1')]
        for call in calls:
            with self.subTest(call=call),self.assertRaises(ValueError):call()
        self.assertEqual(before,w.task_path(f.root,f.ident).read_bytes())
    def test_open_correction_is_not_closed_and_prior_receipt_survives(self):
        f=self.f;prior=f.close();w.correct(f.root,f.ident,['C1'],'Synthetic unresolved correction',self.authority);self.retire();d=f.doc()
        self.assertEqual(d['corrections'][-1]['status'],'open');self.assertEqual(d['receipt'],prior);self.assertEqual(d['retirement']['unresolved']['corrections'],1)
        self.age();w.cleanup(f.root,f.ident,True);d=f.doc();self.assertEqual(d['corrections'][-1]['status'],'open');self.assertEqual(d['corrections'][-1]['prior_receipt'],prior);self.assertEqual(d['receipt'],prior)
    def test_retention_starts_at_actual_retirement_not_old_decision(self):
        f=self.f;self.at=(datetime.now(timezone.utc)-timedelta(days=100)).isoformat();receipt=self.retire();self.assertGreater(w.instant(receipt['retired_at']),w.instant(self.at))
        with self.assertRaisesRegex(ValueError,'RETENTION_NOT_ELAPSED'):w.cleanup(f.root,f.ident,True)
    def test_handoff_lost_or_modified_blocks_cleanup_and_forget(self):
        f=self.f;self.retire();self.age();original=(f.root/'ISSUES.md').read_bytes();before=w.task_path(f.root,f.ident).read_bytes()
        for value in (b'changed',None):
            path=f.root/'ISSUES.md'
            if value is None:path.unlink()
            else:path.write_bytes(value)
            with self.assertRaisesRegex(ValueError,'RETIREMENT_HANDOFF_UNAVAILABLE'):w.cleanup(f.root,f.ident,True,forget=True)
            self.assertEqual(before,w.task_path(f.root,f.ident).read_bytes());path.write_bytes(original)
    def test_expired_compaction_is_idempotent_and_preserves_pending_counts(self):
        f=self.f;self.capture_failure();f.execute();self.retire();self.age();self.assertTrue(w.cleanup(f.root,f.ident,True)['changed']);before=w.task_path(f.root,f.ident).read_bytes()
        self.assertFalse(w.cleanup(f.root,f.ident,True)['changed']);self.assertEqual(before,w.task_path(f.root,f.ident).read_bytes());self.assertNotIn('facts',f.doc());self.assertEqual(f.doc()['retirement']['unresolved']['runtime_failures'],1)
        status=w.storage(f.root);self.assertEqual(status['counts']['complete'],0);self.assertEqual(status['counts']['retired'],1);self.assertEqual(status['counts']['pending_runtime_failure'],1)
    def test_cleanup_preserves_originals_code_other_tasks_and_unknown_outputs(self):
        f=self.f;w.attach(f.root,f.ident,'app.py');f.execute();self.retire();self.age();folder=f.root/'.featrace/artifacts'/f.ident;(folder/'unknown.txt').write_text('keep')
        w.begin(f.root,'OTHER','Unrelated current task');other=w.task_path(f.root,'OTHER').read_bytes()
        with self.assertRaisesRegex(ValueError,'CLEANUP_UNKNOWN_ARTIFACT'):w.cleanup(f.root,f.ident,True)
        (folder/'unknown.txt').unlink();w.cleanup(f.root,f.ident,True,forget=True)
        self.assertTrue((f.root/'app.py').exists());self.assertTrue((f.root/'ISSUES.md').exists());self.assertEqual(other,w.task_path(f.root,'OTHER').read_bytes());self.assertFalse(w.task_path(f.root,f.ident).exists())
    def test_automatic_maintenance_obeys_recorded_retirement_policy(self):
        f=self.f;p=w.task_policy.load(f.root);p['cleanup']='compact';w.task_policy.prepare(f.root,p,w.git);self.retire();self.age();self.assertEqual(w.maintain(f.root)['cleaned'],1);self.assertEqual(w.maintain(f.root)['cleaned'],0)
    def test_retired_id_cannot_restart_and_new_task_does_not_resign_facts(self):
        f=self.f;fid=self.capture_failure();self.retire();before=w.task_path(f.root,f.ident).read_bytes()
        with self.assertRaisesRegex(ValueError,'TASK_EXISTS'):w.begin(f.root,f.ident,'Resume old ID')
        w.begin(f.root,'NEW','Explicit new request; consult surviving ISSUES.md');new=w.load(f.root,'NEW');self.assertEqual(new['facts'],{});self.assertNotIn(fid,new['facts']);self.assertEqual(before,w.task_path(f.root,f.ident).read_bytes())
    def test_query_does_not_count_retirement_as_delivery_or_offer_execution(self):
        f=self.f;self.retire();before=w.task_path(f.root,f.ident).read_bytes();listing=w.task_list(f.root)['items'][0];self.assertEqual(listing['recorded_state'],'retired');self.assertFalse(listing['delivery_certified']);self.assertEqual(w.check_diagnostic(f.root,f.doc(),f.plan['checks'][0])['new_execution_permission'],'task_retired');self.assertEqual(before,w.task_path(f.root,f.ident).read_bytes())
    def test_draft_handoff_does_not_include_its_own_hash(self):
        f=self.f;w.begin(f.root,'DRAFT','No plan yet; investigate current changes');name='ISSUES.md';context=w.retirement_context(f.root,w.load(f.root,'DRAFT'),name)
        self.assertNotIn(name,context['code']['paths']);(f.root/name).write_text('\n'.join([self.reason,self.authority,self.at,w.canonical(context).decode()]))
        self.assertFalse(w.retire(f.root,'DRAFT',self.reason,self.authority,self.at,name)['delivery_certified'])
    def test_handoff_cannot_replace_task_business_input(self):
        f=self.f
        with self.assertRaisesRegex(ValueError,'RETIREMENT_HANDOFF_IS_TASK_INPUT'):w.retire(f.root,f.ident,self.reason,self.authority,self.at,'app.py')
    def test_retirement_requires_well_formed_non_delivery_receipt(self):
        f=self.f;self.retire();d=f.doc();d['retirement']['delivery_certified']=True
        with self.assertRaisesRegex(ValueError,'RETIREMENT_CONTRACT_INVALID'):w.save(f.root,d)

    def test_unavailable_observation_and_partial_judgment_are_handed_off(self):
        f=self.f;f.observe('C1','runtime_observation',w.now(),'Synthetic evidence unavailable',['app.py'],'unavailable',conditions={'session':'unknown outcome'})
        f.assess('C1','partial','Specific expected rendering is not established')
        context=w.retirement_context(f.root,f.doc(),'ISSUES.md');self.assertIn('C1',context['observations']);self.assertIn('C1',context['assessments'])
        receipt=self.retire();self.assertEqual(receipt['unresolved']['observations'],1);self.assertEqual(receipt['unresolved']['assessments'],1)
    def test_unknown_and_product_deferral_survive_in_retirement_handoff(self):
        f=self.f;f.plan['unknowns']=['Synthetic source not yet available'];f.refresh();context=w.retirement_context(f.root,f.doc(),'ISSUES.md');self.assertEqual(context['unknowns'],f.plan['unknowns']);receipt=self.retire();self.assertEqual(receipt['unresolved']['unknowns'],1)

    def test_failed_command_handoff_survives_compaction_with_command_and_target(self):
        f=self.f;(f.root/'check.py').write_text('raise SystemExit(4)\n');f.refresh();result=f.execute();self.assertEqual(result['status'],'failed')
        context=w.retirement_context(f.root,f.doc(),'ISSUES.md');check=context['checks']['target'];self.assertEqual(check['definition']['argv'],f.plan['checks'][0]['argv']);self.assertEqual(check['definition']['environment'],f.plan['checks'][0]['environment']);self.assertEqual(check['fact']['id'],result['execution'])
        self.retire();self.age();w.cleanup(f.root,f.ident,True);self.assertIn(w.canonical(context).decode(),(f.root/'ISSUES.md').read_text());self.assertNotIn('plan',f.doc());self.assertEqual(f.doc()['retirement']['unresolved']['checks'],1)
    def test_product_exclusion_is_not_lost_when_stopping(self):
        f=self.f;reason='Synthetic owner excludes this promise';authority='Synthetic explicit exclusion';issue='EXISTING-ISSUE.md'
        (f.root/issue).write_text(reason+'\n'+authority+'\n'+f.plan['criteria'][0]['expected']+'\n'+w.canonical(w.failure_handoff(f.doc(),'C1')).decode())
        w.defer_claim(f.root,f.ident,'C1',reason,authority,w.now(),issue,exclude=True)
        context=w.retirement_context(f.root,f.doc(),'ISSUES.md');self.assertEqual(context['deferrals']['C1']['authority'],authority);self.assertEqual(self.retire()['unresolved']['deferrals'],1)

    def test_old_failure_keeps_its_own_command_and_target_after_replanning(self):
        f=self.f;(f.root/'check.py').write_text('raise SystemExit(4)\n');f.refresh();f.execute();original=copy.deepcopy(f.execution())
        f.plan['checks'][0]['argv']=[sys.executable,'check.py','new-argument'];f.plan['checks'][0]['environment']['target']='another target';f.refresh()
        context=w.retirement_context(f.root,f.doc(),'ISSUES.md')['checks']['target']
        self.assertEqual(context['definition']['argv'],original['execution_definition']['argv']);self.assertEqual(context['definition']['environment'],original['environment']);self.assertEqual(context['fact']['definition_digest'],original['definition_digest'])
    def test_missing_original_definition_is_unknown_not_current_plan(self):
        f=self.f;(f.root/'check.py').write_text('raise SystemExit(4)\n');f.refresh();f.execute();d=f.doc();d['facts'][d['executions']['target']].pop('execution_definition');w.save(f.root,d)
        f.plan['checks'][0]['environment']['target']='new target';f.refresh();context=w.retirement_context(f.root,f.doc(),'ISSUES.md')['checks']['target']
        self.assertIsNone(context['definition']);self.assertEqual(context['definition_status'],'not_retained');self.assertEqual(context['fact']['environment']['target'],'synthetic local Python')
