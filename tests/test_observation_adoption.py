import copy
import unittest
from pathlib import Path
import test_task_workflow as fixture
w=fixture.w

class AdoptionTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.TaskWorkflowTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.r=self.f.root;self.p=self.f.plan
        self.p['checks']=[];self.p['criteria'][0]['proof']={'any_of':[['runtime_observation']],'reason':'Observed rendering'}
        self.f.refresh();self.f.git('add','app.py');self.f.git('commit','-qm','observed source')
        self.rev=self.f.git('rev-parse','HEAD').decode().strip()
        (self.r/'evidence.txt').write_text('original image surrogate')
        self.old=self.f.observe('C1','runtime_observation',w.now(),'Original rendering',['evidence.txt'])['fact']
        self.original=copy.deepcopy(self.f.doc()['facts'][self.old])
        (self.r/'app.py').write_text('label="after"\nother_branch=1\n');self.f.refresh()
        (self.r/'analysis.txt').write_text('Inspected other branch and relevant callers')
        self.analysis=self.f.observe('C1','static_analysis',w.now(),'Actual synthetic causal proof',['analysis.txt'])['fact']

    def adopt(self):
        return w.task_adoption.adopt(w,self.r,self.f.ident,'C1',self.old,self.rev,[self.analysis],'Other branch only')['fact']

    def test_explicit_adoption_keeps_original_and_allows_current_support(self):
        with self.assertRaisesRegex(ValueError,'CURRENT_FACT_REQUIRED'):
            w.assess(self.r,self.f.ident,'C1','supported','Old alone',fact_ids=[self.old])
        app=self.adopt()
        with self.assertRaisesRegex(ValueError,'ORIGINAL_SELECTION'):
            w.assess(self.r,self.f.ident,'C1','supported','No original selected',fact_ids=[app])
        w.assess(self.r,self.f.ident,'C1','supported','Original plus current adoption',fact_ids=[self.old,app])
        self.assertTrue(w.view(self.r,self.f.ident)['eligible'])
        self.assertEqual(self.original,self.f.doc()['facts'][self.old])

    def test_changed_again_stales_only_adoption(self):
        app=self.adopt();(self.r/'app.py').write_text('label="new"');self.f.refresh()
        with self.assertRaisesRegex(ValueError,'CURRENT_FACT_REQUIRED'):
            w.assess(self.r,self.f.ident,'C1','supported','Stale adoption',fact_ids=[self.old,app])

    def test_real_failure_cannot_be_adopted_away(self):
        self.f.observe('C1','runtime_observation',w.now(),'Actual failure',['evidence.txt'],status='failed')
        with self.assertRaisesRegex(ValueError,'FAILURE_OR_DEFERRAL'):self.adopt()

    def test_unknown_blocks_adoption(self):
        self.p['unknowns']=[{'reason':'Unknown caller','criteria':['C1'],'checks':[]}];self.f.refresh()
        with self.assertRaisesRegex(ValueError,'SCOPE_UNKNOWN'):self.adopt()

    def test_evidence_damage_refuses(self):
        managed=next(iter(self.f.doc()['facts'][self.old]['evidence']))
        (self.r/managed).write_text('changed')
        with self.assertRaisesRegex(ValueError,'ORIGINAL_UNAVAILABLE'):self.adopt()

    def test_wrong_baseline_refuses(self):
        with self.assertRaisesRegex(ValueError,'BASELINE_MISMATCH'):
            w.task_adoption.adopt(w,self.r,self.f.ident,'C1',self.old,self.f.doc()['baseline'],[self.analysis],'wrong source')

    def test_changed_promise_refuses(self):
        self.p['criteria'][0]['expected']='different promise';self.f.refresh()
        with self.assertRaisesRegex(ValueError,'ORIGINAL_UNAVAILABLE'):self.adopt()

    def test_analysis_damage_refuses(self):
        managed=next(iter(self.f.doc()['facts'][self.analysis]['evidence']))
        (self.r/managed).write_text('modified')
        with self.assertRaisesRegex(ValueError,'ANALYSIS_UNAVAILABLE'):self.adopt()

    def test_prune_retains_adopted_sources(self):
        app=self.adopt();w.assess(self.r,self.f.ident,'C1','supported','Selected adoption',fact_ids=[self.old,app])
        w.prune(self.r,self.f.ident,True)
        self.assertTrue({self.old,app,self.analysis}<=set(self.f.doc()['facts']))

    def test_adoption_cannot_chain(self):
        app=self.adopt()
        with self.assertRaisesRegex(ValueError,'ORIGINAL_UNAVAILABLE'):
            w.task_adoption.adopt(w,self.r,self.f.ident,'C1',app,self.rev,[self.analysis],'not original')

    def test_missing_producer_and_current_target_cannot_be_adopted(self):
        d=self.f.doc();d['facts'][self.old]['producer']='missing';w.save(self.r,d)
        with self.assertRaisesRegex(ValueError,'ORIGINAL_UNAVAILABLE'):self.adopt()

    def test_uninspected_changed_behavior_is_not_automatically_supported(self):
        (self.r/'app.py').write_text('label="wrong"');self.f.refresh()
        with self.assertRaisesRegex(ValueError,'ANALYSIS_UNAVAILABLE'):self.adopt()

    def test_fixed_commit_required_not_mutable_branch(self):
        with self.assertRaisesRegex(ValueError,'FIXED_REVISION'):
            w.task_adoption.adopt(w,self.r,self.f.ident,'C1',self.old,'HEAD',[self.analysis],'branch')

    def test_old_contract6_is_refused_without_writes(self):
        d=self.f.doc();d['task_contract']=6;w.save(self.r,d)
        path=w.task_path(self.r,self.f.ident);before=path.read_bytes()
        with self.assertRaisesRegex(ValueError,'PINNED_TOOL'):w.load(self.r,self.f.ident)
        self.assertEqual(path.read_bytes(),before)

    def test_inconsistent_original_source_snapshot_is_not_adoptable(self):
        d=self.f.doc();old=d['facts'][self.old];old['source_inputs']=w.files(self.r,['app.py'])
        self.assertFalse(w.task_adoption.historical(w,self.r,d,d['plan']['criteria'][0],old))
