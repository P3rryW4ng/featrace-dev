import json
from pathlib import Path
import subprocess
import sys
from test_task_workflow import TaskWorkflowTests, CORE


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
        import task_workflow as w
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


for name in list(dir(PolicyDiagnosticsTests)):
    if name.startswith('test_') and name not in PolicyDiagnosticsTests.__dict__:setattr(PolicyDiagnosticsTests,name,None)
del TaskWorkflowTests
