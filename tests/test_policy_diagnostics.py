import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from test_task_workflow import TaskWorkflowTests, CORE, w


class PolicyDiagnosticsTests(TaskWorkflowTests):
    def cli(self, *args):
        result=subprocess.run([sys.executable,'-B',str(CORE/'task_workflow.py'),*args],capture_output=True,text=True)
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        return json.loads(result.stdout)

    def test_missing_policy_has_specific_code_without_creating_task(self):
        (self.root/'.featrace-policy.json').unlink()
        value=self.cli('begin',str(self.root),'NEW','--request','Synthetic task')
        self.assertEqual(value['reason'],'PROJECT_POLICY_REQUIRED')
        self.assertFalse((self.root/'.featrace/tasks/NEW.json').exists())

    def test_ask_and_denied_codes_survive_cli_without_execution(self):
        for permission in ('ask','denied'):
            config=w.task_policy.load(self.root)
            config['rules']=[{'source':'rules.md','sha256':'prepared','paths':['app.py'],'operations':['test'],
                              'environment':'local','decision':'Synthetic restricted check','permission':permission,
                              'authority':'Synthetic fixture only'}]
            w.task_policy.prepare(self.root,config,w.git);self.refresh()
            value=self.cli('run',str(self.root),self.ident,'--check','target')
            self.assertEqual(value['reason'],'OPERATION_POLICY_'+permission.upper())
            self.assertFalse((self.root/'run-count').exists())

    def test_invalid_policy_schema_has_specific_code_not_source_contents(self):
        (self.root/'.featrace-policy.json').write_text(json.dumps({'private_synthetic_field':'do-not-echo-fixture'}))
        value=self.cli('begin',str(self.root),'NEW','--request','Synthetic task')
        self.assertEqual(value['reason'],'POLICY_FIELDS_INVALID')
        self.assertNotIn('do-not-echo-fixture',json.dumps(value))

    def test_unexpected_json_error_remains_generic_without_echoing_input(self):
        (self.root/'.featrace-policy.json').write_text('{not-json-do-not-echo-fixture')
        value=self.cli('begin',str(self.root),'NEW','--request','Synthetic task')
        self.assertEqual(value['reason'],'TASK_OPERATION_REFUSED; inspect selected inputs privately')
        self.assertNotIn('not-json-do-not-echo-fixture',json.dumps(value))


    def assert_scope_reason(self, reason):
        before=w.task_path(self.root,self.ident).read_bytes()
        members=sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        value=w.view(self.root,self.ident)
        self.assertFalse(value['eligible'])
        self.assertIn('SCOPE_NOT_READY',value['blockers'])
        self.assertEqual(value['scope_readiness'],{'ready':False,'reason':reason,'details':'detail --section plan'})
        self.assertEqual(before,w.task_path(self.root,self.ident).read_bytes())
        self.assertEqual(members,sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*')))
        self.assertFalse((self.root/'run-count').exists())
        with self.assertRaisesRegex(ValueError,'DELIVERY_BLOCKED'):
            w.close(self.root,self.ident,[])
        return value

    def test_status_separates_scope_ready_from_missing_checks(self):
        value=w.view(self.root,self.ident)
        self.assertEqual(value['scope_readiness'],{'ready':True})
        self.assertFalse(value['eligible'])
        self.assertIn('CHECK:target',value['blockers'])

    def test_status_names_local_unknown_without_execution_or_write(self):
        self.plan['unknowns']=[{'reason':'Missing selected source','criteria':['C1'],'checks':[]}]
        self.refresh()
        self.assert_scope_reason('SCOPE_UNKNOWN')

    def test_status_names_input_drift_without_execution_or_write(self):
        (self.root/'app.py').write_text('changed after analysis')
        self.assert_scope_reason('SCOPE_REVIEW_REQUIRED')

    def test_status_names_missing_policy_without_execution_or_write(self):
        (self.root/'.featrace-policy.json').unlink()
        self.assert_scope_reason('PROJECT_POLICY_REQUIRED')

    def test_status_names_changed_applicable_rule(self):
        config=w.task_policy.load(self.root)
        config['rules']=[{'source':'rules.md','sha256':'prepared','paths':['app.py'],'operations':['test'],
                         'environment':'local','decision':'Synthetic grant','permission':'allowed','authority':'Fixture only'}]
        w.task_policy.prepare(self.root,config,w.git)
        self.plan['constraints']={};self.refresh()
        (self.root/'rules.md').write_text('Updated governing rule')
        self.assert_scope_reason('APPLICABLE_RULE_CHANGED')

    def test_status_unknown_exceptions_and_code_like_messages_remain_private(self):
        for exc in (OSError('private-path-synthetic'),ValueError('SCOPE_UNKNOWN'),
                    w.TaskError('SCOPE_UNKNOWN private-input-synthetic')):
            with self.subTest(kind=type(exc).__name__), patch.object(w,'ready',side_effect=exc):
                value=self.assert_scope_reason('SCOPE_NOT_READY')
                self.assertNotIn('private-',json.dumps(value))

    def test_status_malformed_policy_remains_generic(self):
        (self.root/'.featrace-policy.json').write_text('{private-invalid-policy-synthetic')
        value=self.assert_scope_reason('SCOPE_NOT_READY')
        self.assertNotIn('private-invalid',json.dumps(value))


for name in list(dir(PolicyDiagnosticsTests)):
    if name.startswith('test_') and name not in PolicyDiagnosticsTests.__dict__:setattr(PolicyDiagnosticsTests,name,None)
del TaskWorkflowTests
