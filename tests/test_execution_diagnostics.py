"""Read-only check explanations never substitute for execution identity or authority."""
import copy
import json
import os
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
import unittest
import test_task_workflow as fixture
w=fixture.w
class ExecutionDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.TaskWorkflowTests(methodName='runTest');self.f.setUp();self.addCleanup(self.f.doCleanups)
    def diagnostic(self):return json.loads(w.detail(self.f.root,self.f.ident,'check','target')['text'])
    def ask_once(self):
        f=self.f;p=w.task_policy.load(f.root);p['rules']=[{'source':'rules.md','sha256':'prepared','paths':['app.py'],'operations':['test'],'environment':'local','decision':'Selected fixture needs real scope approval','permission':'ask','authority':'Synthetic rule owner'}];w.task_policy.prepare(f.root,p,w.git);f.refresh()
        return w.authorize(f.root,f.ident,'target','once','Actual synthetic scoped approval',w.now(),(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),'Only selected local check')
    def test_components_preserve_collector_result_and_do_not_store_environment_values(self):
        f=self.f
        with patch.dict(os.environ,{'CI':'Synthetic-private-environment-value'}):
            plain=w.task_inputs.signature(f.root,['app.py'],[],[],[]);parts={};observed=w.task_inputs.signature(f.root,['app.py'],[],[],[],parts)
            self.assertEqual(plain,observed);f.execute();fact=f.execution()
        self.assertEqual(set(parts),{'environment','selected_inputs'});self.assertEqual(set(fact['identity_components']),set(w.IDENTITY_COMPONENTS));self.assertNotIn('Synthetic-private-environment-value',json.dumps(fact))
    def test_environment_change_is_explained_without_rerunning_or_writing(self):
        f=self.f;f.execute();before=w.task_path(f.root,f.ident).read_bytes()
        with patch.dict(os.environ,{'CI':'Synthetic-changed'}):out=self.diagnostic()
        self.assertEqual(out['reuse']['changed_components'],['environment']);self.assertIn('IDENTITY_CHANGED',out['reuse']['reasons']);self.assertEqual(out['new_execution_permission'],'available');self.assertFalse(out['reuse']['eligible']);self.assertEqual(before,w.task_path(f.root,f.ident).read_bytes());self.assertEqual((f.root/'run-count').read_text(),'1')
    def test_spent_once_approval_does_not_invalidate_a_cached_original_fact(self):
        f=self.f;g=self.ask_once();a=f.execute();before=copy.deepcopy(f.doc());out=self.diagnostic()
        self.assertTrue(out['reuse']['eligible']);self.assertEqual(out['new_execution_permission'],'approval_required');self.assertEqual(f.doc(),before);self.assertTrue(f.execute()['reused']);self.assertEqual(f.doc()['authorizations'][g['authorization']]['uses'],[a['execution']])
    def test_changed_environment_and_new_permission_are_separate(self):
        f=self.f;self.ask_once();f.execute()
        with patch.dict(os.environ,{'CI':'Synthetic-changed'}):
            out=self.diagnostic();self.assertEqual(out['reuse']['changed_components'],['environment']);self.assertEqual(out['new_execution_permission'],'approval_required')
            with self.assertRaisesRegex(ValueError,'OPERATION_POLICY_ASK'):f.execute()
        self.assertEqual((f.root/'run-count').read_text(),'1')
    def test_missing_historical_components_are_not_reconstructed(self):
        f=self.f;f.execute();d=f.doc();del d['facts'][d['executions']['target']]['identity_components'];w.save(f.root,d);before=w.task_path(f.root,f.ident).read_bytes()
        self.assertTrue(self.diagnostic()['reuse']['eligible'])
        with patch.dict(os.environ,{'CI':'Synthetic-changed'}):out=self.diagnostic()
        self.assertEqual(out['reuse']['historical_components'],'not_collected');self.assertEqual(out['reuse']['changed_components'],[]);self.assertIn('IDENTITY_CHANGED',out['reuse']['reasons']);self.assertEqual(before,w.task_path(f.root,f.ident).read_bytes())
    def test_input_and_artifact_changes_remain_distinct(self):
        f=self.f;f.execute();(f.root/'app.py').write_text('label="after changed"\n');f.refresh();out=self.diagnostic();self.assertEqual(out['reuse']['changed_components'],['selected_inputs'])
        artifact=f.root/f.execution()['artifact']['path'];artifact.write_text('corrupted original output\n');out=self.diagnostic();self.assertIn('ARTIFACT_UNAVAILABLE',out['reuse']['reasons'])
    def test_diagnostic_hashes_selected_inputs_once(self):
        self.f.execute()
        with patch.object(w.task_inputs,'signature',wraps=w.task_inputs.signature) as signature:
            self.assertTrue(self.diagnostic()['reuse']['eligible']);self.assertEqual(signature.call_count,1)
    def test_untrusted_exception_and_component_values_are_not_echoed(self):
        f=self.f;f.execute()
        with patch.object(w,'check_stamp',side_effect=OSError('Sensitive arbitrary path')):
            out=self.diagnostic();self.assertEqual(out['reuse']['reasons'],['IDENTITY_UNAVAILABLE']);self.assertNotIn('Sensitive',json.dumps(out))
        d=f.doc();d['facts'][d['executions']['target']]['identity_components']={'Sensitive arbitrary key':'Sensitive arbitrary value'};w.save(f.root,d)
        out=self.diagnostic();self.assertTrue(out['reuse']['eligible']);self.assertEqual(out['reuse']['historical_components'],'not_collected');self.assertNotIn('Sensitive',json.dumps(out))
    def test_cache_never_is_explained_without_revoking_delivery_proof(self):
        f=self.f;f.plan['checks'][0]['cache']={'mode':'never'};f.refresh();f.execute();f.support();out=self.diagnostic()
        self.assertIn('CACHE_DISABLED',out['reuse']['reasons']);self.assertFalse(out['reuse']['eligible']);self.assertTrue(w.view(f.root,f.ident)['eligible'])
    def test_cli_check_details_use_the_check_selector_and_preserve_task(self):
        from pathlib import Path
        import subprocess,sys
        f=self.f;f.execute();before=w.task_path(f.root,f.ident).read_bytes()
        result=subprocess.run([sys.executable,str(Path(w.__file__)),'detail',str(f.root),f.ident,'--section','check','--check','target'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout);page=json.loads(result.stdout);self.assertTrue(page['complete']);self.assertEqual(json.loads(page['text'])['check'],'target');self.assertEqual(before,w.task_path(f.root,f.ident).read_bytes());self.assertEqual((f.root/'run-count').read_text(),'1')
    def test_current_deny_blocks_a_new_process_but_not_a_lawful_cached_fact(self):
        f=self.f;self.ask_once();f.execute();policy=w.task_policy.load(f.root);policy['rules'][0]['permission']='denied';w.task_policy.prepare(f.root,policy,w.git)
        out=self.diagnostic();self.assertTrue(out['reuse']['eligible']);self.assertEqual(out['new_execution_permission'],'denied');self.assertTrue(f.execute()['reused'])
        f.plan['checks'][0]['cache']={'mode':'never'};f.refresh()
        with self.assertRaisesRegex(ValueError,'OPERATION_POLICY_DENIED'):f.execute()
        self.assertEqual((f.root/'run-count').read_text(),'1')
    def test_expiry_is_still_reported_as_a_reuse_blocker(self):
        f=self.f;f.plan['checks'][0]['cache']={'mode':'content','max_age_seconds':1};f.refresh();f.execute();d=f.doc();d['facts'][d['executions']['target']]['at']=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat();w.save(f.root,d)
        out=self.diagnostic();self.assertFalse(out['reuse']['eligible']);self.assertIn('EXPIRED',out['reuse']['reasons']);self.assertEqual((f.root/'run-count').read_text(),'1')
    def test_completed_task_diagnostic_is_not_permission_to_execute(self):
        f=self.f;f.execute();f.support();w.close(f.root,f.ident,[]);out=self.diagnostic();self.assertEqual(out['new_execution_permission'],'task_complete')
        with self.assertRaisesRegex(ValueError,'TASK_ALREADY_COMPLETE'):f.execute()
