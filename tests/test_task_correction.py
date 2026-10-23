import copy
from datetime import datetime, timezone, timedelta
import json
from test_task_workflow import TaskWorkflowTests, w


class TaskCorrectionTests(TaskWorkflowTests):
    def completed_two_claims(self):
        (self.root/'other.py').write_text('unchanged=1')
        self.plan['scope'].append('other.py')
        self.plan['criteria'].append({'id':'C2','expected':'Other unchanged','kind':'unaffected','inputs':['other.py']})
        self.refresh();self.execute();self.support()
        self.observe('C2','static_analysis',w.now(),'No influence',['other.py'])
        self.assess('C2','supported','Causal proof')
        w.close(self.root,self.ident,['Original limit'])
        return copy.deepcopy(self.doc())

    def correct(self, criteria=None):
        return w.correct(self.root,self.ident,criteria or ['C1'],'Wrong evidence attribution','Synthetic user decision')

    def test_correction_keeps_receipt_and_only_requires_selected_reassessment(self):
        original=self.completed_two_claims();self.correct()
        doc=self.doc();entry=doc['corrections'][-1]
        self.assertEqual(doc['state'],'correcting')
        self.assertEqual(entry['prior_receipt'],original['receipt'])
        self.assertEqual(entry['prior_claims']['C1']['assessment'],original['assessments']['C1'])
        self.assertEqual(entry['prior_claims']['C1']['criterion'],original['plan']['criteria'][0])
        self.assertEqual(doc['observations'],original['observations'])
        self.assertEqual(doc['executions'],original['executions'])
        self.assertNotIn('C1',doc['assessments'])
        self.assertEqual(doc['assessments']['C2'],original['assessments']['C2'])
        self.assertEqual({x['id']:x['status'] for x in w.view(self.root,self.ident)['items']},
                         {'C1':'needs_review','C2':'supported'})
        with self.assertRaisesRegex(ValueError,'DELIVERY_BLOCKED'):w.close(self.root,self.ident,[])
        self.assertTrue(self.execute()['reused']);self.support()
        receipt=w.close(self.root,self.ident,['Original limit'])
        self.assertEqual(receipt['corrects_receipt'],w.digest(original['receipt']))
        self.assertEqual(self.doc()['corrections'][-1]['status'],'complete')
        self.assertEqual((self.root/'run-count').read_text(),'1')

    def test_correction_refuses_unclosed_unknown_selection_and_missing_authority(self):
        with self.assertRaisesRegex(ValueError,'CORRECTION_REQUIRES_COMPLETE'):self.correct()
        self.completed_two_claims()
        for criteria,reason,authority in [([], 'reason','decision'),(['missing'],'reason','decision'),(['C1'],'','decision'),(['C1'],'reason','')]:
            with self.assertRaises(ValueError):w.correct(self.root,self.ident,criteria,reason,authority)

    def test_open_correction_cannot_drop_affected_claim(self):
        self.completed_two_claims();self.correct()
        self.plan['criteria']=self.plan['criteria'][1:];self.plan['checks']=[]
        with self.assertRaisesRegex(ValueError,'CORRECTION_CLAIM_REMOVED'):self.refresh()

    def test_refreshed_plan_keeps_correction_state_and_real_failures_block(self):
        self.completed_two_claims();self.correct();self.refresh()
        self.assertEqual(self.doc()['state'],'correcting')
        self.observe('C1','runtime_observation',w.now(),'Actual failure',['app.py'],'failed')
        self.support();self.assertFalse(w.view(self.root,self.ident)['eligible'])
        self.observe('C1','runtime_observation',w.now(),'New targeted pass',['app.py'])
        self.support();self.assertTrue(w.view(self.root,self.ident)['eligible'])

    def test_compacted_task_cannot_be_reopened_without_original_inputs(self):
        self.completed_two_claims();self.age();w.cleanup(self.root,self.ident,True)
        before=w.task_path(self.root,self.ident).read_bytes()
        with self.assertRaisesRegex(ValueError,'CORRECTION_SOURCE_EXPIRED'):self.correct()
        self.assertEqual(before,w.task_path(self.root,self.ident).read_bytes())

    def test_cleanup_refuses_open_correction_and_preserves_closed_correction_receipt(self):
        original=self.completed_two_claims();self.correct()
        with self.assertRaisesRegex(ValueError,'CLEANUP_REQUIRES_COMPLETE'):w.cleanup(self.root,self.ident,True)
        self.support();w.close(self.root,self.ident,['Original limit'])
        self.age();w.cleanup(self.root,self.ident,True)
        doc=self.doc()
        self.assertEqual(doc['task_contract'],3)
        self.assertEqual(doc['corrections'][0]['prior_receipt'],original['receipt'])
        self.assertNotIn('prior_claims',doc['corrections'][0])


    def test_correction_history_has_bound_and_does_not_silently_discard(self):
        self.completed_two_claims()
        for _ in range(w.MAX_CORRECTIONS):
            self.correct();self.support();w.close(self.root,self.ident,['Original limit'])
        before=w.task_path(self.root,self.ident).read_bytes()
        with self.assertRaisesRegex(ValueError,'CORRECTION_LIMIT'):self.correct()
        self.assertEqual(before,w.task_path(self.root,self.ident).read_bytes())




    def test_correction_record_overflow_refuses_atomically(self):
        self.completed_two_claims()
        doc=self.doc();doc['plan']['criteria'][1]['expected']='x'*(w.MAX_RECORD//2)
        w.save(self.root,doc);before=w.task_path(self.root,self.ident).read_bytes()
        with self.assertRaisesRegex(ValueError,'TASK_SIZE_LIMIT'):self.correct(['C2'])
        self.assertEqual(before,w.task_path(self.root,self.ident).read_bytes())




for name in list(dir(TaskCorrectionTests)):
    if name.startswith('test_') and name not in TaskCorrectionTests.__dict__:setattr(TaskCorrectionTests,name,None)
del TaskWorkflowTests
