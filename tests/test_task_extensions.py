import copy
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from test_task_workflow import TaskWorkflowTests
import task_workflow as w

class FullReplacementTests(TaskWorkflowTests):
    # Only this class's tests count: inherited regression cases are kept in their original class.
    def policy(self,mode='forget',rules=None):
        return {'policy_contract':1,'authority':'Synthetic explicit project test grant','timezone':'Asia/Shanghai',
                'retention_days':7,'cleanup':mode,'handoff':None,'rules':rules or []}

    def configure(self,config):
        w.task_policy.prepare(self.root,config,w.git)

    def broad(self):
        self.plan['checks'][0]['inputs']=[]
        self.plan['checks'][0]['input_sets']=[{'kind':'git_tree','path':'.'}]
        self.refresh()

    def test_build_input_breadth_does_not_expand_semantic_claims(self):
        (self.root/'library.py').write_text('build_dependency=1')
        self.plan['exclusions']['library.py']='No rendered effect; still compiler input'
        self.broad();self.execute();self.support()
        (self.root/'library.py').write_text('build_dependency=2');self.refresh()
        self.assertFalse(self.execute()['reused'])
        self.assertEqual(len(self.doc()['plan']['criteria']),1)
        self.assertEqual((self.root/'run-count').read_text(),'2')

    def test_input_group_includes_new_files_and_ignores_build_outputs(self):
        self.broad();self.execute()
        (self.root/'other.py').write_text('unrelated=1');self.plan['exclusions']['other.py']='Separate implementation; build may read it';self.refresh()
        self.assertFalse(self.execute()['reused'])
        (self.root/'__pycache__').mkdir();(self.root/'__pycache__/generated').write_text('ignored')
        self.assertTrue(self.execute()['reused'])

    def test_transient_group_handles_more_than_512_source_paths_without_manifest(self):
        d=self.root/'lib';d.mkdir()
        for i in range(700):(d/f'f{i}.txt').write_text(str(i))
        self.git('add','lib');self.git('commit','-qm','large input fixture')
        self.plan['exclusions'].update({f'lib/f{i}.txt':'Independent library source' for i in range(700)})
        # Scope exclusions need not persist 700 names in normal projects: begin AFTER an unrelated baseline commit.
        w.begin(self.root,'LARGE','Target label');self.ident='LARGE'
        self.plan['exclusions']={};self.broad();self.execute()
        self.assertLess(w.task_path(self.root,self.ident).stat().st_size,12000)
        self.assertNotIn('f699.txt',w.task_path(self.root,self.ident).read_text())

    def test_external_toolchain_bytes_and_environment_invalidate_check(self):
        with __import__('tempfile').TemporaryDirectory() as folder:
            path=Path(folder)/'release';path.write_text('jdk=synthetic1')
            c=self.plan['checks'][0];c['external_inputs']=[{'kind':'file','path':str(path)}];c['env_keys']=['FEATRACE_SYNTHETIC_ENV']
            self.refresh();self.execute();path.write_text('jdk=synthetic2')
            self.assertFalse(self.execute()['reused'])
            with patch.dict(os.environ,{'FEATRACE_SYNTHETIC_ENV':'not-persisted-value'}):
                self.assertFalse(self.execute()['reused'])
                self.assertNotIn('not-persisted-value',w.task_path(self.root,self.ident).read_text())

    def test_missing_external_and_explicit_inputs_cannot_certify(self):
        self.plan['checks'][0]['inputs'].append('missing.py');self.refresh()
        with self.assertRaisesRegex(ValueError,'INPUT_MISSING'):self.execute()

    def test_managed_directory_link_accepted_only_when_declared_in_build_set(self):
        d=self.root/'.agents/skills/example';d.mkdir(parents=True);(d/'SKILL.md').write_text('actual source')
        link=self.root/'.claude/skills/example';link.parent.mkdir(parents=True);link.symlink_to('../../.agents/skills/example',target_is_directory=True)
        self.git('add','.agents','.claude');self.git('commit','-qm','managed skills')
        self.plan['exclusions'].update({'.agents/skills/example/SKILL.md':'Tool instructions separate','.claude/skills/example':'Managed discovery alias'})
        # file exclusion hashing deliberately refuses a link: unrelated links need not be in local semantic scope.
        w.begin(self.root,'LINK','Local label');self.ident='LINK';self.plan['exclusions']={};self.broad()
        self.assertEqual(self.execute()['status'],'passed')

    def test_outside_or_dangling_link_in_selected_build_set_refuses(self):
        link=self.root/'link';link.symlink_to('/tmp')
        self.git('add','link');self.git('commit','-qm','unsafe fixture link')
        w.begin(self.root,'BADLINK','Local label');self.ident='BADLINK';self.broad()
        with self.assertRaisesRegex(ValueError,'LINK_OUTSIDE'):self.execute()

    def test_file_group_cannot_omit_criterion_input(self):
        self.plan['checks'][0]['inputs']=[];self.plan['checks'][0]['input_sets']=[{'kind':'git_tree','path':'check.py'}]
        with self.assertRaisesRegex(ValueError,'MISSING_CRITERION'):self.refresh()

    def test_mutable_environment_requires_non_reusable_bounded_result(self):
        c=self.plan['checks'][0];c['environment'].update(kind='device',policy_environment='test')
        with self.assertRaisesRegex(ValueError,'MUTABLE_ENVIRONMENT'):self.refresh()
        c['cache']={'mode':'never','max_age_seconds':60};self.refresh();self.execute()
        self.assertFalse(self.execute()['reused']);self.support();self.assertTrue(w.view(self.root,self.ident)['eligible'])
        doc=self.doc();doc['executions']['target']['at']=(datetime.now(timezone.utc)-timedelta(seconds=61)).isoformat();w.save(self.root,doc)
        self.assertFalse(w.view(self.root,self.ident)['eligible'])

    def test_policy_standing_grant_applies_only_to_matching_scope_environment(self):
        rules=[{'source':'rules.md','sha256':'prepared','paths':['app.py'],'operations':['test'],'environment':'test',
                'decision':'Only test sandbox execution','permission':'allowed','authority':'Synthetic same-scope grant'}]
        self.configure(self.policy(rules=rules));self.plan['checks'][0]['environment']['kind']='test';self.refresh()
        self.assertEqual(self.execute()['status'],'passed')
        rules[0]['permission']='denied';self.configure(self.policy(rules=rules));self.refresh()
        with self.assertRaisesRegex(ValueError,'POLICY_DENIED'):self.execute()
        self.plan['checks'][0]['environment']['kind']='local';self.refresh()
        self.assertEqual(self.execute()['status'],'passed')

    def test_changed_applicable_rule_needs_reconciliation_not_blanket_permission(self):
        r={'source':'rules.md','sha256':'prepared','paths':['app.py'],'operations':['test'],'environment':'any',
           'decision':'Target test','permission':'allowed','authority':'Synthetic grant'}
        self.configure(self.policy(rules=[r]));self.refresh();self.execute()
        (self.root/'rules.md').write_text('Different rule')
        with self.assertRaisesRegex(ValueError,'RULE_CHANGED'):self.refresh()
        self.configure(self.policy(rules=[r]));self.refresh();self.assertFalse(self.execute()['reused'])

    def test_policy_setup_preserves_user_ignore_and_refuses_owned_block_conflict(self):
        original=(self.root/'.gitignore').read_text();self.configure(self.policy())
        self.assertEqual((self.root/'.gitignore').read_text(),original)
        with (self.root/'.gitignore').open('a') as f:f.write(w.task_policy.START+'\ncustom\n')
        before=(self.root/'.gitignore').read_bytes()
        with self.assertRaisesRegex(ValueError,'CONFLICT'):self.configure(self.policy())
        self.assertEqual((self.root/'.gitignore').read_bytes(),before)

    def test_tracked_local_task_data_prevents_silent_ignore_setup(self):
        self.git('add','-f',str(w.task_path(self.root,self.ident)))
        with self.assertRaisesRegex(ValueError,'TRACKED'):self.configure(self.policy())

    def test_automatic_retention_forgets_expired_task_without_new_per_task_prompt(self):
        self.configure(self.policy());self.refresh();self.execute();self.support();w.close(self.root,self.ident,[]);self.age()
        w.begin(self.root,'NEXT','Next authorized work')
        self.assertFalse(w.task_path(self.root,'UI-1').exists());self.assertTrue(w.task_path(self.root,'NEXT').exists())
        self.assertTrue((self.root/'app.py').exists())

    def test_automatic_retention_never_forgets_unhanded_limitations(self):
        self.configure(self.policy());self.refresh();self.close();self.age()
        result=w.maintain(self.root)
        self.assertEqual(result['retained'],1);self.assertTrue(w.task_path(self.root,self.ident).exists())
        self.assertIn('Synthetic local environment only',w.detail(self.root,self.ident,'receipt')['text'])

    def test_automatic_retention_preserves_unknown_files(self):
        self.configure(self.policy());self.refresh();self.execute();self.support();w.close(self.root,self.ident,[]);self.age()
        folder=self.root/'.featrace/artifacts'/self.ident;(folder/'not-owned.txt').write_text('keep')
        self.assertEqual(w.maintain(self.root)['retained'],1);self.assertTrue((folder/'not-owned.txt').exists())

    def test_maintenance_rotates_past_active_tasks_and_obeys_recorded_retention(self):
        self.configure(self.policy());self.refresh();self.execute();self.support();w.close(self.root,self.ident,[]);self.age()
        for i in range(4):w.begin(self.root,f'A-{i}','active')
        # Existing completed policy is forget. Changing project policy to manual cannot rewrite its original retention receipt.
        self.configure(self.policy('manual'))
        for _ in range(6):w.maintain(self.root,limit=1)
        self.assertFalse(w.task_path(self.root,'UI-1').exists())
        self.assertTrue(w.task_path(self.root,'A-0').exists())

    def test_completed_summary_does_not_dump_large_limitation_body(self):
        self.execute();self.support();limitation='Large unresolved issue '+('汉'*20000);w.close(self.root,self.ident,[limitation])
        summary=w.view(self.root,self.ident)
        self.assertLess(len(json.dumps(summary).encode()),4096)
        first=w.detail(self.root,self.ident,'receipt',limit=8000)
        self.assertIsNotNone(first['next_offset']);self.assertLess(len(json.dumps(first,ensure_ascii=False).encode()),16384)

    def test_scoped_review_input_returns_current_fact_ids_not_other_task_history(self):
        self.execute();self.support();before=w.task_path(self.root,self.ident).read_bytes()
        proof=w.review_input(self.root,self.ident,'C1')
        self.assertEqual(proof['facts'],[self.doc()['executions']['target']['id']]);self.assertEqual(proof['criterion'],'C1')
        self.assertEqual(before,w.task_path(self.root,self.ident).read_bytes())

    def test_code_query_is_literal_current_source_only_with_explicit_paging(self):
        (self.root/'app.py').write_text('label="after"\n'*30)
        found=w.code_query(self.root,'label=',limit=5)
        self.assertEqual(len(found['items']),5);self.assertEqual(found['next_offset'],5);self.assertFalse(found['exhausted'])
        self.assertEqual(w.code_query(self.root,'not-present')['items'],[])

    def test_fast_output_is_refused_without_exceeding_hard_log_cap(self):
        self.plan['checks'][0]['argv']=[sys.executable,'-c','import os;os.write(1,b"X"*65536)'];self.refresh()
        with patch.object(w,'MAX_LOG',1024):
            self.assertEqual(self.execute()['status'],'unavailable')
        artifact=self.doc()['executions']['target']['artifact']
        self.assertLessEqual((self.root/artifact['path']).stat().st_size,1024)
        self.assertFalse(w.view(self.root,self.ident)['eligible'])

    def test_closed_stdout_does_not_evade_timeout(self):
        self.plan['checks'][0]['argv']=[sys.executable,'-c','import os,time;os.close(1);os.close(2);time.sleep(20)']
        self.plan['checks'][0]['timeout']=1;self.refresh()
        self.assertEqual(self.execute()['status'],'unavailable')

    def test_code_query_never_reads_retired_ledger(self):
        folder=self.root/'.agent-workflow';folder.mkdir();(folder/'old.txt').write_text('unique_old_secret_needle')
        self.git('add','.agent-workflow');self.git('commit','-qm','old record fixture')
        self.assertEqual(w.code_query(self.root,'unique_old_secret_needle')['items'],[])

    def test_manifest_membership_drift_is_not_silently_certified(self):
        import task_inputs
        original=task_inputs.git_paths;counter=[0]
        def changed(root):
            counter[0]+=1
            names=original(root)
            return names+['created-during-scan'] if counter[0]>1 else names
        with patch.object(task_inputs,'git_paths',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'MEMBERSHIP_MOVED'):
                task_inputs.signature(self.root,[],[{'kind':'git_tree','path':'.'}],[],[])

    def test_large_detail_cli_is_bounded_and_explicit_about_tail(self):
        self.execute();self.support();w.close(self.root,self.ident,['汉'*20000])
        result=subprocess.run([sys.executable,str(Path(w.__file__)),'detail',str(self.root),self.ident,'--section','receipt','--limit','8000'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout);self.assertLessEqual(len(result.stdout.encode()),w.MAX_OUTPUT+1)
        self.assertIsNotNone(json.loads(result.stdout)['next_offset'])

    def test_external_toolchain_tree_accepts_internal_aliases_but_not_escape(self):
        import tempfile,task_inputs
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'real').write_text('tool data');(root/'alias').symlink_to('real')
            args=(self.root,[],[],[{'kind':'tree','path':str(root)}],[])
            first=task_inputs.signature(*args);self.assertGreater(first['entries'],2)
            (root/'real').write_text('new tool data');self.assertNotEqual(first,task_inputs.signature(*args))
            (root/'escape').symlink_to('/tmp')
            with self.assertRaisesRegex(ValueError,'EXTERNAL_LINK_OUTSIDE'):task_inputs.signature(*args)

    def test_link_cycles_refuse_without_unbounded_recursion(self):
        import tempfile,task_inputs
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'loop').symlink_to('loop')
            with self.assertRaisesRegex(ValueError,'LINK_CYCLE'):
                task_inputs.signature(self.root,[],[],[{'kind':'tree','path':str(root)}],[])

    def test_foreign_policy_is_not_silently_overwritten(self):
        path=self.root/w.task_policy.NAME;path.write_text('{"foreign":"keep"}')
        with self.assertRaisesRegex(ValueError,'POLICY_FIELDS_INVALID'):self.configure(self.policy())
        self.assertEqual(path.read_text(),'{"foreign":"keep"}')

    def test_removing_local_ignore_protection_blocks_next_execution(self):
        (self.root/'.gitignore').write_text('run-count\nother-count\n__pycache__/\n')
        self.plan['constraints']['.gitignore']='Synthetic intentionally changed ignore, but local outputs still need protection';self.refresh()
        with self.assertRaisesRegex(ValueError,'IGNORE_CONFLICT'):self.execute()

    def test_status_hashes_shared_execution_inputs_once_not_per_criterion(self):
        self.plan['criteria']=[{'id':f'C{i}','expected':'Same synthetic target assertion','kind':'changed','inputs':['app.py']} for i in range(30)]
        self.plan['checks'][0]['covers']=[c['id'] for c in self.plan['criteria']];self.refresh();self.execute()
        for c in self.plan['criteria']:w.assess(self.root,self.ident,c['id'],'supported','Same synthetic target fact')
        with patch.object(w.task_inputs,'signature',wraps=w.task_inputs.signature) as capture:
            self.assertTrue(w.view(self.root,self.ident)['eligible'])
            self.assertEqual(capture.call_count,1)

    def test_maintenance_control_lock_does_not_collide_with_task_slots(self):
        import hashlib
        slot=int(hashlib.sha256(b'maintenance').hexdigest()[:8],16)%64
        ident=next(f'COLLIDE-{i}' for i in range(1000) if int(hashlib.sha256(f'COLLIDE-{i}'.encode()).hexdigest()[:8],16)%64==slot)
        self.configure(self.policy());w.begin(self.root,ident,'Synthetic known lock collision');self.ident=ident
        self.refresh();self.execute();self.support();w.close(self.root,ident,[]);self.age()
        w.maintain(self.root)
        self.assertFalse(w.task_path(self.root,ident).exists())

    def test_owned_attachment_copy_is_collected_but_original_is_preserved(self):
        original=self.root/'other-count';original.write_bytes(b'synthetic evidence bytes')
        ref=w.attach(self.root,self.ident,'other-count')
        self.assertEqual((self.root/ref['path']).read_bytes(),original.read_bytes())
        self.execute();self.support();w.close(self.root,self.ident,[]);self.age()
        preview=w.cleanup(self.root,self.ident)
        self.assertEqual(preview['owned_attachments'],1)
        w.cleanup(self.root,self.ident,True,forget=True)
        self.assertFalse((self.root/ref['path']).exists());self.assertTrue(original.exists())

    def test_changed_owned_attachment_is_retained_as_unknown(self):
        (self.root/'other-count').write_text('source');ref=w.attach(self.root,self.ident,'other-count')
        self.execute();self.support();w.close(self.root,self.ident,[]);self.age()
        (self.root/ref['path']).write_text('replaced by unrelated bytes')
        with self.assertRaisesRegex(ValueError,'CHANGED_ATTACHMENT'):w.cleanup(self.root,self.ident,True)
        self.assertTrue(w.task_path(self.root,self.ident).exists())

    def test_attachment_budget_refuses_without_deleting_original(self):
        original=self.root/'other-count';original.write_bytes(b'x'*100)
        with patch.object(w,'MAX_LOG',50):
            with self.assertRaisesRegex(ValueError,'SIZE_LIMIT'):w.attach(self.root,self.ident,'other-count')
        self.assertTrue(original.exists())

    def test_observation_survives_wording_revision_but_assessment_must_be_renewed(self):
        self.plan['checks']=[];self.refresh()
        self.observe('C1','runtime_observation',w.now(),'Synthetic fixture observation',['app.py'])
        self.support();original=self.doc()['observations']['C1'].copy()
        self.plan['criteria'][0]['expected']='The same after label, clarified';self.refresh()
        self.assertFalse(w.view(self.root,self.ident)['eligible'])
        self.assertEqual(w.review_input(self.root,self.ident,'C1')['facts'],[original['id']])
        self.support();self.assertTrue(w.view(self.root,self.ident)['eligible'])
        self.assertEqual(self.doc()['observations']['C1'],original)

    def test_authority_revision_invalidates_only_its_assessment_not_execution(self):
        (self.root/'prd.md').write_text('Label shall read after')
        self.plan['criteria'][0]['sources']=['prd.md']
        self.plan['criteria'].append({'id':'C2','expected':'Same label rendering from independent intent','kind':'changed','inputs':['app.py']})
        self.plan['checks'][0]['covers'].append('C2');self.refresh();self.execute();self.support()
        w.assess(self.root,self.ident,'C2','supported','Same fixture assertion')
        (self.root/'prd.md').write_text('Clarification: after is exact lowercase')
        self.refresh();status=w.view(self.root,self.ident)
        self.assertEqual({c['id']:c['status'] for c in status['items']},{'C1':'needs_review','C2':'supported'})
        self.assertTrue(self.execute()['reused']);self.assertEqual((self.root/'run-count').read_text(),'1')

    def test_old_static_fact_never_becomes_runtime_by_changing_claim_kind(self):
        self.plan['criteria'][0]['kind']='unaffected';self.plan['checks']=[];self.refresh()
        self.observe('C1','static_analysis',w.now(),'Synthetic no influence',['app.py']);self.support()
        self.plan['criteria'][0]['kind']='changed';self.refresh()
        self.assertEqual(w.review_input(self.root,self.ident,'C1')['facts'],[])
        with self.assertRaisesRegex(ValueError,'CURRENT_FACT'):self.support()

# Prevent inherited cases being counted again in this module; expose only extension cases.
for _name in list(dir(FullReplacementTests)):
    if _name.startswith('test_') and _name not in FullReplacementTests.__dict__:setattr(FullReplacementTests,_name,None)
del TaskWorkflowTests
