import copy
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
import unittest
import test_task_workflow as fixture
w=fixture.w


class ScopedAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.TaskWorkflowTests(methodName='runTest');self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.policy=w.task_policy.load(self.f.root)
        self.policy['rules']=[{'source':'rules.md','sha256':'prepared','paths':['app.py'],'operations':['test'],'environment':'local','decision':'Keep the same substantive test rule','permission':'ask','authority':'Synthetic standing rule owner'}]
        self.configure();self.f.refresh()

    def configure(self):w.task_policy.prepare(self.f.root,self.policy,w.git)
    def grant(self,mode='once',expiry=None):
        return w.authorize(self.f.root,self.f.ident,'target',mode,'Actual synthetic scoped human approval',w.now(),expiry or (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),'Only selected fixture check and environment')

    def test_ask_refuses_without_a_process(self):
        with self.assertRaisesRegex(ValueError,'OPERATION_POLICY_ASK'):self.f.execute()
        self.assertFalse((self.f.root/'run-count').exists())

    def test_once_grant_does_not_change_standing_policy_and_retains_authority(self):
        f=self.f;before=(f.root/w.task_policy.NAME).read_bytes();g=self.grant();a=f.execute()
        self.assertEqual((f.root/w.task_policy.NAME).read_bytes(),before)
        self.assertEqual(f.execution()['authorization']['grant'],g['authorization'])
        self.assertEqual(f.doc()['authorizations'][g['authorization']]['uses'],[a['execution']])
        f.support();self.assertTrue(w.view(f.root,f.ident)['eligible'])

    def test_expired_used_grant_keeps_original_fact_but_refuses_new_execution(self):
        f=self.f;g=self.grant();first=f.execute();f.support()
        d=f.doc();d['authorizations'][g['authorization']]['expires_at']=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat();w.save(f.root,d)
        self.assertTrue(w.view(f.root,f.ident)['eligible']);self.assertTrue(f.execute()['reused'])
        (f.root/'app.py').write_text('label="after changed"');f.refresh()
        with self.assertRaisesRegex(ValueError,'OPERATION_POLICY_ASK'):f.execute()
        self.assertIn(first['execution'],f.doc()['facts']);self.assertEqual((f.root/'run-count').read_text(),'1')

    def test_restore_ask_does_not_expire_original_lawful_result(self):
        f=self.f;self.policy['rules'][0]['permission']='allowed';self.configure();f.refresh();a=f.execute();f.support()
        self.policy['rules'][0]['permission']='ask';self.policy['rules'][0]['authority']='Original approver metadata clarified';self.configure()
        self.assertTrue(w.view(f.root,f.ident)['eligible']);self.assertEqual(f.execute()['execution'],a['execution'])

    def test_once_grant_is_not_reusable_for_another_physical_attempt(self):
        f=self.f;f.plan['checks'][0]['cache']={'mode':'never'};f.refresh();self.grant();f.execute()
        with self.assertRaisesRegex(ValueError,'OPERATION_POLICY_ASK'):f.execute()
        self.assertEqual((f.root/'run-count').read_text(),'1')

    def test_task_grant_covers_authorized_repair_retries_in_same_declared_scope(self):
        f=self.f;g=self.grant('task');f.execute();(f.root/'app.py').write_text('label="after retry"');f.refresh();f.execute()
        self.assertEqual(len(f.doc()['authorizations'][g['authorization']]['uses']),2)
        self.assertEqual((f.root/'run-count').read_text(),'2')

    def test_changed_command_or_environment_cannot_expand_grant(self):
        f=self.f;self.grant('task');f.plan['checks'][0]['environment']['target']='Another target';f.refresh()
        with self.assertRaisesRegex(ValueError,'OPERATION_POLICY_ASK'):f.execute()

    def test_denied_still_blocks_new_process_and_grant(self):
        f=self.f;self.grant('task');self.policy['rules'][0]['permission']='denied';self.configure()
        with self.assertRaisesRegex(ValueError,'OPERATION_POLICY_DENIED'):f.execute()
        with self.assertRaisesRegex(ValueError,'OPERATION_POLICY_DENIED'):self.grant()
        self.assertFalse((f.root/'run-count').exists())

    def test_substantive_rule_change_does_not_reuse_old_grant(self):
        f=self.f;self.grant('task');(f.root/'rules.md').write_text('A materially different required check')
        with self.assertRaisesRegex(ValueError,'APPLICABLE_RULE_CHANGED'):f.refresh()
        self.configure();f.refresh()
        with self.assertRaisesRegex(ValueError,'OPERATION_POLICY_ASK'):f.execute()

    def test_interrupted_attempt_consumes_once_without_erasing_unavailable_fact(self):
        f=self.f;g=self.grant()
        original=w.task_execution.invoke
        def invoke(*args):
            status,code,interrupted,reason=original(*args)
            return 'unavailable',code,KeyboardInterrupt(),'Synthetic caught interruption'
        with patch.object(w.task_execution,'invoke',side_effect=invoke):
            with self.assertRaises(KeyboardInterrupt):f.execute()
        self.assertEqual(f.execution()['status'],'unavailable')
        self.assertEqual(len(f.doc()['authorizations'][g['authorization']]['uses']),1)
        with self.assertRaisesRegex(ValueError,'OPERATION_POLICY_ASK'):f.execute()

    def test_authorizations_are_bounded_and_overflow_does_not_overwrite(self):
        f=self.f
        for _ in range(w.task_authorization.MAX_GRANTS):self.grant()
        before=w.task_path(f.root,f.ident).read_bytes()
        with self.assertRaisesRegex(ValueError,'AUTHORIZATION_LIMIT'):self.grant()
        self.assertEqual(w.task_path(f.root,f.ident).read_bytes(),before)

    def test_future_decision_refuses_without_mutation(self):
        f=self.f;before=w.task_path(f.root,f.ident).read_bytes();future=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
        with self.assertRaisesRegex(ValueError,'AUTHORIZATION_TIME_INVALID'):w.authorize(f.root,f.ident,'target','once','Owner',future,future,'Scope')
        self.assertEqual(w.task_path(f.root,f.ident).read_bytes(),before)
