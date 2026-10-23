import copy
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from test_task_workflow import TaskWorkflowTests, w


class EvidenceCoreTests(TaskWorkflowTests):
    def proof(self, alternatives, checks=False):
        self.plan['criteria'][0]['proof']={'any_of':alternatives,'reason':'Specific synthetic proof requirement'}
        if not checks:self.plan['checks']=[]
        self.refresh()

    def explicit(self, ids):
        return w.assess(self.root,self.ident,'C1','supported','Actual selected facts only',fact_ids=ids)

    def test_changed_structural_claim_can_use_sufficient_static_proof(self):
        self.proof([['static_analysis']])
        f=self.observe('C1','static_analysis',w.now(),'Changed structure satisfies inspected invariant',['app.py'])
        self.explicit([f['fact']]);self.assertTrue(w.view(self.root,self.ident)['eligible'])
        self.assertFalse((self.root/'run-count').exists())

    def test_runtime_requirement_cannot_be_supported_by_static_or_compile_command(self):
        self.proof([['runtime_observation']],True);run=self.execute()
        f=self.observe('C1','static_analysis',w.now(),'Only inspected source',['app.py'])
        for ids in ([run['execution']],[f['fact']]):
            with self.assertRaisesRegex(ValueError,'PROOF_REQUIREMENTS_UNMET'):self.explicit(ids)

    def test_supported_requires_explicit_fact_selection(self):
        self.execute()
        with self.assertRaisesRegex(ValueError,'SUPPORT_SELECTION_REQUIRED'):
            w.assess(self.root,self.ident,'C1','supported','Command passed is not automatic coverage')

    def test_combined_proof_keeps_both_observations_and_explicit_subset(self):
        self.proof([['runtime_observation','static_analysis']])
        a=self.observe('C1','runtime_observation',w.now(),'Success path observed',['app.py'])
        b=self.observe('C1','runtime_observation',w.now(),'Failure behavior observed to work',['app.py'])
        c=self.observe('C1','static_analysis',w.now(),'Cancellation propagation inspected',['app.py'])
        with self.assertRaisesRegex(ValueError,'PROOF_REQUIREMENTS_UNMET'):self.explicit([a['fact']])
        self.explicit([a['fact'],b['fact'],c['fact']])
        self.assertEqual(set(self.doc()['assessments']['C1']['facts']),{a['fact'],b['fact'],c['fact']})
        self.assertEqual(len(self.doc()['facts']),3)
        self.assertTrue(w.view(self.root,self.ident)['eligible'])

    def test_new_compatible_observation_does_not_stale_selected_old_fact(self):
        self.proof([['runtime_observation']])
        a=self.observe('C1','runtime_observation',w.now(),'Observed relevant success',['app.py']);self.explicit([a['fact']])
        self.observe('C1','runtime_observation',w.now(),'Extra independent supporting view',['app.py'])
        self.assertTrue(w.view(self.root,self.ident)['eligible'])
        self.assertEqual(self.doc()['assessments']['C1']['facts'],[a['fact']])

    def test_unused_candidate_artifact_drift_does_not_invalidate_selected_fact(self):
        self.proof([['runtime_observation']])
        (self.root/'extra.txt').write_text('extra');a=self.observe('C1','runtime_observation',w.now(),'Main',['app.py'])
        self.observe('C1','runtime_observation',w.now(),'Unused candidate',['extra.txt'])
        self.explicit([a['fact']]);(self.root/'extra.txt').write_text('changed unused evidence')
        self.assertTrue(w.view(self.root,self.ident)['eligible'])

    def test_missing_unused_artifact_does_not_break_candidate_query(self):
        self.proof([['runtime_observation']]);(self.root/'unused.txt').write_text('unused')
        a=self.observe('C1','runtime_observation',w.now(),'Selected',['app.py'])
        b=self.observe('C1','runtime_observation',w.now(),'Unused',['unused.txt']);self.explicit([a['fact']])
        (self.root/'unused.txt').unlink()
        self.assertEqual(w.review_input(self.root,self.ident,'C1')['facts'],[a['fact']])
        self.assertTrue(w.view(self.root,self.ident)['eligible'])

    def test_unrelated_check_cannot_be_selected_as_support(self):
        self.plan['criteria'].append({'id':'C2','expected':'Other','kind':'unaffected','inputs':['app.py']})
        self.plan['checks'][0]['covers']=['C2'];self.refresh();run=self.execute()
        with self.assertRaisesRegex(ValueError,'CURRENT_FACT_REQUIRED'):self.explicit([run['execution']])

    def test_selected_original_fact_drift_is_not_hidden_by_new_fact(self):
        self.proof([['runtime_observation']]);(self.root/'old.txt').write_text('old')
        a=self.observe('C1','runtime_observation',w.now(),'Original',['old.txt']);self.explicit([a['fact']])
        self.observe('C1','runtime_observation',w.now(),'New alternative',['app.py'])
        (self.root/'old.txt').write_text('damaged')
        self.assertFalse(w.view(self.root,self.ident)['eligible'])

    def test_original_result_survives_later_command_attempt(self):
        self.plan['checks'][0]['cache']={'mode':'never','max_age_seconds':300};self.refresh()
        first=self.execute();self.explicit([first['execution']]);original=copy.deepcopy(self.doc()['facts'][first['execution']])
        second=self.execute();self.assertNotEqual(first['execution'],second['execution'])
        self.assertEqual(self.doc()['facts'][first['execution']],original)
        self.assertTrue(w.view(self.root,self.ident)['eligible'])

    def test_new_failed_command_cannot_be_hidden_by_selected_old_success(self):
        self.plan['checks'][0]['cache']={'mode':'never','max_age_seconds':300};self.refresh()
        first=self.execute();self.explicit([first['execution']])
        # Same inputs, external nondeterministic failure: latest command still blocks.
        (self.root/'check.py').write_text('raise RuntimeError("synthetic failure")');self.refresh();self.execute()
        self.assertFalse(w.view(self.root,self.ident)['eligible'])

    def test_fact_recovery_is_paged_and_read_only(self):
        a=self.observe('C1','static_analysis',w.now(),'x'*10000,['app.py']);before=w.task_path(self.root,self.ident).read_bytes()
        body='';offset=0
        while offset is not None:
            page=w.detail(self.root,self.ident,'fact',a['fact'],offset,2000)
            body+=page['text'];offset=page['next_offset']
        self.assertEqual(json.loads(body)['id'],a['fact'])
        self.assertEqual(w.task_path(self.root,self.ident).read_bytes(),before)

    def test_reader_only_workflow_change_does_not_change_execution_identity(self):
        first=self.execute();old=self.execution()['producer'];copy_path=self.root/'reader-only.py'
        copy_path.write_text(Path(w.__file__).read_text()+'\n# reader-only change\n')
        with patch.object(w,'__file__',str(copy_path)):
            self.assertNotEqual(w.task_execution.producer(w.__file__),old)
            self.assertTrue(self.execute()['reused'])
        self.assertEqual(self.execution()['id'],first['execution']);self.assertEqual((self.root/'run-count').read_text(),'1')

    def test_actual_protocol_change_invalidates_without_predecessor_allowlist(self):
        self.execute()
        with patch.object(w.task_execution,'VERSION',999):
            self.assertFalse(self.execute()['reused'])
        self.assertEqual((self.root/'run-count').read_text(),'2')

    def test_unknown_execution_module_bytes_cannot_self_declare_same_version(self):
        self.execute();f=self.root/'modified-execution.py';f.write_text('VERSION=1\n# unknown implementation')
        with patch.object(w.task_execution,'__file__',str(f)):
            self.assertFalse(self.execute()['reused'])

    def test_log_contains_recoverable_identity_not_actual_environment_values(self):
        with patch.dict(w.os.environ,{'PRIVATE_PROBE':'never-print-secret'}):
            self.plan['checks'][0]['env_keys']=['PRIVATE_PROBE'];self.refresh();self.execute()
        record=self.execution();lines=(self.root/record['artifact']['path']).read_text().splitlines()
        start=json.loads(lines[1].removeprefix('Featrace start '))
        end=json.loads(lines[-1].removeprefix('Featrace result '))
        self.assertEqual(start['input_digest'],record['input_digest']);self.assertEqual(end['status'],'passed')
        self.assertNotIn('never-print-secret','\n'.join(lines));self.assertNotIn('argv',start)

    def test_observed_test_result_binds_actual_producer_and_original_time(self):
        run=self.execute();record=self.execution();(self.root/'result.xml').write_text('<testsuite tests="1"/>')
        fact=self.observe('C1','runtime_observation',record['at'],'Inspected actual fixture result',['result.xml'],producer=run['execution'])
        self.explicit([fact['fact']]);self.assertEqual(self.observation('C1')['producer'],run['execution'])
        self.assertTrue(w.view(self.root,self.ident)['eligible'])

    def test_old_xml_cannot_be_assigned_to_later_invocation(self):
        self.plan['checks'][0]['cache']={'mode':'never','max_age_seconds':300};self.refresh()
        self.execute();at=self.execution()['at'];self.execute();record=self.execution()
        with self.assertRaisesRegex(ValueError,'PRODUCER_NOT_APPLICABLE'):
            self.observe('C1','runtime_observation',at,'Old result',['app.py'],producer=record['id'])

    def test_record_budget_refuses_before_command_not_after_losing_new_result(self):
        self.execute();d=self.doc()
        self.plan['checks'][0]['cache']={'mode':'never','max_age_seconds':300};self.refresh();d=self.doc()
        d['request']='x'*(w.MAX_RECORD-len(json.dumps(d,ensure_ascii=False,indent=2).encode())-300)
        w.save(self.root,d);before=w.task_path(self.root,self.ident).read_bytes()
        with self.assertRaisesRegex(ValueError,'TASK_SIZE_LIMIT_BEFORE_EXECUTION'):self.execute()
        self.assertEqual((self.root/'run-count').read_text(),'1');self.assertEqual(before,w.task_path(self.root,self.ident).read_bytes())

    def test_execution_wrapper_change_is_part_of_protocol(self):
        self.execute();f=self.root/'changed-execution-wrapper.py'
        f.write_text(Path(w.__file__).read_text().replace("timeout=check['timeout']", "timeout=check['timeout']"))
        source=f.read_text();source=source.replace("budget=min(MAX_LOG,64*1024*1024-used)","budget=min(MAX_LOG,32*1024*1024-used)")
        f.write_text(source)
        with patch.object(w,'__file__',str(f)):self.assertFalse(self.execute()['reused'])

    def test_prune_preserves_selected_old_observation_and_negative_facts(self):
        self.proof([['runtime_observation']])
        a=self.observe('C1','runtime_observation',w.now(),'Original success',['app.py']);self.explicit([a['fact']])
        b=self.observe('C1','runtime_observation',w.now(),'Failure',['app.py'],'failed')
        c=self.observe('C1','runtime_observation',w.now(),'Repair observed',['app.py'])
        before=w.task_path(self.root,self.ident).read_bytes();w.prune(self.root,self.ident)
        self.assertEqual(before,w.task_path(self.root,self.ident).read_bytes());w.prune(self.root,self.ident,True)
        self.assertTrue({a['fact'],b['fact'],c['fact']}<=set(self.doc()['facts']))

    def test_prune_removes_only_unreferenced_success_not_files(self):
        self.proof([['static_analysis']])
        first=self.observe('C1','static_analysis',w.now(),'Superseded unadopted',['app.py'])
        self.observe('C1','static_analysis',w.now(),'Current',['app.py'])
        self.assertEqual(w.prune(self.root,self.ident)['removable_fact_count'],1)
        w.prune(self.root,self.ident,True);self.assertNotIn(first['fact'],self.doc()['facts']);self.assertTrue((self.root/'app.py').exists())

    def test_correction_roots_survive_prune(self):
        self.execute();self.support();w.close(self.root,self.ident,[])
        w.correct(self.root,self.ident,['C1'],'Specific error','Synthetic approval')
        old=self.execution()['id'];self.execute();w.prune(self.root,self.ident,True)
        self.assertIn(old,self.doc()['facts'])

    def test_fact_count_limit_is_atomic_and_cached_result_remains_usable(self):
        self.execute();d=self.doc();one=copy.deepcopy(self.execution())
        for n in range(1,w.MAX_FACTS):
            f=copy.deepcopy(one);f['id']='synthetic-'+str(n);d['facts'][f['id']]=f
        # This fixture measures count protection independently of the byte cap.
        with patch.object(w,'MAX_RECORD',1024*1024):
            w.save(self.root,d);before=w.task_path(self.root,self.ident).read_bytes()
            self.assertTrue(self.execute()['reused'])
            with self.assertRaisesRegex(ValueError,'FACT_LIMIT'):
                self.observe('C1','runtime_observation',w.now(),'Too many',['app.py'])
            self.assertEqual(before,w.task_path(self.root,self.ident).read_bytes())

    def test_old_contract_refuses_without_rewrite_or_migration(self):
        for contract in (1,2):
            d=json.loads(w.task_path(self.root,self.ident).read_text());d['task_contract']=contract
            d['checksum']=w.digest({k:v for k,v in d.items() if k!='checksum'})
            w.task_path(self.root,self.ident).write_text(json.dumps(d));before=w.task_path(self.root,self.ident).read_bytes()
            with self.assertRaisesRegex(ValueError,'PINNED_TOOL'):w.view(self.root,self.ident)
            self.assertEqual(before,w.task_path(self.root,self.ident).read_bytes())

    def test_fresh_process_recovers_selected_facts_without_reexecution(self):
        self.execute();self.support();before=w.task_path(self.root,self.ident).read_bytes()
        result=subprocess.run([sys.executable,w.__file__,'status',str(self.root),self.ident],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertTrue(json.loads(result.stdout)['eligible']);self.assertEqual(before,w.task_path(self.root,self.ident).read_bytes())
        self.assertEqual((self.root/'run-count').read_text(),'1')

    def test_independent_provenance_selects_subset_not_all_candidates(self):
        self.proof([['runtime_observation']]);self.plan['review']={'independent':True,'reason':'Selected synthetic risk','criteria':['C1']};self.refresh()
        first=self.observe('C1','runtime_observation',w.now(),'Actual selected view',['app.py'])
        self.observe('C1','runtime_observation',w.now(),'Extra unselected view',['app.py'])
        proof=w.review_input(self.root,self.ident,'C1');proof.update(facts=[first['fact']],verdict='supported',fresh_context=True,
            host='synthetic',context_id='isolated-fixture',reviewer='fixture',reason='Only this selected fact supports the scoped claim')
        name='.featrace/proof.json';(self.root/name).write_text(json.dumps(proof))
        w.assess(self.root,self.ident,'C1','supported','Explicit scoped proof',True,name,[first['fact']])
        self.assertTrue(w.view(self.root,self.ident)['eligible'])

    def test_missing_or_invalid_proof_requirement_is_not_silently_inferred(self):
        for proof in (None,{'any_of':[],'reason':'empty'},{'any_of':[['imagined']],'reason':'unknown kind'}):
            plan=copy.deepcopy(self.plan)
            if proof is None:plan['criteria'][0].pop('proof')
            else:plan['criteria'][0]['proof']=proof
            before=w.task_path(self.root,self.ident).read_bytes()
            with self.assertRaises(ValueError):w.set_plan(self.root,self.ident,plan)
            self.assertEqual(before,w.task_path(self.root,self.ident).read_bytes())

    def test_byte_limit_refuses_atomic_observation_without_overwriting_prior_facts(self):
        before=w.task_path(self.root,self.ident).read_bytes()
        with self.assertRaisesRegex(ValueError,'TASK_SIZE_LIMIT'):
            self.observe('C1','runtime_observation',w.now(),'x'*w.MAX_RECORD,['app.py'])
        self.assertEqual(before,w.task_path(self.root,self.ident).read_bytes())


for _name in list(dir(EvidenceCoreTests)):
    if _name.startswith('test_') and _name not in EvidenceCoreTests.__dict__:setattr(EvidenceCoreTests,_name,None)
del TaskWorkflowTests
