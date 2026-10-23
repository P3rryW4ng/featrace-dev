from datetime import datetime, timezone, timedelta
import json
from unittest.mock import patch
from test_task_workflow import TaskWorkflowTests, w


class ObservationValidityTests(TaskWorkflowTests):
    def current(self, age=60):
        self.plan['criteria'][0]['validity']={'mode':'current','target':'synthetic-current-environment',
                                             'max_age_seconds':age,'reason':'Synthetic setting can change independently'}
        self.plan['checks']=[];self.refresh()

    def capture(self):
        return self.observe('C1','runtime_observation',w.now(),'Synthetic current setting',['app.py'],
                            target='synthetic-current-environment')

    def later(self, seconds):
        clock=patch.object(w,'datetime');mock=clock.start();self.addCleanup(clock.stop)
        mock.now.side_effect=lambda *args:datetime.now(timezone.utc)+timedelta(seconds=seconds)
        mock.fromisoformat.side_effect=datetime.fromisoformat

    def test_as_of_observation_does_not_expire_by_time_alone(self):
        self.plan['criteria'][0]['validity']={'mode':'as_of'}
        self.plan['checks']=[];self.refresh()
        self.observe('C1','runtime_observation',w.now(),'Captured layout',['app.py']);self.support()
        before=self.doc()['observations']['C1']
        self.later(30*86400)
        self.assertTrue(w.view(self.root,self.ident)['eligible'])
        self.assertEqual(self.doc()['observations']['C1'],before)

    def test_expired_current_observation_blocks_without_rewriting_fact(self):
        self.current();self.capture();self.support()
        before=w.task_path(self.root,self.ident).read_bytes()
        self.later(61)
        status=w.view(self.root,self.ident)
        self.assertFalse(status['eligible'])
        self.assertEqual(status['items'][0]['observation_applicability'],'EXPIRED')
        self.assertEqual(w.task_path(self.root,self.ident).read_bytes(),before)
        with self.assertRaisesRegex(ValueError,'DELIVERY_BLOCKED'):w.close(self.root,self.ident,[])

    def test_registration_or_reassessment_cannot_refresh_old_observation_time(self):
        self.current();self.capture();self.support();original=self.doc()['observations']['C1']['observed_at']
        self.later(61)
        with self.assertRaisesRegex(ValueError,'CURRENT_FACT_REQUIRED'):self.support()
        self.assertEqual(self.doc()['observations']['C1']['observed_at'],original)

    def test_target_change_invalidates_fact_inside_time_window(self):
        self.current(600);self.capture();self.support()
        self.plan['criteria'][0]['validity']['target']='different-synthetic-deployment';self.refresh()
        self.assertEqual(w.facts(self.root,self.doc(),self.plan['criteria'][0]),[])

    def test_wrong_target_cannot_be_recorded_as_current_pass(self):
        self.current()
        with self.assertRaisesRegex(ValueError,'CURRENT_TARGET_MISMATCH'):
            self.observe('C1','runtime_observation',w.now(),'Wrong environment',['app.py'],target='other')

    def test_static_analysis_does_not_prove_live_environment(self):
        self.current();self.plan['criteria'][0]['kind']='unaffected';self.refresh()
        with self.assertRaisesRegex(ValueError,'CURRENT_STATE_NEEDS_RUNTIME'):
            self.observe('C1','static_analysis',w.now(),'Code alone',['app.py'])

    def test_expired_failure_still_blocks_and_new_current_runtime_pass_resolves(self):
        self.current()
        self.observe('C1','runtime_observation',w.now(),'Synthetic failure',['app.py'],'failed',target='synthetic-current-environment')
        original=self.doc()['runtime_failures']['C1']['id']
        self.later(61)
        self.assertIn('RUNTIME_FAILURE:C1',w.view(self.root,self.ident)['blockers'])
        self.capture();self.support()
        self.assertTrue(w.view(self.root,self.ident)['eligible'])
        self.assertEqual(self.doc()['observations']['C1']['resolved_failure']['id'],original)

    def test_current_expiry_does_not_invalidate_independent_check(self):
        self.current()
        self.plan['criteria'].append({'id':'C2','expected':'Independent local label','kind':'changed','inputs':['app.py']})
        self.plan['checks']=[{'id':'target','argv':[__import__('sys').executable,'check.py'],
                             'inputs':['app.py','check.py'],'covers':['C2'],'reason':'Local deterministic label',
                             'timeout':5,'environment':{'kind':'local','target':'local label'}}]
        self.refresh();self.execute();w.assess(self.root,self.ident,'C2','supported','Actual local assertion')
        self.capture();self.support();self.later(61)
        status=w.view(self.root,self.ident)
        self.assertEqual({x['id']:x['status'] for x in status['items']},{'C1':'needs_review','C2':'supported'})
        self.assertTrue(self.execute()['reused'])

    def test_current_check_uses_original_start_and_matching_target(self):
        self.current()
        check={'id':'target','argv':[__import__('sys').executable,'check.py'],'inputs':['app.py','check.py'],
               'covers':['C1'],'reason':'Synthetic environment assertion','timeout':5,
               'environment':{'kind':'local','target':'synthetic-current-environment'}}
        self.plan['checks']=[check];self.refresh();self.execute();self.support()
        doc=self.doc();doc['executions']['target']['started_at']=(datetime.now(timezone.utc)-timedelta(seconds=61)).isoformat()
        w.save(self.root,doc)
        self.assertEqual(w.facts(self.root,self.doc(),self.plan['criteria'][0]),[])

    def test_invalid_current_contracts_are_rejected(self):
        for validity in ({'mode':'unknown'}, {'mode':'current'},
                         {'mode':'current','target':'fixture','reason':'Fixture','max_age_seconds':True},
                         {'mode':'current','target':'fixture','reason':'Fixture','max_age_seconds':0}):
            self.plan['criteria'][0]['validity']=validity
            with self.assertRaises(ValueError):self.refresh()

    def test_expired_current_check_executes_again_instead_of_returning_cached_pass(self):
        self.plan['criteria'][0]['validity']={'mode':'current','target':'synthetic local Python',
                                             'max_age_seconds':60,'reason':'Synthetic current property'}
        self.refresh();self.execute();self.later(61)
        result=self.execute()
        self.assertFalse(result['reused'])
        self.assertEqual((self.root/'run-count').read_text(),'2')
        self.support();self.assertTrue(w.view(self.root,self.ident)['eligible'])

    def test_expired_pass_cannot_remove_pending_runtime_failure(self):
        self.current()
        at=w.now()
        self.observe('C1','runtime_observation',at,'Failure',['app.py'],'failed',target='synthetic-current-environment')
        self.later(120)
        old_pass=(datetime.fromisoformat(at)+timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(ValueError,'CURRENT_OBSERVATION_NOT_APPLICABLE'):
            self.observe('C1','runtime_observation',old_pass,'Old targeted pass',['app.py'],target='synthetic-current-environment')
        self.assertIn('C1',self.doc()['runtime_failures'])


for name in list(dir(ObservationValidityTests)):
    if name.startswith('test_') and name not in ObservationValidityTests.__dict__:setattr(ObservationValidityTests,name,None)
del TaskWorkflowTests
