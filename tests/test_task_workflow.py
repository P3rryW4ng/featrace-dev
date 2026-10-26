import copy
from datetime import datetime, timezone, timedelta
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

CORE=Path(__file__).resolve().parents[1]/'skills/dev/core/scripts'
if not CORE.exists(): CORE=Path('/Users/mac/Entrepôt/featrace-dev/skills/dev/core/scripts')
sys.path.insert(0,str(CORE))
import task_workflow as w

def fixture_proofs(plan):
    for c in plan['criteria']:
        c.setdefault('proof',{'any_of':[['command'],['runtime_observation'],['static_analysis']],
                             'reason':'Synthetic fixture has explicit evidence chosen by its individual test'})

class TaskWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.git('init','-q');self.git('config','user.name','Synthetic');self.git('config','user.email','synthetic@example.invalid')
        (self.root/'.gitignore').write_text('run-count\nother-count\n__pycache__/\n')
        (self.root/'app.py').write_text('label="before"\n')
        (self.root/'check.py').write_text('from pathlib import Path\np=Path("run-count")\np.write_text(str(int(p.read_text())+1) if p.exists() else "1")\nassert "after" in Path("app.py").read_text()\nprint("checked")\n')
        (self.root/'rules.md').write_text('Use targeted tests.\n')
        w.task_policy.prepare(self.root,{'policy_contract':1,'authority':'Synthetic fixture grant','timezone':'UTC','retention_days':7,'cleanup':'manual','handoff':None,'rules':[]},w.git)
        self.git('add','.');self.git('commit','-qm','baseline')
        self.ident='UI-1';w.begin(self.root,self.ident,'Change one local label; no business behavior changes.')
        (self.root/'app.py').write_text('label="after"\n')
        self.plan={'reason':'Inspected single use and unchanged state/callbacks; synthetic fixture.',
            'categories':['presentation'],'scope':['app.py','check.py'],'exclusions':{},
            'constraints':{'rules.md':'Targeted execution authorized in fixture'},'unknowns':[],
            'criteria':[{'id':'C1','expected':'The label is after','kind':'changed','inputs':['app.py']}],
            'checks':[{'id':'target','argv':[sys.executable,'check.py'],'inputs':['app.py','check.py'],
                'covers':['C1'],'reason':'Executable assertion for this label only','timeout':5,'environment':{'target':'synthetic local Python','kind':'local'}}],
            'review':{'independent':False,'reason':'Local presentation; no shared behavior changed'}}
        fixture_proofs(self.plan)
        w.set_plan(self.root,self.ident,self.plan)

    def git(self,*args):
        result=subprocess.run(['git','-C',str(self.root),*args],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr);return result.stdout

    def doc(self):return w.load(self.root,self.ident)
    def execute(self):return w.run_check(self.root,self.ident,'target')
    def execution(self):
        d=self.doc();return d['facts'][d['executions']['target']]
    def observation(self,c):
        d=self.doc();return d['facts'][d['observations'][c]]
    def runtime_failure(self,c):
        return next(iter(w.task_failures.pending(self.doc(),c).values()))
    def resolve(self,c='C1',failure=None,evidence=None):
        d=self.doc();pending=w.task_failures.pending(d,c)
        fid=failure or next(iter(pending))
        pid=evidence or d['observations'][c]
        return w.failure_action(self.root,self.ident,fid,'resolve','Inspected same synthetic reproduction conditions',[pid])

    def assess(self,c,*args,**kwargs):
        criterion=next(x for x in self.doc()['plan']['criteria'] if x['id']==c)
        kwargs.setdefault('fact_ids',w.facts(self.root,self.doc(),criterion))
        return w.assess(self.root,self.ident,c,*args,**kwargs)
    def support(self):return self.assess('C1','supported','Actual selected assertion covers this criterion.')
    def close(self):self.execute();self.support();return w.close(self.root,self.ident,['Synthetic local environment only'])
    def refresh(self):
        fixture_proofs(self.plan)
        w.set_plan(self.root,self.ident,self.plan)
    def observe(self,*args,**kwargs):
        kwargs.setdefault("target","synthetic current fixture, not a real device")
        if args[1]=='runtime_observation':kwargs.setdefault('conditions',{'case':'default fixture'})
        return w.observe(self.root,self.ident,*args,**kwargs)

    def test_vertical_closure_has_no_legacy_files(self):
        self.close();self.assertEqual(w.view(self.root,self.ident)['state'],'complete')
        self.assertFalse((self.root/'.agent-workflow').exists())
        self.assertFalse(list((self.root/'.featrace').rglob('verification.json')))
        self.assertEqual((self.root/'run-count').read_text(),'1')

    def test_repeated_check_reuses_actual_success(self):
        first=self.execute();second=self.execute()
        self.assertEqual(first['execution'],second['execution']);self.assertTrue(second['reused'])
        self.assertEqual((self.root/'run-count').read_text(),'1')

    def test_status_does_not_execute_or_write(self):
        before=w.task_path(self.root,self.ident).read_bytes();w.view(self.root,self.ident)
        self.assertFalse((self.root/'run-count').exists());self.assertEqual(before,w.task_path(self.root,self.ident).read_bytes())

    def test_other_criterion_wording_does_not_rerun_check(self):
        self.execute();self.plan['criteria'][0]['expected']='The same label is visibly after'
        self.refresh();self.assertTrue(self.execute()['reused'])
        self.assertEqual((self.root/'run-count').read_text(),'1')

    def test_changed_criterion_requires_new_assessment_but_reuses_check(self):
        self.execute();self.support();self.plan['criteria'][0]['expected']='The actual after label'
        self.refresh();self.assertFalse(w.view(self.root,self.ident)['eligible']);self.assertTrue(self.execute()['reused'])
        self.support();self.assertTrue(w.view(self.root,self.ident)['eligible'])

    def test_input_change_invalidates_execution(self):
        self.execute();(self.root/'app.py').write_text('label="after, revised"\n');self.refresh()
        self.assertFalse(self.execute()['reused']);self.assertEqual((self.root/'run-count').read_text(),'2')

    def test_environment_change_invalidates_execution(self):
        self.execute();self.plan['checks'][0]['environment']['target']='different declared environment';self.refresh()
        self.assertFalse(self.execute()['reused'])

    def test_executable_bytes_are_inputs_even_if_path_stays_same(self):
        runner=self.root/'runner';runner.write_text('#!/bin/sh\nexit 0\n');runner.chmod(0o755)
        self.plan['scope'].append('runner');self.plan['checks'][0]['argv']=['./runner'];self.refresh();self.execute()
        runner.write_text('#!/bin/sh\nexit 1\n');self.refresh()
        self.assertEqual(self.execute()['status'],'failed')

    def test_edited_constraint_invalidates_current_inputs(self):
        self.execute();(self.root/'rules.md').write_text('Updated applicable rules\n')
        with self.assertRaisesRegex(ValueError,'SCOPE_REVIEW'):self.execute()
        self.plan['exclusions']['rules.md']='Rules are reviewed as authority, not business behavior';self.refresh()
        self.assertFalse(self.execute()['reused'])

    def test_outside_scope_change_is_visible_not_automatic_reacceptance(self):
        self.execute();self.support()
        (self.root/'new.py').write_text('separate_task=1')
        self.assertGreater(w.view(self.root,self.ident)['outside_scope_change_count'],0)
        self.assertTrue(w.view(self.root,self.ident)['eligible'])
        self.assertTrue(self.execute()['reused'])

    def test_excluded_unrelated_file_drift_does_not_stale_task(self):
        (self.root/'other.py').write_text('separate=1');self.plan['exclusions']={'other.py':'Separate task, no imports or shared behavior in fixture'};self.refresh()
        self.execute();self.support();(self.root/'other.py').write_text('separate=2')
        self.assertTrue(self.execute()['reused']);self.assertTrue(w.view(self.root,self.ident)['eligible'])

    def test_unrelated_committed_head_does_not_rerun_selected_check(self):
        self.execute();self.git('add','app.py');self.git('commit','-qm','label')
        self.assertTrue(self.execute()['reused'])

    def test_scope_unknown_refuses_execution(self):
        self.plan['unknowns']=['Dynamic caller unresolved'];self.refresh()
        with self.assertRaisesRegex(ValueError,'SCOPE_UNKNOWN'):self.execute()

    def test_shared_scope_does_not_alone_require_independent_review(self):
        self.plan['categories']=['presentation','shared']
        self.plan['review']={'independent':False,'criteria':[],
                             'reason':'Known local callers; targeted proof sufficient, no mandatory independent rule'}
        self.refresh();self.execute();self.support()
        self.assertTrue(w.view(self.root,self.ident)['eligible'])

    def test_failed_check_cannot_be_turned_green_by_assessment(self):
        (self.root/'app.py').write_text('label="before"\n');self.refresh()
        self.assertEqual(self.execute()['status'],'failed')
        with self.assertRaisesRegex(ValueError,'CURRENT_FACT|SUPPORT_SELECTION_REQUIRED'):self.support()
        with self.assertRaisesRegex(ValueError,'DELIVERY_BLOCKED'):w.close(self.root,self.ident,[])

    def test_failed_check_cannot_be_removed_from_plan_to_escape_failure(self):
        (self.root/'app.py').write_text('label="before"');self.refresh();self.execute()
        self.plan['checks']=[]
        with self.assertRaisesRegex(ValueError,'UNRESOLVED_CHECK_REMOVED'):self.refresh()

    def test_observed_failure_blocks_even_with_a_passing_check(self):
        self.execute()
        self.observe('C1','runtime_observation',w.now(),'Synthetic actual visual failure',['app.py'],'failed')
        self.support();self.assertFalse(w.view(self.root,self.ident)['eligible'])
        self.observe('C1','runtime_observation',w.now(),'Synthetic targeted verification passed',['app.py'])
        self.assertFalse(w.view(self.root,self.ident)['eligible']);self.resolve()
        self.support();self.assertTrue(w.view(self.root,self.ident)['eligible'])
        self.assertEqual(self.doc()['facts'][self.observation('C1')['previous_failure']]['status'],'failed')

    def test_failed_observation_cannot_be_removed_with_criterion(self):
        self.observe('C1','runtime_observation',w.now(),'Synthetic failure',['app.py'],'failed')
        self.plan['criteria'][0]['id']='C2';self.plan['checks'][0]['covers']=['C2']
        with self.assertRaisesRegex(ValueError,'UNRESOLVED_OBSERVATION_REMOVED'):self.refresh()

    def test_actual_runtime_failure_cannot_be_cleared_by_static_no_influence(self):
        self.plan['criteria'][0]['kind']='unaffected';self.refresh()
        self.observe('C1','runtime_observation',w.now(),'Actual synthetic regression',['app.py'],'failed')
        self.observe('C1','static_analysis',w.now(),'Merely inferred no influence',['app.py'])
        with self.assertRaisesRegex(ValueError,'TARGETED_RUNTIME_PROOF_REQUIRED'):self.resolve()
        self.assertFalse(w.view(self.root,self.ident)['eligible'])

    def test_check_cannot_omit_declared_criterion_dependency(self):
        self.plan['checks'][0]['inputs']=['check.py']
        with self.assertRaisesRegex(ValueError,'MISSING_CRITERION_INPUTS'):self.refresh()

    def test_targeted_pass_resolves_failure_without_erasing_original_artifact(self):
        (self.root/'app.py').write_text('label="before"\n');self.refresh();failed=self.execute()
        old=self.execution()['artifact']['path']
        (self.root/'app.py').write_text('label="after"\n');self.refresh();self.close()
        self.assertTrue((self.root/old).exists())
        self.assertEqual(self.execution()['previous_failure'],failed['execution'])

    def test_log_corruption_prevents_reuse(self):
        self.execute();ref=self.execution()['artifact'];(self.root/ref['path']).write_text('tampered')
        self.assertFalse(self.execute()['reused'])

    def test_timeout_records_unavailable(self):
        self.plan['checks'][0]['argv']=[sys.executable,'-c','import time;time.sleep(10)'];self.plan['checks'][0]['timeout']=1;self.refresh()
        self.assertEqual(self.execute()['status'],'unavailable');self.assertFalse(w.view(self.root,self.ident)['eligible'])

    def test_interrupt_reaps_owned_child_and_never_saves_a_pass(self):
        real=w.subprocess.Popen;child=MagicMock();child.pid=999999;child.poll.side_effect=KeyboardInterrupt
        argv=self.plan['checks'][0]['argv']
        def spawn(command,**kwargs):return child if command==argv else real(command,**kwargs)
        with patch.object(w.subprocess,'Popen',side_effect=spawn),patch.object(w.os,'killpg') as kill:
            with self.assertRaises(KeyboardInterrupt):self.execute()
        kill.assert_called_once_with(child.pid,w.task_execution.signal.SIGKILL);child.wait.assert_called()
        self.assertEqual(self.execution()['status'],'unavailable')
        self.assertEqual(self.execution()['reason'],'EXECUTION_INTERRUPTED')

    def test_monitor_io_error_reaps_owned_child_and_records_unavailable(self):
        real=w.subprocess.Popen;child=MagicMock();child.pid=999999;child.poll.side_effect=OSError('synthetic monitor failure')
        argv=self.plan['checks'][0]['argv']
        def spawn(command,**kwargs):return child if command==argv else real(command,**kwargs)
        with patch.object(w.subprocess,'Popen',side_effect=spawn),patch.object(w.os,'killpg') as kill:
            result=self.execute()
        kill.assert_called_once_with(child.pid,w.task_execution.signal.SIGKILL);child.wait.assert_called()
        self.assertEqual(result['status'],'unavailable')

    def test_input_drift_during_execution_is_not_a_pass(self):
        self.plan['checks'][0]['argv']=[sys.executable,'-c','from pathlib import Path;Path("app.py").write_text("after drift")'];self.refresh()
        self.assertEqual(self.execute()['status'],'unavailable')

    def test_static_analysis_does_not_satisfy_runtime_proof(self):
        self.plan['criteria'][0]['proof']={'any_of':[['runtime_observation']], 'reason':'Actual new rendering needs observation'};self.refresh()
        fact=self.observe('C1','static_analysis',w.now(),'Only inspected code',['app.py'])
        with self.assertRaisesRegex(ValueError,'PROOF_REQUIREMENTS_UNMET'):
            w.assess(self.root,self.ident,'C1','supported','Not rendering proof',fact_ids=[fact['fact']])

    def test_static_unaffected_claim_needs_no_extra_runtime(self):
        self.plan['criteria'].append({'id':'C2','expected':'Existing callbacks unaffected','kind':'unaffected','inputs':['app.py']});self.refresh()
        self.observe('C2','static_analysis',w.now(),'Fixture diff excludes callbacks; no runtime claim',['app.py'])
        self.assess('C2','supported','Static exclusion adequate for unchanged behavior')
        self.close();self.assertEqual((self.root/'run-count').read_text(),'1')

    def test_future_observation_refuses(self):
        with self.assertRaisesRegex(ValueError,'FUTURE'):
            self.observe('C1','runtime_observation','2999-01-01T00:00:00+00:00','Not observed',['app.py'])

    def test_observation_predating_task_cannot_be_signed_as_current(self):
        with self.assertRaisesRegex(ValueError,'OBSERVATION_PREDATES_TASK'):
            w.observe(self.root,self.ident,'C1','runtime_observation','2020-01-01T00:00:00+00:00','Old observation is not current',['app.py'])

    def test_runtime_observation_requires_actual_target_identity(self):
        with self.assertRaisesRegex(ValueError,'OBSERVED_TARGET_REQUIRED'):
            w.observe(self.root,self.ident,'C1','runtime_observation',w.now(),'Target unknown',['app.py'])

    def test_evidence_drift_invalidates_observation(self):
        self.observe('C1','runtime_observation',w.now(),'Synthetic observed',['app.py'])
        self.support();(self.root/'app.py').write_text('different');self.refresh()
        self.assertFalse(w.view(self.root,self.ident)['eligible'])

    def test_missing_independent_review_blocks_close(self):
        self.plan['review']={'independent':True,'reason':'Required by fixture constraint'};self.refresh();self.execute();self.support()
        self.assertFalse(w.view(self.root,self.ident)['eligible'])

    def test_fake_independent_provenance_refuses(self):
        self.execute();path=self.root/'.featrace/proof.json';path.write_text('{}')
        with self.assertRaisesRegex(ValueError,'PROVENANCE_INVALID'):
            self.assess('C1','supported','claimed independent',True,'.featrace/proof.json')

    def test_independent_structural_provenance_binds_exact_facts(self):
        self.plan['review']={'independent':True,'reason':'Fixture-only structural check'};self.refresh();self.execute()
        doc=self.doc();c=self.plan['criteria'][0]
        proof={'task':self.ident,'criterion':'C1','criterion_digest':w.criterion_stamp(self.root,doc,c),
               'facts':w.facts(self.root,doc,c),'verdict':'supported','fresh_context':True,
               'host':'synthetic host','context_id':'synthetic-context','reviewer':'synthetic reviewer','reason':'Synthetic structure only, not a real Agent review'}
        path=self.root/'.featrace/proof.json';path.write_text(json.dumps(proof))
        self.assess('C1','supported','Fixture provenance validates fields only',True,'.featrace/proof.json')
        self.assertTrue(w.view(self.root,self.ident)['eligible'])

    def test_closed_result_is_as_of_not_recertification_of_future_code(self):
        self.close();(self.root/'app.py').write_text('future change')
        result=w.view(self.root,self.ident);self.assertEqual(result['state'],'complete');self.assertFalse(result['current_revision_certified'])
        with self.assertRaisesRegex(ValueError,'ALREADY_COMPLETE'):self.refresh()

    def test_second_close_does_not_run_anything(self):
        receipt=self.close();self.assertEqual(w.close(self.root,self.ident,[]),receipt)
        self.assertEqual((self.root/'run-count').read_text(),'1')

    def test_unsafe_task_id_refuses(self):
        with self.assertRaisesRegex(ValueError,'INVALID_TASK'):w.begin(self.root,'../outside','request')

    def test_symlink_scope_refuses_but_unrelated_symlink_does_not(self):
        (self.root/'link').symlink_to('rules.md');self.git('add','link');self.git('commit','-qm','unrelated link')
        self.plan['exclusions']['link']='Unrelated AI discovery link'
        with self.assertRaisesRegex(ValueError,'SYMLINK'):self.refresh()

    def test_unrelated_preexisting_symlink_is_not_scanned(self):
        # A fresh task starts from the current baseline, without whole-tree symlink scanning.
        (self.root/'link').symlink_to('rules.md');self.git('add','link');self.git('commit','-qm','unrelated link')
        w.begin(self.root,'UI-2','New task');w.set_plan(self.root,'UI-2',self.plan)
        self.assertEqual(w.run_check(self.root,'UI-2','target')['status'],'passed')

    def test_runtime_target_and_registration_revision_are_distinct(self):
        self.observe('C1','runtime_observation',w.now(),'Synthetic local observation',['app.py'])
        fact=self.observation('C1')
        self.assertIn('observed_target',fact);self.assertIn('git_head_at_registration',fact)
        self.assertNotIn('tested_revision',fact)

    def test_duplicate_keys_and_oversized_task_refuse(self):
        p=self.root/'bad.json';p.write_text('{"id":1,"id":2}')
        with self.assertRaisesRegex(ValueError,'DUPLICATE'):w.read_json(p)
        doc=self.doc();doc['request']='x'*(w.MAX_RECORD+1)
        with self.assertRaisesRegex(ValueError,'SIZE_LIMIT'):w.save(self.root,doc)

    def test_task_tampering_refuses(self):
        p=w.task_path(self.root,self.ident);value=json.loads(p.read_text());value['request']='changed';p.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'TASK_CHANGED'):self.doc()

    def test_same_task_lock_blocks_concurrent_writer(self):
        with w.locked(self.root,self.ident):
            with self.assertRaisesRegex(ValueError,'TASK_BUSY'):self.execute()

    def test_new_process_resumes_without_conversation_or_reexecution(self):
        self.execute();self.support()
        command=[sys.executable,str(CORE/'task_workflow.py'),'status',str(self.root),self.ident]
        result=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(json.loads(result.stdout)['eligible'])
        self.assertEqual((self.root/'run-count').read_text(),'1')

    def test_cli_begin_succeeds_but_draft_status_returns_not_ready(self):
        script=str(CORE/'task_workflow.py')
        created=subprocess.run([sys.executable,script,'begin',str(self.root),'CLI-NEW','--request','Synthetic request'],capture_output=True,text=True)
        self.assertEqual(created.returncode,0,created.stdout)
        status=subprocess.run([sys.executable,script,'status',str(self.root),'CLI-NEW'],capture_output=True,text=True)
        self.assertEqual(status.returncode,2);self.assertEqual(json.loads(status.stdout)['state'],'draft')

    def test_cli_refusal_reports_specific_code_without_echoing_input(self):
        secret='synthetic_private_argument'
        result=subprocess.run([sys.executable,str(CORE/'task_workflow.py'),'status',str(self.root),self.ident,'--'+secret],capture_output=True,text=True)
        self.assertEqual(result.returncode,2);self.assertEqual(json.loads(result.stdout)['reason'],'INVALID_ARGUMENTS')
        self.assertNotIn(secret,result.stdout+result.stderr)

    def test_paging_does_not_hide_tail_gap(self):
        self.plan['criteria']=[{'id':f'C{i}','expected':'separate requirement','kind':'changed','inputs':['app.py']} for i in range(60)]
        self.plan['checks'][0]['covers']=['C0'];self.refresh()
        page=w.view(self.root,self.ident,0,25)
        self.assertEqual(page['total'],60);self.assertEqual(page['next_offset'],25);self.assertEqual(page['blocker_count'],61)
        tail=w.view(self.root,self.ident,50,25,50)
        self.assertIn('CLAIM:C59',tail['blockers']);self.assertFalse(tail['eligible'])

    def age(self):
        doc=self.doc();doc['receipt']['completed_at']=(datetime.now(timezone.utc)-timedelta(days=8)).isoformat();w.save(self.root,doc)

    def test_cleanup_preview_and_apply_only_after_completion_and_retention(self):
        with self.assertRaisesRegex(ValueError,'REQUIRES_COMPLETE'):w.cleanup(self.root,self.ident)
        self.close()
        with self.assertRaisesRegex(ValueError,'RETENTION'):w.cleanup(self.root,self.ident)
        self.age();before=w.task_path(self.root,self.ident).read_bytes();preview=w.cleanup(self.root,self.ident)
        self.assertEqual(preview['owned_logs'],1);self.assertEqual(before,w.task_path(self.root,self.ident).read_bytes())
        w.cleanup(self.root,self.ident,True);self.assertEqual((self.root/'app.py').read_text(),'label="after"\n')
        self.assertEqual(w.view(self.root,self.ident)['state'],'complete');self.assertLess(w.task_path(self.root,self.ident).stat().st_size,2000)

    def test_cleanup_refuses_unknown_artifacts(self):
        self.close();self.age();folder=self.root/'.featrace/artifacts'/self.ident
        (folder/'user-file.txt').write_text('do not delete')
        with self.assertRaisesRegex(ValueError,'UNKNOWN_ARTIFACT'):w.cleanup(self.root,self.ident,True)
        self.assertTrue((folder/'user-file.txt').exists())

    def test_forget_requires_limitations_handoff_and_removes_task_record(self):
        self.close();self.age()
        with self.assertRaisesRegex(ValueError,'HANDOFF_REQUIRED'):w.cleanup(self.root,self.ident,True,forget=True)
        path=self.root/'constraints.md';path.write_text('Synthetic local environment only\n')
        w.cleanup(self.root,self.ident,True,forget=True,handoff='constraints.md')
        self.assertFalse(w.task_path(self.root,self.ident).exists());self.assertTrue(path.exists());self.assertTrue((self.root/'app.py').exists())

    def test_forget_without_limitations_needs_no_permanent_delivery_file(self):
        self.execute();self.support();w.close(self.root,self.ident,[]);self.age()
        w.cleanup(self.root,self.ident,True,forget=True)
        self.assertFalse(w.task_path(self.root,self.ident).exists())

    def test_no_legacy_module_imports(self):
        import ast
        names={a.name for n in ast.walk(ast.parse((CORE/'task_workflow.py').read_text())) if isinstance(n,(ast.Import,ast.ImportFrom)) for a in n.names}
        self.assertFalse(names & {'acceptance_contract','verification','verification_policy','module_context','check_runs'})

    def test_locate_is_a_readonly_candidate_query(self):
        before=w.task_path(self.root,self.ident).read_bytes();result=w.locate(self.root,'app')
        self.assertIn('app.py',result['paths']);self.assertIn('not a semantic',result['boundary'])
        self.assertEqual(before,w.task_path(self.root,self.ident).read_bytes())

    def test_list_is_paged_and_does_not_certify_recorded_state(self):
        before=w.task_path(self.root,self.ident).read_bytes();result=w.task_list(self.root)
        self.assertEqual(result['total'],1);self.assertEqual(result['items'][0]['recorded_state'],'planned')
        self.assertIn('No tests executed',result['boundary']);self.assertEqual(before,w.task_path(self.root,self.ident).read_bytes())

if __name__=='__main__':unittest.main()
