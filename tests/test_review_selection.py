"""Scoped review policy and actual execution identity remain separate."""
from pathlib import Path
import unittest
from unittest.mock import patch
import test_task_workflow as fixture
w = fixture.w


class ReviewSelectionTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.TaskWorkflowTests(methodName='runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def test_acceptance_validator_change_preserves_original_execution(self):
        f=self.f
        first=f.execute();original=f.execution().copy()
        source=Path(w.__file__).read_text()
        changed=source.replace("fail('REVIEW_SCOPE_REQUIRED')", "fail('REVIEW_POLICY_SCOPE_REQUIRED')")
        self.assertNotEqual(changed,source)
        path=f.root/'acceptance-policy-change.py';path.write_text(changed)
        with patch.object(w,'__file__',str(path)):
            self.assertTrue(f.execute()['reused'])
            self.assertNotEqual(w.task_execution.producer(w.__file__),original['producer'])
        self.assertEqual(f.execution(),original)
        self.assertEqual(f.execution()['id'],first['execution'])
        self.assertEqual((f.root/'run-count').read_text(),'1')

    def test_execution_validator_change_still_invalidates_execution(self):
        f=self.f;f.execute()
        source=Path(w.__file__).read_text()
        changed=source.replace("not 1<=c['timeout']<=3600", "not 1<=c['timeout']<=1800")
        self.assertNotEqual(changed,source)
        path=f.root/'execution-validation-change.py';path.write_text(changed)
        with patch.object(w,'__file__',str(path)):
            self.assertFalse(f.execute()['reused'])
        self.assertEqual((f.root/'run-count').read_text(),'2')

    def test_project_required_selected_review_cannot_be_self_certified(self):
        f=self.f
        (f.root/'rules.md').write_text('Independent review is mandatory for the changed shared claim.')
        f.plan['categories']=['shared']
        f.plan['review']={'independent':True,'criteria':['C1'],'reason':'Current explicit project requirement'}
        f.refresh();f.execute();f.support()
        self.assertFalse(w.view(f.root,f.ident)['eligible'])
        proof=w.review_input(f.root,f.ident,'C1')
        proof.update(verdict='supported',fresh_context=True,host='synthetic fixture',
                     context_id='synthetic-fixture-only',reviewer='synthetic fixture',reason='Program structure, not a real Agent review')
        import json
        p=f.root/'.featrace/review.json';p.write_text(json.dumps(proof))
        f.assess('C1','supported','Program fixture only',True,'.featrace/review.json')
        self.assertTrue(w.view(f.root,f.ident)['eligible'])

    def test_single_caller_selected_high_risk_review_still_blocks(self):
        f=self.f
        f.plan['categories']=['state']
        f.plan['review']={'independent':True,'criteria':['C1'],'reason':'Declared high-risk claim despite one caller; synthetic selection only'}
        f.refresh();f.execute();f.support()
        self.assertIn('CLAIM:C1',w.view(f.root,f.ident)['blockers'])
        with self.assertRaisesRegex(ValueError,'DELIVERY_BLOCKED'):w.close(f.root,f.ident,[])

    def test_runtime_failure_survives_shared_self_review_selection(self):
        f=self.f;f.execute()
        failed=f.observe('C1','runtime_observation',w.now(),'Actual synthetic runtime failure',['app.py'],'failed')['fact']
        f.plan['categories']=['shared','presentation']
        f.plan['review']={'independent':False,'criteria':[],'reason':'No separate review needed does not resolve failure'}
        f.refresh()
        f.observe('C1','static_analysis',w.now(),'Code inspection is not a repair observation',['app.py'])
        with self.assertRaisesRegex(ValueError,'TARGETED_RUNTIME_PROOF_REQUIRED'):f.resolve()
        f.support()
        self.assertEqual(f.runtime_failure('C1')['id'],failed)
        self.assertIn('RUNTIME_FAILURE:'+failed,w.view(f.root,f.ident)['blockers'])
        with self.assertRaisesRegex(ValueError,'DELIVERY_BLOCKED'):w.close(f.root,f.ident,[])

    def test_execution_path_keeps_environment_and_cache_validation(self):
        f=self.f
        for replacement, error in [
            ({'environment':{'kind':'unrecognized','target':'fixture'}},'ENVIRONMENT_KIND_REQUIRED'),
            ({'environment':{'kind':'remote','target':'fixture','policy_environment':'test'}},'MUTABLE_ENVIRONMENT_CACHE_REFUSED'),
            ({'timeout':0},'CHECK_INVALID'),
        ]:
            with self.subTest(error=error):
                d=f.doc();d['plan']['checks'][0].update(replacement);w.save(f.root,d)
                with self.assertRaisesRegex(ValueError,error):f.execute()
                self.assertFalse((f.root/'run-count').exists())
                # Restore from the valid fixture plan, not from the malformed saved object.
                f.refresh()

    def test_invalid_proof_or_review_cannot_be_planned_or_closed(self):
        f=self.f
        for field,value,error in [('review',{'independent':False,'reason':'','criteria':[]},'REVIEW_SCOPE_REQUIRED'),
                                  ('proof',{'any_of':[],'reason':'No actual proof'},'PROOF_REQUIREMENTS_INVALID')]:
            with self.subTest(field=field):
                import copy
                p=copy.deepcopy(f.plan)
                if field=='proof':p['criteria'][0]['proof']=value
                else:p['review']=value
                with self.assertRaisesRegex(ValueError,error):w.set_plan(f.root,f.ident,p)
                d=f.doc();d['plan']=p;w.save(f.root,d)
                with self.assertRaisesRegex(ValueError,'DELIVERY_BLOCKED|'+error):w.close(f.root,f.ident,[])
                f.refresh()


if __name__=='__main__':unittest.main()
