"""Synthetic contract10 behavioral probes; no business/device or real reviewer claims."""
import copy
import json
import unittest
from unittest.mock import patch
import test_task_workflow as fixture
w=fixture.w

class Contract10Tests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.TaskWorkflowTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.r=self.f.root;self.id=self.f.ident;self.p=self.f.plan

    def note(self,actual='Current causal analysis',cid='C1'):
        path='analysis-'+str(len(self.f.doc()['facts']))+'.txt'
        (self.r/path).write_text(actual)
        return self.f.observe(cid,'static_analysis',w.now(),actual,[path])['fact']

    def partial(self,reason='Missing inspected evidence',independent=False):
        refs=w.facts(self.r,self.f.doc(),self.p['criteria'][0])
        proof=self.proof('partial',refs) if independent else None
        return w.assess(self.r,self.id,'C1','partial',reason,independent,proof,refs)['finding']

    def proof(self,verdict,refs,extra=None,context='synthetic-reviewer'):
        d=self.f.doc();c=d['plan']['criteria'][0]
        p={'task':self.id,'criterion':'C1','criterion_digest':w.criterion_stamp(self.r,d,c),
           'facts':sorted(refs),'verdict':verdict,'fresh_context':True,'host':'synthetic',
           'context_id':context,'reviewer':'fixture','reason':'Synthetic provenance, not independent review',**(extra or {})}
        path='.featrace/review.json';(self.r/path).write_text(json.dumps(p));return path

    def dispose(self,key,refs,action='addressed',proof=None):
        return w.task_failures.review_dispose(w,self.r,self.id,key,action,'Inspected targeted basis',refs,proof)

    def setup_adopt(self):
        self.p['checks'][0]['acceptance']={'mode':'applicable_result','reason':'Original assertion plus inspected current difference is sufficient'}
        self.p['criteria'][0]['proof']={'any_of':[['command'],['applicable_command']],'reason':'Explicit historical-result acceptance'}
        self.f.refresh();self.f.git('add','app.py');self.f.git('commit','-qm','observed baseline')
        self.rev=self.f.git('rev-parse','HEAD').decode().strip()
        self.f.execute();self.original=copy.deepcopy(self.f.execution())
        (self.r/'app.py').write_text('label="after"\n# explanation\n');self.f.refresh()
        self.analysis=self.note()

    def adopt(self):
        return w.task_adoption.check_adopt(w,self.r,self.id,'target',self.original['id'],[self.analysis],'Inspected all changed inputs')['fact']

    def test_partial_blocks_then_addressed_retains_original(self):
        self.f.execute();key=self.partial();old=copy.deepcopy(self.f.doc()['review_findings'][key])
        with self.assertRaisesRegex(ValueError,'REVIEW_FINDING_UNRESOLVED'):self.f.support()
        fact=self.note();self.dispose(key,[fact]);self.f.support()
        self.assertTrue(w.view(self.r,self.id)['eligible']);w.close(self.r,self.id,[])
        self.assertEqual(self.f.doc()['review_findings'][key]['assessment'],old['assessment'])
        self.assertEqual(self.f.doc()['receipt']['review_findings'][key]['disposition'],'addressed')

    def test_duplicate_partial_and_disposition_are_idempotent(self):
        self.f.execute();key=self.partial();self.assertEqual(key,self.partial())
        fact=self.note();first=self.dispose(key,[fact]);self.assertEqual(first,self.dispose(key,[fact]))
        self.assertEqual(len(self.f.doc()['review_findings'][key]['dispositions']),1)

    def test_duplicate_independent_partial_reuses_managed_original(self):
        self.f.execute();key=self.partial(independent=True);self.assertEqual(key,self.partial(independent=True))
        self.assertEqual(len(self.f.doc()['attachments']),1)

    def test_new_finding_is_not_removed_by_old_disposition(self):
        self.f.execute();a=self.partial();self.dispose(a,[self.note()]);b=self.partial('Different uncovered branch')
        self.assertIn(b,w.task_failures.review_pending(w,self.r,self.f.doc()))
        with self.assertRaisesRegex(ValueError,'UNRESOLVED'):self.f.support()

    def test_independent_disposition_requires_matching_real_shape(self):
        self.f.execute();key=self.partial(independent=True);fact=self.note()
        with self.assertRaisesRegex(ValueError,'PROVENANCE'):self.dispose(key,[fact])
        wrong=self.proof('supported',[fact],{'finding':'wrong','disposition':'addressed'})
        with self.assertRaisesRegex(ValueError,'PROVENANCE'):self.dispose(key,[fact],proof=wrong)
        proof=self.proof('supported',[fact],{'finding':key,'disposition':'addressed'})
        self.dispose(key,[fact],proof=proof)
        self.assertFalse(w.task_failures.review_pending(w,self.r,self.f.doc()))

    def test_judgment_error_keeps_facts_and_context(self):
        self.f.execute();key=self.partial(independent=True);refs=[self.f.execution()['id']]
        proof=self.proof('supported',refs,{'finding':key,'disposition':'judgment_error'},'different')
        with self.assertRaisesRegex(ValueError,'CONTEXT_CHANGED'):self.dispose(key,refs,'judgment_error',proof)
        proof=self.proof('supported',refs,{'finding':key,'disposition':'judgment_error'})
        self.dispose(key,refs,'judgment_error',proof)
        self.assertFalse(w.task_failures.review_pending(w,self.r,self.f.doc()))

    def test_disposition_drift_reopens_and_prune_retains_basis(self):
        self.f.execute();key=self.partial();fact=self.note();self.dispose(key,[fact]);self.f.support()
        self.assertNotIn(fact,w.retention_candidates(self.r,self.f.doc())[0])
        asset=next(iter(self.f.doc()['facts'][fact]['evidence']))
        (self.r/asset).write_text('changed')
        self.assertIn(key,w.task_failures.review_pending(w,self.r,self.f.doc()))
        self.assertFalse(w.view(self.r,self.id)['eligible'])

    def test_cannot_remove_finding_claim(self):
        key=self.partial();self.p['criteria'][0]['id']='C2';self.p['checks'][0]['covers']=['C2']
        with self.assertRaisesRegex(ValueError,'REVIEW_FINDING_CLAIM_REMOVED'):self.f.refresh()
        self.assertIn(key,self.f.doc()['review_findings'])

    def test_defer_preserves_finding_handoff_and_reopen_blocks(self):
        self.f.execute();key=self.partial();reason='Later product delivery';authority='Synthetic explicit decision'
        text=reason+' '+authority+' '+self.p['criteria'][0]['expected']+' '+w.canonical(w.failure_handoff(self.f.doc(),'C1')).decode()
        (self.r/'handoff.md').write_text(text)
        w.defer_claim(self.r,self.id,'C1',reason,authority,w.now(),'handoff.md',exclude=True)
        self.assertTrue(w.view(self.r,self.id)['eligible'])
        w.defer_claim(self.r,self.id,'C1','Resume',authority,w.now(),reopen=True)
        self.assertIn(key,w.task_failures.review_pending(w,self.r,self.f.doc()))
        self.assertFalse(w.view(self.r,self.id)['eligible'])

    def test_retirement_counts_unresolved_findings(self):
        key=self.partial();context=w.retirement_context(self.r,self.f.doc())
        self.assertIn(key,context['review_findings'])
        with self.assertRaisesRegex(ValueError,'HANDOFF'):w.retire(self.r,self.id,'Stop','Synthetic',w.now())

    def test_finding_capacity_refuses_without_overwrite(self):
        self.partial()
        with patch.object(w.task_failures,'MAX_REVIEW_FINDINGS',1):
            with self.assertRaisesRegex(ValueError,'LIMIT'):self.partial('New missing evidence')
        self.assertEqual(len(self.f.doc()['review_findings']),1)

    def test_check_adoption_closes_without_new_execution(self):
        self.setup_adopt();app=self.adopt()
        self.assertEqual(app,self.adopt())
        self.assertFalse(w.view(self.r,self.id)['eligible'])
        w.assess(self.r,self.id,'C1','supported','Historical assertion applies',fact_ids=[app])
        self.assertTrue(w.view(self.r,self.id)['eligible'])
        receipt=w.close(self.r,self.id,[])
        self.assertEqual(receipt['check_results']['target']['mode'],'adopted')
        self.assertEqual(self.f.doc()['facts'][self.original['id']],self.original)
        self.assertEqual((self.r/'run-count').read_text(),'1')
        self.assertNotIn(self.original['id'],w.retention_candidates(self.r,self.f.doc())[0])

    def test_adoption_does_not_satisfy_current_command_proof(self):
        self.setup_adopt();self.p['criteria'][0]['proof']={'any_of':[['command']],'reason':'Must be current'};self.f.refresh()
        with self.assertRaisesRegex(ValueError,'ADOPTION_UNAVAILABLE'):self.adopt()

    def test_adoption_does_not_grant_run_permission_or_fake_reuse(self):
        self.setup_adopt();self.adopt()
        result=self.f.execute()
        self.assertFalse(result['reused']);self.assertEqual((self.r/'run-count').read_text(),'2')
        self.assertTrue(self.f.execute()['reused'])

    def test_current_mode_cannot_be_retroactively_weakened(self):
        self.f.execute();self.original=copy.deepcopy(self.f.execution())
        self.p['checks'][0]['acceptance']={'mode':'applicable_result','reason':'Later weakening'};self.f.refresh();self.analysis=self.note()
        with self.assertRaisesRegex(ValueError,'ADOPTION_UNAVAILABLE'):self.adopt()

    def test_changed_again_stales_application(self):
        self.setup_adopt();app=self.adopt();w.assess(self.r,self.id,'C1','supported','Fixture',fact_ids=[app])
        (self.r/'app.py').write_text('label="after"\n# another change');self.f.refresh()
        self.assertFalse(w.view(self.r,self.id)['eligible'])

    def test_input_membership_or_executable_bit_change_refuses(self):
        self.setup_adopt();(self.r/'app.py').chmod(0o755)
        self.f.refresh();self.analysis=self.note()
        with self.assertRaisesRegex(ValueError,'ADOPTION_UNAVAILABLE'):self.adopt()

    def test_changed_command_refuses(self):
        self.setup_adopt();self.p['checks'][0]['argv'].append('--extra');self.f.refresh()
        with self.assertRaisesRegex(ValueError,'ADOPTION_UNAVAILABLE'):self.adopt()

    def test_failed_new_attempt_blocks_old_result(self):
        self.setup_adopt();(self.r/'app.py').write_text('label="broken"');self.f.refresh();self.f.execute();self.analysis=self.note()
        with self.assertRaisesRegex(ValueError,'ADOPTION_UNAVAILABLE'):self.adopt()

    def test_pending_review_or_runtime_failure_blocks_adoption(self):
        self.setup_adopt();self.partial()
        with self.assertRaisesRegex(ValueError,'ADOPTION_UNAVAILABLE'):self.adopt()

    def test_current_live_requirement_cannot_opt_in(self):
        self.p['checks'][0]['acceptance']={'mode':'applicable_result','reason':'Invalid live reuse'}
        self.p['criteria'][0]['validity']={'mode':'current','target':'synthetic','max_age_seconds':60,'reason':'Live'}
        with self.assertRaisesRegex(ValueError,'CURRENT_REFUSED'):self.f.refresh()

    def test_corrupted_original_artifact_refuses(self):
        self.setup_adopt();(self.r/self.original['artifact']['path']).write_text('damaged')
        with self.assertRaisesRegex(ValueError,'ADOPTION_UNAVAILABLE'):self.adopt()

    def test_old_contract9_refuses_without_mutation(self):
        doc=self.f.doc();doc['task_contract']=9;w.save(self.r,doc);before=w.task_path(self.r,self.id).read_bytes()
        with self.assertRaisesRegex(ValueError,'PINNED_TOOL'):w.load(self.r,self.id)
        self.assertEqual(w.task_path(self.r,self.id).read_bytes(),before)

    def test_runtime_failure_and_unknown_refuse_check_adoption(self):
        self.setup_adopt()
        self.f.observe('C1','runtime_observation',w.now(),'Actual fixture failure',['app.py'],'failed')
        with self.assertRaisesRegex(ValueError,'ADOPTION_UNAVAILABLE'):self.adopt()
        self.p['unknowns']=[{'reason':'Unresolved caller','criteria':['C1'],'checks':[]}];self.f.refresh()
        with self.assertRaisesRegex(ValueError,'SCOPE_UNKNOWN'):self.adopt()

    def test_external_bytes_are_not_adoptable(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            from pathlib import Path
            external=Path(folder)/'sdk';external.write_text('one')
            self.p['checks'][0]['external_inputs']=[{'kind':'file','path':str(external)}]
            self.setup_adopt();external.write_text('two')
            with self.assertRaisesRegex(ValueError,'ADOPTION_UNAVAILABLE'):self.adopt()

    def test_dependency_membership_change_refuses(self):
        (self.r/'lib').mkdir();(self.r/'lib/a.py').write_text('x=1')
        self.p['checks'][0]['input_sets']=[{'kind':'tree','path':'lib'}]
        self.setup_adopt();(self.r/'lib/b.py').write_text('y=1')
        with self.assertRaisesRegex(ValueError,'ADOPTION_UNAVAILABLE'):self.adopt()

    def test_environment_change_refuses(self):
        self.setup_adopt()
        with patch.dict(w.os.environ,{'LANG':'synthetic-different'}):
            with self.assertRaisesRegex(ValueError,'ADOPTION_UNAVAILABLE'):self.adopt()

    def test_adoption_analysis_must_cover_entire_check(self):
        (self.r/'other.py').write_text('second=1')
        self.p['scope'].append('other.py')
        self.p['criteria'].append({'id':'C2','expected':'Second behavior','kind':'unaffected','inputs':['other.py'],
                                  'proof':{'any_of':[['command'],['applicable_command']],'reason':'Fixture'}})
        self.p['checks'][0]['inputs'].append('other.py');self.p['checks'][0]['covers'].append('C2')
        self.setup_adopt()
        with self.assertRaisesRegex(ValueError,'ADOPTION_UNAVAILABLE'):self.adopt()
        analysis2=self.note('Other caller unchanged','C2')
        app=w.task_adoption.check_adopt(w,self.r,self.id,'target',self.original['id'],[self.analysis,analysis2],'Both criteria inspected')['fact']
        w.assess(self.r,self.id,'C1','supported','Fixture',fact_ids=[app])
        self.assertFalse(w.view(self.r,self.id)['eligible'])
        w.assess(self.r,self.id,'C2','supported','Fixture',fact_ids=[app])
        self.assertTrue(w.view(self.r,self.id)['eligible'])

    def test_test_result_retains_original_producer_when_command_adopted(self):
        # Register original result BEFORE editing, then explicitly adopt both kinds.
        self.p['checks'][0]['acceptance']={'mode':'applicable_result','reason':'Scoped old result valid'}
        self.p['criteria'][0]['proof']={'any_of':[['command','runtime_observation'],['applicable_command','runtime_observation']],
                                      'reason':'Must retain actual test output too'}
        self.f.refresh();self.f.git('add','app.py');self.f.git('commit','-qm','Tested source')
        revision=self.f.git('rev-parse','HEAD').decode().strip();self.f.execute();self.original=copy.deepcopy(self.f.execution())
        (self.r/'result.xml').write_text('<testsuite tests="1" failures="0"/>')
        observed=self.f.observe('C1','runtime_observation',self.original['at'],'Synthetic output, not real JUnit',['result.xml'],producer=self.original['id'])['fact']
        (self.r/'app.py').write_text('label="after"\n# explanation');self.f.refresh();self.analysis=self.note()
        command_app=self.adopt()
        runtime_app=w.task_adoption.adopt(w,self.r,self.id,'C1',observed,revision,[self.analysis],'Original output still applies')['fact']
        w.assess(self.r,self.id,'C1','supported','Explicit historical results',fact_ids=[command_app,runtime_app,observed])
        self.assertTrue(w.view(self.r,self.id)['eligible'])
        self.assertEqual(self.f.doc()['facts'][observed]['producer'],self.original['id'])
        asset=next(iter(self.f.doc()['facts'][observed]['evidence']));(self.r/asset).write_text('damaged')
        self.assertFalse(w.view(self.r,self.id)['eligible'])

    def test_application_does_not_satisfy_command_only_proof_even_with_optin(self):
        self.p['checks'][0]['acceptance']={'mode':'applicable_result','reason':'Fixture policy'}
        self.p['criteria'][0]['proof']={'any_of':[['command']],'reason':'Explicit current command required'}
        self.f.refresh();self.f.execute();self.original=copy.deepcopy(self.f.execution())
        (self.r/'app.py').write_text('label="after"\n# comment');self.f.refresh();self.analysis=self.note();app=self.adopt()
        with self.assertRaisesRegex(ValueError,'PROOF_REQUIREMENTS_UNMET'):
            w.assess(self.r,self.id,'C1','supported','Cannot weaken proof',fact_ids=[app])

    def test_correct_preserves_finding_and_cleanup_respects_handoff(self):
        self.f.execute();key=self.partial();self.dispose(key,[self.note()]);self.f.support();w.close(self.r,self.id,[])
        old=copy.deepcopy(self.f.doc()['review_findings'][key])
        w.correct(self.r,self.id,['C1'],'Fixture original judgment refinement','Synthetic user')
        self.assertEqual(self.f.doc()['review_findings'][key],old)
        self.f.support();w.close(self.r,self.id,[])
        doc=self.f.doc();doc['receipt']['completed_at']='2000-01-01T00:00:00+00:00';w.save(self.r,doc)
        w.cleanup(self.r,self.id,apply=True)
        doc=self.f.doc();self.assertNotIn('facts',doc)
        self.assertEqual(doc['receipt']['review_findings'][key]['disposition'],'addressed')

    def test_failed_disposition_save_does_not_publish_resolution(self):
        self.f.execute();key=self.partial(independent=True);fact=self.note()
        proof=self.proof('supported',[fact],{'finding':key,'disposition':'addressed'})
        original=w.task_path(self.r,self.id).read_bytes()
        with patch.object(w,'save',side_effect=ValueError('Synthetic publication failure')):
            with self.assertRaisesRegex(ValueError,'publication'):self.dispose(key,[fact],proof=proof)
        self.assertEqual(w.task_path(self.r,self.id).read_bytes(),original)
        self.assertIn(key,w.task_failures.review_pending(w,self.r,self.f.doc()))

    def test_review_correction_does_not_hide_runtime_failure(self):
        fact=self.note();key=self.partial()
        self.f.observe('C1','runtime_observation',w.now(),'Actual failed branch',['app.py'],'failed')
        self.dispose(key,[fact],action='judgment_error')
        self.assertTrue(w.task_failures.pending(self.f.doc()))
        self.assertFalse(w.view(self.r,self.id)['eligible'])

    def test_repeated_partial_after_disposition_is_a_new_blocker(self):
        self.f.execute();refs=[self.f.execution()['id']]
        first=w.assess(self.r,self.id,'C1','partial','Recurring concern',fact_ids=refs)['finding']
        self.dispose(first,[self.note()]);self.f.support()
        second=w.assess(self.r,self.id,'C1','partial','Recurring concern',fact_ids=refs)['finding']
        self.assertNotEqual(first,second)
        self.assertIn(second,w.task_failures.review_pending(w,self.r,self.f.doc()))
        with self.assertRaisesRegex(ValueError,'REVIEW_FINDING_UNRESOLVED'):self.f.support()
        self.assertEqual(second,w.assess(self.r,self.id,'C1','partial','Recurring concern',fact_ids=refs)['finding'])
