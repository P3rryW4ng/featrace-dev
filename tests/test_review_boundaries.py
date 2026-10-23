import json
from unittest.mock import patch, MagicMock
from test_task_workflow import TaskWorkflowTests, w


class ReviewBoundaryTests(TaskWorkflowTests):
    def two_claims(self):
        (self.root/'other.py').write_text('independent=1')
        (self.root/'other-rules.md').write_text('Other display requirement')
        self.plan['scope'].append('other.py')
        self.plan['criteria'].append({'id':'C2','expected':'Other display','kind':'unaffected','inputs':['other.py']})

    def proof(self, criterion):
        p=w.review_input(self.root,self.ident,criterion)
        p.update(verdict='supported',fresh_context=True,host='synthetic',context_id='synthetic',reviewer='synthetic',reason='Synthetic provenance only')
        name='.featrace/proof-'+criterion+'.json'
        (self.root/name).write_text(json.dumps(p))
        self.assess(criterion,'supported','Fixture only',True,name)

    def test_selected_independent_review_does_not_expand_to_other_claim(self):
        self.two_claims()
        self.plan['categories']=['presentation','shared']
        self.plan['review']={'independent':True,'reason':'Only C1 has shared effects','criteria':['C1']}
        self.refresh();self.execute();self.proof('C1')
        self.observe('C2','static_analysis',w.now(),'Independent caller unaffected',['other.py'])
        self.assess('C2','supported','No shared influence')
        self.assertTrue(w.view(self.root,self.ident)['eligible'])

    def test_review_scope_cannot_name_missing_claim_or_empty_shared_scope(self):
        for selected in ([],['missing']):
            self.plan['categories']=['shared']
            self.plan['review']={'independent':True,'reason':'Shared fixture','criteria':selected}
            with self.assertRaises(ValueError):self.refresh()

    def test_selected_claim_still_requires_independent_proof(self):
        self.two_claims()
        self.plan['review']={'independent':True,'reason':'Only C1','criteria':['C1']}
        self.refresh();self.execute();self.support()
        self.observe('C2','static_analysis',w.now(),'No influence',['other.py'])
        self.assess('C2','supported','No influence')
        self.assertFalse(w.view(self.root,self.ident)['eligible'])

    def test_adding_review_requirement_invalidates_old_self_assessment(self):
        self.execute();self.support()
        self.plan['review']={'independent':True,'reason':'Newly discovered shared caller','criteria':['C1']}
        self.refresh()
        self.assertFalse(w.view(self.root,self.ident)['eligible'])
        self.assertTrue(self.execute()['reused'])

    def test_local_rule_change_preserves_unrelated_execution_and_assessment(self):
        self.two_claims()
        self.plan['constraints']={'other-rules.md':{'decision':'Only C2 display','criteria':['C2'],'checks':[]}}
        self.refresh();self.execute();self.support()
        old=self.doc()['assessments']['C1']['criterion_digest']
        (self.root/'other-rules.md').write_text('Updated C2 display only')
        self.assertTrue(self.execute()['reused'])
        self.assertEqual(old,w.criterion_stamp(self.root,self.doc(),self.plan['criteria'][0]))
        with self.assertRaisesRegex(ValueError,'SCOPE_REVIEW'):
            w.observe(self.root,self.ident,'C2','static_analysis',w.now(),'Not yet reviewed',['other.py'])

    def test_execution_rule_change_requires_reconciliation_and_rerun(self):
        self.plan['constraints']={'rules.md':{'decision':'Execution settings','criteria':[],'checks':['target']}}
        self.refresh();self.execute()
        (self.root/'rules.md').write_text('Changed applicable execution rule')
        with self.assertRaisesRegex(ValueError,'SCOPE_REVIEW'):self.execute()
        self.refresh();self.assertFalse(self.execute()['reused'])

    def test_constraint_unknown_selection_cannot_be_silently_ignored(self):
        self.plan['constraints']={'rules.md':{'decision':'Fixture','criteria':['missing'],'checks':[]}}
        with self.assertRaises(ValueError):self.refresh()

    def test_empty_constraint_selection_is_rejected(self):
        self.plan['constraints']={'rules.md':{'decision':'Cannot silently omit authority','criteria':[],'checks':[]}}
        with self.assertRaisesRegex(ValueError,'CONSTRAINT_SCOPE'):self.refresh()

    def test_pending_failure_details_survive_latest_unavailable_observation(self):
        self.observe('C1','runtime_observation',w.now(),'Actual synthetic failure',['app.py'],'failed')
        original=self.runtime_failure('C1')
        self.observe('C1','runtime_observation',w.now(),'Latest evidence unavailable',['app.py'],'unavailable')
        detail=w.detail(self.root,self.ident,'facts','C1',limit=8000)
        body=detail['text'];offset=detail['next_offset']
        while offset is not None:
            page=w.detail(self.root,self.ident,'facts','C1',offset,8000)
            body+=page['text'];offset=page['next_offset']
        self.assertEqual(json.loads(body)['runtime_failure'],original)
        self.assertEqual(w.review_input(self.root,self.ident,'C1')['runtime_failure']['id'],original['id'])

    def test_interrupted_attempt_replaces_previous_success_as_unavailable(self):
        self.plan['checks'][0]['cache']={'mode':'never','max_age_seconds':300}
        self.refresh();previous=self.execute()
        real=w.subprocess.Popen;child=MagicMock();child.pid=999999;child.poll.side_effect=KeyboardInterrupt
        argv=self.plan['checks'][0]['argv']
        def spawn(command,**kwargs):return child if command==argv else real(command,**kwargs)
        with patch.object(w.subprocess,'Popen',side_effect=spawn),patch.object(w.os,'killpg'):
            with self.assertRaises(KeyboardInterrupt):self.execute()
        record=self.execution()
        self.assertEqual(record['status'],'unavailable')
        self.assertEqual(record['reason'],'EXECUTION_INTERRUPTED')
        self.assertEqual(record['previous_result'],previous['execution'])
        self.assertFalse(w.view(self.root,self.ident)['eligible'])

    def test_post_execution_identity_failure_is_recorded(self):
        original=w.check_stamp;calls=[]
        def stamp(*args):
            calls.append(True)
            if len(calls)==2:raise ValueError('Synthetic tool disappeared')
            return original(*args)
        with patch.object(w,'check_stamp',side_effect=stamp):
            result=self.execute()
        self.assertEqual(result['status'],'unavailable')
        self.assertEqual(self.execution()['reason'],'EXECUTION_IDENTITY_UNAVAILABLE')


for name in list(dir(ReviewBoundaryTests)):
    if name.startswith('test_') and name not in ReviewBoundaryTests.__dict__:setattr(ReviewBoundaryTests,name,None)
del TaskWorkflowTests
