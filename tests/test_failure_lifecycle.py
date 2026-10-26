"""Synthetic condition-specific failures, explicit disposition and scoped deferral."""
import copy
from datetime import datetime,timezone,timedelta
import unittest
import test_task_workflow as fixture
w=fixture.w


class FailureLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.TaskWorkflowTests(methodName='runTest');self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def capture(self,status,case='first launch',**kwargs):
        f=self.f
        return f.observe('C1','runtime_observation',w.now(),'Synthetic '+case,['app.py'],status,
                         conditions={'session':case},**kwargs)['fact']

    def resolve(self,fid,pid):
        f=self.f
        return w.failure_action(f.root,f.ident,fid,'resolve','Compared the actual reproduction and targeted result',[pid])

    def defer(self,exclude=True):
        f=self.f;reason='Known issue is explicitly outside this delivery';authority='Synthetic product owner decision reference'
        (f.root/'ISSUES.md').write_text(reason+'\n'+authority+'\n'+f.plan['criteria'][0]['expected']+'\n'+w.canonical(w.failure_handoff(f.doc(),'C1')).decode()+'\nStill unresolved, not a passing test.\n')
        return w.defer_claim(f.root,f.ident,'C1',reason,authority,w.now(),'ISSUES.md',exclude=exclude)

    def test_control_pass_does_not_automatically_resolve_or_certify(self):
        f=self.f;f.execute();bad=self.capture('failed');original=copy.deepcopy(f.doc()['facts'][bad])
        control=self.capture('passed','normal restart');f.support()
        self.assertIn(bad,w.task_failures.pending(f.doc()))
        self.assertNotIn('resolved_failure',f.doc()['facts'][control])
        self.assertEqual(f.doc()['facts'][bad],original)
        with self.assertRaisesRegex(ValueError,'DELIVERY_BLOCKED'):w.close(f.root,f.ident,[])

    def test_explicit_control_resolution_is_rejected(self):
        bad=self.capture('failed');control=self.capture('passed','normal restart')
        with self.assertRaisesRegex(ValueError,'FAILURE_CONDITIONS_MISMATCH'):self.resolve(bad,control)

    def test_one_of_two_failures_does_not_clear_the_other(self):
        f=self.f;f.execute();a=self.capture('failed','A');b=self.capture('failed','B')
        self.resolve(a,self.capture('passed','A'));f.support()
        self.assertEqual(set(w.task_failures.pending(f.doc())),{b})
        self.assertFalse(w.view(f.root,f.ident)['eligible'])
        self.resolve(b,self.capture('passed','B'));f.support()
        self.assertTrue(w.view(f.root,f.ident)['eligible'])

    def test_actual_code_change_can_resolve_same_conditions(self):
        f=self.f;a=self.capture('failed');old=f.doc()['facts'][a]['input_digest']
        (f.root/'app.py').write_text('label="after"\n# real synthetic repair\n');f.refresh();f.execute()
        b=self.capture('passed');self.assertNotEqual(f.doc()['facts'][b]['input_digest'],old)
        self.resolve(a,b);f.support();self.assertTrue(w.view(f.root,f.ident)['eligible'])

    def test_unknown_conditions_can_be_recorded_then_clarified_without_resigning(self):
        f=self.f;f.execute()
        a=f.observe('C1','runtime_observation',w.now(),'Failure with incomplete context',['app.py'],'failed',conditions={})['fact']
        original=copy.deepcopy(f.doc()['facts'][a]);p=self.capture('passed')
        with self.assertRaisesRegex(ValueError,'FAILURE_CONDITIONS_REQUIRED'):self.resolve(a,p)
        w.failure_action(f.root,f.ident,a,'clarify','Read original retained failure evidence',conditions={'session':'first launch'})
        self.resolve(a,p);self.assertEqual(f.doc()['facts'][a],original)
        self.assertEqual([x['action'] for x in f.doc()['failure_actions'][a]],['clarify','resolve'])

    def test_static_and_unavailable_results_never_resolve(self):
        f=self.f;a=self.capture('failed')
        b=f.observe('C1','static_analysis',w.now(),'Structural argument',['app.py'])['fact']
        with self.assertRaisesRegex(ValueError,'TARGETED_RUNTIME_PROOF_REQUIRED'):self.resolve(a,b)
        c=self.capture('unavailable')
        with self.assertRaisesRegex(ValueError,'CURRENT_FACT_REQUIRED'):self.resolve(a,c)
        self.assertIn(a,w.task_failures.pending(f.doc()))

    def test_older_observation_is_kept_but_cannot_resolve(self):
        f=self.f;earlier=w.now();a=self.capture('failed')
        b=f.observe('C1','runtime_observation',earlier,'Older actual source',['app.py'],conditions={'session':'first launch'})['fact']
        with self.assertRaisesRegex(ValueError,'PASS_PREDATES_FAILURE'):self.resolve(a,b)
        self.assertIn(b,f.doc()['facts'])

    def test_reopen_keeps_original_resolution_without_new_runtime(self):
        f=self.f;f.execute();a=self.capture('failed');p=self.capture('passed');self.resolve(a,p)
        original=copy.deepcopy(f.doc()['facts']);w.failure_action(f.root,f.ident,a,'reopen','Prior applicability judgment was wrong')
        self.assertEqual(f.doc()['facts'],original)
        self.assertEqual([x['action'] for x in f.doc()['failure_actions'][a]],['resolve','reopen'])
        self.assertIn(a,w.task_failures.pending(f.doc()))

    def test_product_deferral_is_explicit_exclusion_not_support_or_repair(self):
        f=self.f;a=self.capture('failed')
        self.defer();status=w.view(f.root,f.ident)
        self.assertTrue(status['eligible']);self.assertEqual(status['items'][0]['status'],'deferred')
        self.assertIn(a,w.task_failures.pending(f.doc()))
        with self.assertRaisesRegex(ValueError,'CLAIM_DEFERRED_NOT_SUPPORTED'):f.support()
        receipt=w.close(f.root,f.ident,[])
        self.assertEqual(receipt['supported_criteria'],0)
        self.assertEqual(receipt['deferrals']['C1']['unresolved_failures'],[a])
        self.assertEqual(receipt['outcome'],'scoped_delivery_with_deferrals')

    def test_delay_that_remains_in_delivery_does_not_bypass(self):
        f=self.f;a=self.capture('failed')
        with self.assertRaisesRegex(ValueError,'EXPLICIT_DELIVERY_EXCLUSION_REQUIRED'):self.defer(exclude=False)
        self.assertFalse(w.view(f.root,f.ident)['eligible'])
        self.assertIn(a,w.task_failures.pending(f.doc()))

    def test_partial_deferral_does_not_waive_shared_required_check(self):
        f=self.f
        f.plan['scope'].append('other.py');(f.root/'other.py').write_text('other=1')
        f.plan['criteria'].append({'id':'C2','expected':'Other required behavior','kind':'changed','inputs':['other.py']})
        f.plan['checks'][0]['covers'].append('C2');f.plan['checks'][0]['inputs'].append('other.py');f.refresh()
        self.capture('failed');self.defer()
        self.assertIn('CHECK:target',w.view(f.root,f.ident)['blockers'])

    def test_deferral_does_not_automatically_apply_to_new_failures(self):
        f=self.f;self.capture('failed');self.defer();self.assertTrue(w.view(f.root,f.ident)['eligible'])
        new=self.capture('failed','new case')
        self.assertFalse(w.view(f.root,f.ident)['eligible'])
        self.assertIn('RUNTIME_FAILURE:'+new,w.view(f.root,f.ident)['blockers'])

    def test_deferral_requires_surviving_unchanged_handoff(self):
        f=self.f;self.capture('failed');self.defer();(f.root/'ISSUES.md').unlink()
        self.assertFalse(w.view(f.root,f.ident)['eligible'])
        with self.assertRaisesRegex(ValueError,'DEFERRAL_HANDOFF_MUST_SURVIVE'):
            w.defer_claim(f.root,f.ident,'C1','reason','authority',w.now(),'.featrace/scratch/issue.md',exclude=True)

    def test_restoring_a_deferred_promise_restores_its_failure(self):
        f=self.f;a=self.capture('failed');self.defer()
        w.defer_claim(f.root,f.ident,'C1','Product restored the original promise','Actual new synthetic decision',w.now(),reopen=True)
        self.assertFalse(w.view(f.root,f.ident)['eligible']);self.assertIn(a,w.task_failures.pending(f.doc()))

    def test_changed_statement_or_kind_does_not_resolve_failure(self):
        f=self.f;a=self.capture('failed');f.plan['criteria'][0].update(expected='Clarified text',kind='unaffected');f.refresh()
        self.assertIn(a,w.task_failures.pending(f.doc()))
        p=copy.deepcopy(f.plan);p['criteria'][0]['id']='C2';p['checks'][0]['covers']=['C2']
        with self.assertRaisesRegex(ValueError,'UNRESOLVED_OBSERVATION_REMOVED'):w.set_plan(f.root,f.ident,p)

    def test_prune_keeps_original_failure_and_resolution_support(self):
        f=self.f;a=self.capture('failed');p=self.capture('passed');self.resolve(a,p)
        self.capture('passed','extra evidence');w.prune(f.root,f.ident,True)
        self.assertTrue({a,p}<=set(f.doc()['facts']))

    def test_closed_deferral_cleanup_stops_if_handoff_is_lost(self):
        f=self.f;self.capture('failed');self.defer();w.close(f.root,f.ident,[])
        d=f.doc();d['receipt']['completed_at']=(datetime.now(timezone.utc)-timedelta(days=9)).isoformat();w.save(f.root,d)
        (f.root/'ISSUES.md').unlink();before=w.task_path(f.root,f.ident).read_bytes()
        with self.assertRaises(ValueError):w.cleanup(f.root,f.ident,True,forget=True)
        self.assertEqual(w.task_path(f.root,f.ident).read_bytes(),before)

    def test_later_condition_clarification_invalidates_old_handoff(self):
        f=self.f;a=self.capture('failed');self.defer()
        w.failure_action(f.root,f.ident,a,'clarify','Original evidence establishes another necessary condition',conditions={'session':'first launch','language':'empty'})
        self.assertFalse(w.view(f.root,f.ident)['eligible'])
        self.assertIn('DEFERRAL_STALE:C1',w.view(f.root,f.ident)['blockers'])

    def test_generic_handoff_cannot_discard_reproduction_context(self):
        f=self.f;self.capture('failed')
        reason='Known issue';authority='Synthetic product decision'
        (f.root/'ISSUES.md').write_text(reason+'\n'+authority)
        with self.assertRaisesRegex(ValueError,'DEFERRAL_HANDOFF_INCOMPLETE'):
            w.defer_claim(f.root,f.ident,'C1',reason,authority,w.now(),'ISSUES.md',exclude=True)

    def test_prune_keeps_prior_deferral_command_references(self):
        f=self.f;old=f.execute()['execution'];self.capture('failed');self.defer()
        f.plan['checks'][0]['cache']={'mode':'never'};f.refresh();f.execute()
        w.prune(f.root,f.ident,True)
        self.assertIn(old,f.doc()['facts'])

    def test_compacted_deferral_still_counts_unresolved_failure(self):
        f=self.f;a=self.capture('failed');self.defer();w.close(f.root,f.ident,[])
        d=f.doc();d['receipt']['completed_at']=(datetime.now(timezone.utc)-timedelta(days=9)).isoformat();w.save(f.root,d)
        handoff=(f.root/'ISSUES.md').read_text();w.cleanup(f.root,f.ident,True)
        self.assertNotIn('facts',f.doc())
        self.assertEqual(w.storage(f.root)['items'][0]['pending_runtime_failures'],1)
        self.assertEqual(w.storage(f.root)['counts']['pending_runtime_failure'],1)
        self.assertIn('first launch',handoff);self.assertIn(a,handoff)
        self.assertEqual(w.view(f.root,f.ident)['deferred_count'],1)

    def test_expired_resolution_evidence_refuses(self):
        f=self.f;f.plan['criteria'][0]['validity']={'mode':'current','target':'synthetic current fixture, not a real device','max_age_seconds':1,'reason':'Current synthetic state'};f.refresh()
        a=self.capture('failed');p=self.capture('passed')
        d=f.doc();d['facts'][p]['observed_at']=(datetime.now(timezone.utc)-timedelta(seconds=2)).isoformat();w.save(f.root,d)
        with self.assertRaisesRegex(ValueError,'CURRENT_FACT_REQUIRED'):self.resolve(a,p)

    def test_format3_refuses_without_rewriting(self):
        f=self.f;d=f.doc();d['task_contract']=3;w.save(f.root,d);before=w.task_path(f.root,f.ident).read_bytes()
        with self.assertRaisesRegex(ValueError,'USE_PINNED_TOOL'):w.load(f.root,f.ident)
        self.assertEqual(w.task_path(f.root,f.ident).read_bytes(),before)

    def test_action_history_is_bounded_and_never_discarded(self):
        f=self.f;a=self.capture('failed')
        for _ in range(w.task_failures.MAX_ACTIONS):w.failure_action(f.root,f.ident,a,'reopen','Synthetic bounded correction')
        before=w.task_path(f.root,f.ident).read_bytes()
        with self.assertRaisesRegex(ValueError,'FAILURE_ACTION_LIMIT'):w.failure_action(f.root,f.ident,a,'reopen','One too many')
        self.assertEqual(w.task_path(f.root,f.ident).read_bytes(),before)


if __name__=='__main__':unittest.main()
