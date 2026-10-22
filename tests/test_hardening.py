import copy
import json
from datetime import datetime, timedelta, timezone
from test_task_workflow import TaskWorkflowTests,w

class HardeningTests(TaskWorkflowTests):
    def test_runtime_failure_survives_unavailable_static_and_plan_removal(self):
        self.plan['criteria'][0]['kind']='unaffected';self.plan['checks']=[];self.refresh()
        self.observe('C1','runtime_observation',w.now(),'Actual runtime failure',['app.py'],'failed')
        self.observe('C1','static_analysis',w.now(),'Evidence unavailable',['app.py'],'unavailable')
        with self.assertRaisesRegex(ValueError,'RUNTIME_FAILURE_NEEDS_RUNTIME'):
            self.observe('C1','static_analysis',w.now(),'No influence',['app.py'],'passed')
        other=copy.deepcopy(self.plan);other['criteria'][0]['id']='C2'
        with self.assertRaisesRegex(ValueError,'UNRESOLVED_OBSERVATION_REMOVED'):w.set_plan(self.root,self.ident,other)
        self.observe('C1','runtime_observation',w.now(),'Targeted runtime pass',['app.py'])
        self.support();self.assertTrue(w.view(self.root,self.ident)['eligible'])
        self.assertEqual(self.doc()['observations']['C1']['resolved_failure']['actual'],'Actual runtime failure')

    def test_execution_input_rule_not_only_semantic_scope(self):
        cfg=w.task_policy.load(self.root)
        cfg['rules']=[{'source':'rules.md','sha256':'prepared','paths':['check.py'],'operations':['test'],'environment':'any','decision':'No execution','permission':'denied','authority':'Synthetic grant boundary'}]
        w.task_policy.prepare(self.root,cfg,w.git);self.plan['scope']=['app.py'];self.refresh()
        with self.assertRaisesRegex(ValueError,'POLICY_DENIED'):self.execute()
        self.assertFalse((self.root/'run-count').exists())

    def test_unknown_and_missing_environment_refuse(self):
        for value in ('device_typo',None):
            if value is None:self.plan['checks'][0]['environment'].pop('kind',None)
            else:self.plan['checks'][0]['environment']['kind']=value
            with self.assertRaisesRegex(ValueError,'ENVIRONMENT_KIND'):self.refresh()

    def two_claims(self):
        (self.root/'other.py').write_text('independent=1')
        self.plan['scope'].append('other.py')
        self.plan['criteria'].append({'id':'C2','expected':'Other behavior','kind':'unaffected','inputs':['other.py']})
        self.plan['checks'].append({'id':'second','argv':[__import__('sys').executable,'-c','print("second")'],'inputs':['other.py'],'covers':['C2'],'reason':'Independent assertion fixture','timeout':5,'environment':{'kind':'local','target':'synthetic'}})

    def test_scoped_unknown_allows_independent_check_but_blocks_closure(self):
        self.two_claims();self.plan['unknowns']=[{'reason':'Investigating other behavior','criteria':['C2'],'checks':[]}];self.refresh()
        self.assertEqual(self.execute()['status'],'passed');self.support()
        with self.assertRaisesRegex(ValueError,'SCOPE_UNKNOWN'):w.run_check(self.root,self.ident,'second')
        self.assertFalse(w.view(self.root,self.ident)['eligible'])
        with self.assertRaisesRegex(ValueError,'DELIVERY_BLOCKED'):w.close(self.root,self.ident,[])

    def test_other_owned_file_drift_does_not_block_independent_check(self):
        self.two_claims();self.refresh();self.execute();self.support()
        (self.root/'other.py').write_text('independent=2')
        self.assertTrue(self.execute()['reused'])
        with self.assertRaisesRegex(ValueError,'SCOPE_REVIEW_REQUIRED'):w.run_check(self.root,self.ident,'second')
        self.assertFalse(w.view(self.root,self.ident)['eligible'])

    def test_unrelated_branch_commit_does_not_expand_claims(self):
        self.execute();self.support()
        (self.root/'merge.py').write_text('separate_module=1');self.git('add','merge.py');self.git('commit','-qm','unrelated merge fixture')
        self.assertTrue(self.execute()['reused']);self.assertTrue(w.view(self.root,self.ident)['eligible'])
        self.assertEqual(len(self.doc()['plan']['criteria']),1)

    def test_broad_check_still_invalidates_on_unrelated_compiler_input(self):
        self.plan['checks'][0]['input_sets']=[{'kind':'git_tree','path':'.'}];self.refresh();self.execute()
        (self.root/'added.py').write_text('compiler_input=1')
        self.assertFalse(self.execute()['reused']);self.assertEqual(len(self.doc()['plan']['criteria']),1)

    def test_input_set_permissions_are_enforced(self):
        (self.root/'restricted').mkdir();(self.root/'restricted/source.py').write_text('actual_input=1')
        cfg=w.task_policy.load(self.root);cfg['rules']=[{'source':'rules.md','sha256':'prepared','paths':['restricted/**'],'operations':['test'],'environment':'any','decision':'Do not use restricted files in checks','permission':'denied','authority':'Synthetic scope'}]
        w.task_policy.prepare(self.root,cfg,w.git);self.plan['checks'][0]['input_sets']=[{'kind':'git_tree','path':'.'}];self.refresh()
        with self.assertRaisesRegex(ValueError,'POLICY_DENIED'):self.execute()

    def test_unrelated_claim_rule_does_not_block_independent_action(self):
        self.two_claims();cfg=w.task_policy.load(self.root);cfg['rules']=[{'source':'rules.md','sha256':'prepared','paths':['other.py'],'operations':['test'],'environment':'any','decision':'Other action denied','permission':'denied','authority':'Synthetic scope'}]
        w.task_policy.prepare(self.root,cfg,w.git);self.refresh();self.assertEqual(self.execute()['status'],'passed')
        with self.assertRaisesRegex(ValueError,'POLICY_DENIED'):w.run_check(self.root,self.ident,'second')

    def test_storage_reports_stale_active_tasks_without_modifying_or_cleaning(self):
        d=self.doc();d['created_at']=(datetime.now(timezone.utc)-timedelta(days=30)).isoformat();w.save(self.root,d)
        # Simulate a genuinely inactive task, without mutating sources or clearing its state.
        d=w.load(self.root,self.ident);d['updated_at']=d['created_at'];d['checksum']=w.digest({k:v for k,v in d.items() if k!='checksum'})
        w.task_path(self.root,self.ident).write_text(json.dumps(d))
        extra=self.root/'.featrace/unknown.bin';extra.write_bytes(b'unknown')
        before={str(p):p.read_bytes() for p in (self.root/'.featrace').rglob('*') if p.is_file()}
        summary=w.storage(self.root)
        self.assertEqual(summary['counts']['stale_incomplete'],1);self.assertGreater(summary['usage']['regular_bytes'],7)
        self.assertIn('STALE_INCOMPLETE_TASKS_RETAINED',summary['warnings'])
        self.assertEqual(before,{str(p):p.read_bytes() for p in (self.root/'.featrace').rglob('*') if p.is_file()})

    def test_storage_paginates_and_does_not_follow_unknown_links(self):
        for i in range(3):w.begin(self.root,'OTHER'+str(i),'Synthetic work')
        external=self.root.parent/'outside-storage-fixture';external.mkdir(exist_ok=True)
        (external/'secret').write_text('do not inspect')
        (self.root/'.featrace/outside').symlink_to(external,target_is_directory=True)
        try:
            summary=w.storage(self.root,0,2);self.assertEqual(len(summary['items']),2);self.assertEqual(summary['next_offset'],2)
            self.assertEqual(summary['usage']['links'],1);self.assertEqual(summary['task_count'],4)
        finally:(external/'secret').unlink();external.rmdir()

    def test_investigation_can_resolve_unknown_without_double_execution(self):
        self.plan['unknowns']=[{'reason':'Need actual targeted result','criteria':['C1'],'checks':[]}];self.refresh()
        result=w.run_check(self.root,self.ident,'target',investigate=True)
        self.assertEqual(result['status'],'passed');self.assertFalse(w.view(self.root,self.ident)['eligible'])
        with self.assertRaisesRegex(ValueError,'SCOPE_UNKNOWN'):self.support()
        self.plan['unknowns']=[];self.refresh();self.assertTrue(self.execute()['reused']);self.support()
        self.assertTrue(w.view(self.root,self.ident)['eligible']);self.assertEqual((self.root/'run-count').read_text(),'1')

    def test_investigation_does_not_bypass_actual_permissions(self):
        cfg=w.task_policy.load(self.root);cfg['rules']=[{'source':'rules.md','sha256':'prepared','paths':['check.py'],'operations':['test'],'environment':'any','decision':'No run','permission':'denied','authority':'Synthetic scope'}]
        w.task_policy.prepare(self.root,cfg,w.git);self.plan['unknowns']=['Unknown needs investigation'];self.refresh()
        with self.assertRaisesRegex(ValueError,'POLICY_DENIED'):w.run_check(self.root,self.ident,'target',investigate=True)
        self.assertFalse((self.root/'run-count').exists())

    def test_production_results_cannot_use_content_cache(self):
        self.plan['checks'][0]['environment']['kind']='production'
        with self.assertRaisesRegex(ValueError,'MUTABLE_ENVIRONMENT_CACHE_REFUSED'):self.refresh()

    def test_pass_older_than_pending_failure_does_not_resolve_it(self):
        self.plan['criteria'][0]['kind']='unaffected';self.plan['checks']=[];self.refresh()
        earlier=w.now();self.observe('C1','runtime_observation',w.now(),'Observed failure',['app.py'],'failed')
        with self.assertRaisesRegex(ValueError,'PASS_PREDATES_FAILURE'):self.observe('C1','runtime_observation',earlier,'Older result',['app.py'])
        self.assertFalse(w.view(self.root,self.ident)['eligible'])

    def test_nonexistent_rule_path_does_not_block_actual_input_set(self):
        cfg=w.task_policy.load(self.root);cfg['rules']=[{'source':'rules.md','sha256':'prepared','paths':['absent/**'],'operations':['test'],'environment':'any','decision':'Absent area denied','permission':'denied','authority':'Synthetic scope'}]
        w.task_policy.prepare(self.root,cfg,w.git);self.plan['checks'][0]['input_sets']=[{'kind':'git_tree','path':'.'}];self.refresh()
        self.assertEqual(self.execute()['status'],'passed')

    def test_explicit_directory_execution_input_also_checks_member_rules(self):
        (self.root/'restricted').mkdir();(self.root/'restricted/source.py').write_text('actual=1')
        cfg=w.task_policy.load(self.root);cfg['rules']=[{'source':'rules.md','sha256':'prepared','paths':['restricted/source.py'],'operations':['test'],'environment':'any','decision':'Restricted member denied','permission':'denied','authority':'Synthetic scope'}]
        w.task_policy.prepare(self.root,cfg,w.git);self.plan['checks'][0]['inputs'].append('restricted');self.refresh()
        with self.assertRaisesRegex(ValueError,'POLICY_DENIED'):self.execute()

for name in list(dir(HardeningTests)):
    if name.startswith('test_') and name not in HardeningTests.__dict__:setattr(HardeningTests,name,None)
del TaskWorkflowTests
