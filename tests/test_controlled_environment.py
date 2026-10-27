"""Actual child environments, causal tool identities and contract6 refusal."""
import copy
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import test_task_workflow as fixture
w=fixture.w

class ControlledEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.TaskWorkflowTests(methodName='runTest');self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.configure()
    def configure(self,keys=None,paths=None):
        f=self.f;f.plan['checks'][0]['execution_env']={'mode':'controlled','inherit_keys':keys or [],'search_path':paths or ['/usr/bin','/bin']};f.refresh()
    def test_unselected_host_changes_reuse_and_values_are_absent_in_child(self):
        f=self.f;(f.root/'check.py').write_text('import os\nassert "JAVA_HOME" not in os.environ\nassert "PRIVATE_SYNTHETIC" not in os.environ\nprint("controlled child")\n');f.refresh()
        with patch.dict(os.environ,{'JAVA_HOME':'first','PRIVATE_SYNTHETIC':'never persist'}):first=f.execute()
        with patch.dict(os.environ,{'JAVA_HOME':'second','PATH':'/unselected/host:/usr/bin:/bin'}):second=f.execute()
        self.assertEqual(first['status'],'passed');self.assertTrue(second['reused']);self.assertEqual(first['execution'],second['execution'])
        self.assertNotIn('never persist',w.task_path(f.root,f.ident).read_text())
    def test_selected_key_changes_invalidate_and_missing_is_missing(self):
        f=self.f;self.configure(['SELECTED_SYNTHETIC']);(f.root/'check.py').write_text('import os\nprint("present" if "SELECTED_SYNTHETIC" in os.environ else "absent")\n');f.refresh()
        with patch.dict(os.environ,{'SELECTED_SYNTHETIC':'secret one'}):a=f.execute();b=f.execute()
        with patch.dict(os.environ,{'SELECTED_SYNTHETIC':'secret two'}):c=f.execute()
        with patch.dict(os.environ,{},clear=True):d=f.execute()
        self.assertTrue(b['reused']);self.assertFalse(c['reused']);self.assertFalse(d['reused']);self.assertEqual(d['status'],'passed')
        self.assertNotIn('secret one',w.task_path(f.root,f.ident).read_text());self.assertNotIn('secret two',w.task_path(f.root,f.ident).read_text())
    def test_selected_key_is_bound_even_if_currently_absent(self):
        f=self.f;f.execute();old=f.execution()['input_digest'];self.configure(['ABSENT_SYNTHETIC_KEY'])
        self.assertNotEqual(old,w.check_stamp(f.root,f.doc(),f.plan['checks'][0]))
    def test_top_level_resolution_and_launch_use_controlled_path(self):
        f=self.f;tools=f.root/'tools';tools.mkdir();tool=tools/'synthetic-check';tool.write_text('#!'+sys.executable+'\nprint("selected executable")\n');tool.chmod(0o755)
        f.plan['checks'][0]['argv']=['synthetic-check'];f.plan['checks'][0]['inputs'].append('tools/synthetic-check');self.configure(paths=[str(tools)])
        with patch.dict(os.environ,{'PATH':'/missing-host-path:/usr/bin:/bin'}):self.assertEqual(f.execute()['status'],'passed')
        old=f.execution()['input_digest'];tool.write_text('#!'+sys.executable+'\nprint("new actual executable bytes")\n');self.assertNotEqual(old,w.check_stamp(f.root,f.doc(),f.plan['checks'][0]))
    def test_nested_tool_bytes_require_existing_declared_inputs(self):
        f=self.f;tools=f.root/'tools';tools.mkdir();tool=tools/'subtool';tool.write_text('#!/bin/sh\necho first\n');tool.chmod(0o755)
        (f.root/'check.py').write_text('import subprocess\nprint(subprocess.check_output(["subtool"]).decode())\n')
        f.plan['checks'][0]['external_inputs']=[{'kind':'file','path':str(tool)}];self.configure(paths=[str(tools)])
        f.execute();before=f.execution()['input_digest'];tool.write_text('#!/bin/sh\necho second\n')
        self.assertNotEqual(before,w.check_stamp(f.root,f.doc(),f.plan['checks'][0]));self.assertFalse(f.execute()['reused'])
    def test_fixed_search_path_change_invalidates(self):
        f=self.f;f.execute();before=f.execution()['input_digest'];self.configure(paths=['/bin','/usr/bin']);self.assertNotEqual(before,w.check_stamp(f.root,f.doc(),f.plan['checks'][0]))
    def test_invalid_or_escaping_config_is_refused_without_plan_write(self):
        f=self.f;before=w.task_path(f.root,f.ident).read_bytes()
        configs=[{'mode':'invalid'},{'mode':'inherit','inherit_keys':[]},
                 {'mode':'controlled','inherit_keys':['PATH'],'search_path':['/bin']},
                 {'mode':'controlled','inherit_keys':['BAD-NAME'],'search_path':['/bin']},
                 {'mode':'controlled','inherit_keys':['A','A'],'search_path':['/bin']},
                 *[{'mode':'controlled','inherit_keys':[],'search_path':paths} for paths in ([],[''],['.'],['../tools'],['/bin:'],['/bin/../tmp'])]]
        for config in configs:
            plan=copy.deepcopy(f.plan);plan['checks'][0]['execution_env']=config
            with self.subTest(config=config),self.assertRaises(ValueError):w.set_plan(f.root,f.ident,plan)
        self.assertEqual(before,w.task_path(f.root,f.ident).read_bytes())
    def test_env_keys_conflict_refused(self):
        f=self.f;plan=copy.deepcopy(f.plan);plan['checks'][0]['env_keys']=['JAVA_HOME']
        with self.assertRaisesRegex(ValueError,'EXECUTION_ENV_KEYS_CONFLICT'):w.set_plan(f.root,f.ident,plan)
    def test_start_snapshot_is_used_even_if_host_changes_before_launch(self):
        f=self.f;self.configure(['SELECTED_SYNTHETIC']);(f.root/'check.py').write_text('import os\nassert os.environ["SELECTED_SYNTHETIC"]=="start-value"\n');f.refresh();original=w.task_execution.invoke
        def invoke(*args):
            os.environ['SELECTED_SYNTHETIC']='later-value'
            return original(*args)
        with patch.dict(os.environ,{'SELECTED_SYNTHETIC':'start-value'}),patch.object(w.task_execution,'invoke',side_effect=invoke):result=f.execute()
        self.assertEqual(result['status'],'unavailable');self.assertEqual(f.execution()['exit_code'],0);self.assertEqual(f.execution()['reason'],'EXECUTION_INPUT_MOVED')
    def test_inherit_remains_default_and_conservative(self):
        f=self.f;del f.plan['checks'][0]['execution_env'];f.refresh()
        with patch.dict(os.environ,{'JAVA_HOME':'one'}):f.execute()
        with patch.dict(os.environ,{'JAVA_HOME':'two'}):self.assertFalse(f.execute()['reused'])
    def test_contracts_one_to_five_refused_without_mutation(self):
        f=self.f;original=f.doc()
        for contract in range(1,6):
            d=copy.deepcopy(original);d['task_contract']=contract;w.save(f.root,d);before=w.task_path(f.root,f.ident).read_bytes()
            with self.assertRaisesRegex(ValueError,'TASK_CONTRACT_UNSUPPORTED_USE_PINNED_TOOL'):w.load(f.root,f.ident)
            self.assertEqual(before,w.task_path(f.root,f.ident).read_bytes())

    def test_actual_path_tool_cannot_escape_denied_or_ask_policy(self):
        f=self.f;tools=f.root/'tools';tools.mkdir();tool=tools/'policy-tool';tool.write_text('#!'+sys.executable+'\nfrom pathlib import Path\nPath("launched").touch()\n');tool.chmod(0o755)
        f.plan['checks'][0]['argv']=['policy-tool'];self.configure(paths=[str(tools)])
        policy=w.task_policy.load(f.root)
        for permission in ('denied','ask'):
            policy['rules']=[{'source':'rules.md','sha256':'prepared','paths':['tools/policy-tool'],'operations':['test'],'environment':'local','decision':'Synthetic tool-specific policy','permission':permission,'authority':'Synthetic owner'}]
            w.task_policy.prepare(f.root,policy,w.git)
            with self.subTest(permission=permission),self.assertRaisesRegex(ValueError,'OPERATION_POLICY_'+permission.upper()):f.execute()
            self.assertFalse((f.root/'launched').exists())
    def test_controlled_remote_freshness_is_not_replaced_by_content_cache(self):
        f=self.f;plan=copy.deepcopy(f.plan);plan['checks'][0]['environment']={'kind':'remote','target':'synthetic remote','policy_environment':'test'}
        with self.assertRaisesRegex(ValueError,'MUTABLE_ENVIRONMENT_CACHE_REFUSED'):w.set_plan(f.root,f.ident,plan)
