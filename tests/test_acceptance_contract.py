"""Behavioral acceptance-contract tests on synthetic Git projects only."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import test_check_runs
import verification as v
import check_runs as runs
import acceptance_contract as a


class AcceptanceContractTests(unittest.TestCase):
    def setUp(self):
        h=test_check_runs.CheckRunTests();h.setUp();self.addCleanup(h.doCleanups)
        self.h=h;self.root=h.root;self.folder=h.folder
        self.h.execute()
        for row in v.load_plan(self.folder)['items']:
            if row['mode']=='manual':
                stamp,head=v.context(self.root,self.folder,v.load_plan(self.folder))
                v.record(self.root,self.folder,row['id'],'passed',stamp,head,'Synthetic complete observation','Synthetic non-device fixture')
        h.helper.git('add','-A');self.commit('original observations')
        self.origin=copy.deepcopy(v.load_plan(self.folder))
        self.approval={'active_features':['FEAT-001'],'hosts':[{'name':'unittest synthetic host','schema6_capable':True}],'evidence':'Synthetic explicit opt-in'}
        a.prepare(self.root,self.folder,self.approval)

    def commit(self,message):
        self.h.helper.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm',message)

    def plan(self):return a.load(self.folder)

    def capture(self):return a.capture_assessment(self.root,self.folder)[0]

    def review(self,request,verdict='supported'):
        proof={'request_digest':request['request_digest'],'fresh_context':True,'host':'synthetic test host','context_id':'separate synthetic context','reviewer':'synthetic reviewer'}
        path=self.root/'.agent-workflow/scratch/acceptance-reviews'/self.folder.name/'host.json'
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(proof))
        assess=[]
        for claim in request['active_versions']:
            refs=[k for k,x in request['fact_refs'].items() if x['source']==claim['locator'] and x['fact']['status']=='passed']
            if claim['execution_mapping']['mode']=='automatic':refs=[k for k,x in request['fact_refs'].items() if x['ref']['container']=='check_attempt']
            assess.append(dict(claim_key=claim['claim_key'],verdict=verdict,source_basis='Synthetic source inspected',required_scope='Entire synthetic AC',observed_scope='Original complete synthetic observation',evidence_ref='Original Git record',counterexample_check='Failure/unknown must not be replaced by earlier green',fact_refs=refs))
        return dict(request_digest=request['request_digest'],reviewer='synthetic reviewer',reviewer_evidence_ref={'path':path.relative_to(self.root).as_posix(),'sha256':a.byte_hash(path.read_bytes())},
                    change_findings=[{'id':x['id'],'classification':'affected','targets':[c['claim_key'] for c in request['active_versions']],'evidence':'Synthetic full change inspected'} for x in request['deltas']],
                    assess=assess,reuse=[],pending=[],barrier_resolutions=[])

    def accept(self):
        request=self.capture();review=self.review(request);a.apply_assessment(self.root,self.folder,request,review);return request,review

    def change(self,file,fn):
        path=self.folder/file;doc=json.loads(path.read_text());fn(doc);path.write_text(json.dumps(doc))

    def test_initial_capture_pending_without_check_pass_cycle(self):
        self.assertFalse(a.resolve_claims(self.root,self.folder)['acceptance_eligible'])
        self.assertTrue(self.capture()['fact_refs'])
        self.assertEqual(self.plan()['items'][0]['history'],[])
        self.assertEqual(a.latest_result(self.root,self.folder,self.plan()['items'][0])['tested_revision'],self.origin['items'][0]['history'][-1]['tested_revision'])

    def test_supported_and_no_input_change_readonly(self):
        self.accept();before=(self.folder/'verification.json').read_bytes();counter=self.h.counter.read_text()
        for _ in range(2):self.assertTrue(a.resolve_claims(self.root,self.folder)['acceptance_eligible'])
        self.assertEqual((self.folder/'verification.json').read_bytes(),before);self.assertEqual(self.h.counter.read_text(),counter)
        self.assertEqual(v.validate_verification(self.root,self.folder,{},'check'),[])
        self.assertEqual(v.state(self.plan()['items'][0],'unused',v.row_evidence_stamp(self.root,self.folder,self.plan()['items'][0])),'passed')

    def test_progress_not_free_note(self):
        self.accept();self.change('spec/requirements.json',lambda d:d['feature'].update(status='provisional'))
        self.assertTrue(a.resolve_claims(self.root,self.folder)['acceptance_eligible'])
        self.change('spec/requirements.json',lambda d:d['feature'].update(status_note='not progress metadata'))
        self.assertFalse(a.resolve_claims(self.root,self.folder)['acceptance_eligible'])
        self.assertTrue(any('status_note' in x['path'] for x in self.capture()['deltas']))

    def test_local_decision_reuses_all_without_resigning_observations(self):
        self.accept();before=self.plan();counter=self.h.counter.read_text()
        self.change('decisions.json',lambda d:d['decisions'].append({'id':'D-LOCAL','status':'approved','evidence':'Synthetic unrelated aspect'}))
        request=self.capture();review=self.review(request)
        for x in review['change_findings']: x['classification']='unaffected_with_evidence'
        review['reuse']=[dict(claim_key=c['claim_key'],from_key=c['claim_key'],evidence='All complete deltas inspected; synthetic converter unaffected',semantic_equivalence='Exact criterion and dependencies unchanged') for c in request['active_versions']];review['assess']=[]
        review['reuse']=[{'targets':[{'claim_key':x['claim_key'],'from_key':x['from_key']} for x in review['reuse']],'evidence':'One complete shared delta investigation','semantic_equivalence':'Unchanged local requirements and inputs'}]
        a.apply_assessment(self.root,self.folder,request,review)
        self.assertTrue(a.resolve_claims(self.root,self.folder)['acceptance_eligible'])
        self.assertEqual([r['history'] for r in self.plan()['items']],[r['history'] for r in before['items']]);self.assertEqual(self.h.counter.read_text(),counter)
        self.assertEqual(len(self.plan()['acceptance']['events']),3)

    def test_all_negative_saved_and_same_input_cannot_turn_green(self):
        request=self.capture();review=self.review(request,'partial');a.apply_assessment(self.root,self.folder,request,review)
        self.assertFalse(a.resolve_claims(self.root,self.folder)['acceptance_eligible'])
        request=self.capture();review=self.review(request)
        with self.assertRaisesRegex(ValueError,'NEGATIVE_UNRESOLVED'):a.apply_assessment(self.root,self.folder,request,review)
        self.assertEqual(len(self.plan()['acceptance']['events']),2)

    def test_missing_delta_and_claim_reject_no_write(self):
        request=self.capture();review=self.review(request);before=self.plan()
        review['change_findings'].pop()
        with self.assertRaisesRegex(ValueError,'REVIEW_INCOMPLETE'):a.apply_assessment(self.root,self.folder,request,review)
        self.assertEqual(self.plan(),before)
        review=self.review(request);review['assess'].pop()
        with self.assertRaisesRegex(ValueError,'REVIEW_INCOMPLETE'):a.apply_assessment(self.root,self.folder,request,review)
        self.assertEqual(self.plan(),before)

    def test_unknown_change_not_ignored(self):
        request=self.capture();review=self.review(request);review['change_findings'][0]['classification']='unknown'
        with self.assertRaisesRegex(ValueError,'WORLD_UNKNOWN'):a.apply_assessment(self.root,self.folder,request,review)

    def test_real_host_provenance_required(self):
        request=self.capture();review=self.review(request);review['reviewer_evidence_ref']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'REVIEW_NOT_INDEPENDENT'):a.apply_assessment(self.root,self.folder,request,review)

    def test_input_drift_and_generation_no_partial_writes(self):
        request=self.capture();review=self.review(request);before=self.plan()
        self.change('decisions.json',lambda d:d['decisions'].append({'id':'D-NEW','evidence':'Moved'}))
        with self.assertRaisesRegex(ValueError,'INPUTS_MOVED'):a.apply_assessment(self.root,self.folder,request,review)
        self.assertEqual(self.plan(),before)

    def test_idempotent_apply_no_duplicate(self):
        request,review=self.accept();before=self.plan();a.apply_assessment(self.root,self.folder,request,review)
        self.assertEqual(self.plan(),before)

    def test_new_direct_fact_not_support_until_review(self):
        self.accept();doc=self.plan();request=self.capture();row=doc['items'][0]
        a.record_fact(self.root,self.folder,row['id'],'passed',request['world_digest'],self.h.helper.git('rev-parse','HEAD').strip(),'New actual observation','Synthetic evidence')
        self.assertEqual(self.plan()['items'][0]['history'][0]['actual'],'New actual observation')
        self.assertFalse(a.resolve_claims(self.root,self.folder)['acceptance_eligible'])
        self.accept();self.assertTrue(a.resolve_claims(self.root,self.folder)['acceptance_eligible'])

    def test_latest_failure_cannot_use_original_green(self):
        self.accept();request=self.capture();row=self.plan()['items'][0]
        a.record_fact(self.root,self.folder,row['id'],'failed',request['world_digest'],self.h.helper.git('rev-parse','HEAD').strip(),'Actual latest failure','Synthetic evidence')
        request=self.capture();review=self.review(request)
        with self.assertRaisesRegex(ValueError,'NEGATIVE_UNRESOLVED'):a.apply_assessment(self.root,self.folder,request,review)
        self.assertEqual(a.resolve_claims(self.root,self.folder)['items'][0]['status'],'failed')

    def test_business_change_requires_execution_again(self):
        self.accept();(self.root/'convert.py').write_text('changed source')
        view=a.resolve_claims(self.root,self.folder);self.assertFalse(view['acceptance_eligible'])
        self.assertIn('EXECUTION_UNAVAILABLE',[x['code'] for x in view['blockers']])

    def test_latest_attempt_failure_never_falls_back(self):
        self.accept();cfg=json.loads((self.h.helper.base/'quality-gates.json').read_text());cfg['gates'][0]['command']=[sys.executable,'-c','raise SystemExit(4)'];(self.h.helper.base/'quality-gates.json').write_text(json.dumps(cfg))
        self.assertEqual(runs.run(self.root,self.folder.name),2)
        self.assertFalse(a.resolve_claims(self.root,self.folder)['acceptance_eligible'])

    def test_workspace_busy(self):
        with runs.execution_lock(self.root):
            with self.assertRaisesRegex(ValueError,'WORKSPACE_BUSY'):a.reconcile_claims(self.root,self.folder)

    def test_removed_or_corrupt_original_refuses(self):
        doc=self.plan();doc['acceptance']['origins'][0]['blob_oid']='0'*40;(self.folder/'verification.json').write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError,'ORIGIN_UNAVAILABLE'):self.capture()

    def test_duplicate_json_and_event_hash_refuse(self):
        with self.assertRaisesRegex(ValueError,'CONTRACT_UNSUPPORTED'):a.parse('{"x":1,"x":2}')
        doc=self.plan();doc['acceptance']['events'][0]['actor']='edited'
        with self.assertRaisesRegex(ValueError,'CONTRACT_UNSUPPORTED'):a.validate_document(doc)

    def test_old_writers_disabled_and_no_mutation(self):
        import manual_scope,evidence_carry,result_corrections,evidence_adoption
        before=self.plan()
        for fn,args in [(manual_scope.prepare,()),(evidence_carry.minimize_copies,([],)),(result_corrections.capture,([],)),(evidence_adoption.capture,([],))]:
            with self.assertRaises(ValueError):fn(self.root,self.folder,*args)
            self.assertEqual(self.plan(),before)
        with self.assertRaisesRegex(ValueError,'LEGACY_WRITER_DISABLED'):v.adopt_checks(self.root,self.folder)

    def test_projection_failure_rebuild_does_not_execute(self):
        self.accept();before=self.plan();counter=self.h.counter.read_text()
        with patch('check_runs.save',side_effect=OSError('disk full')):
            with self.assertRaisesRegex(ValueError,'PROJECTION_STALE'):a.project_views(self.root,self.folder)
        self.assertEqual(self.plan(),before)
        a.project_views(self.root,self.folder);self.assertEqual(self.h.counter.read_text(),counter)
        self.assertEqual(json.loads((self.folder/'claim-review.json').read_text())['schema_version'],2)

    def test_claim_review_capture_before_supported(self):
        import claim_review
        self.assertEqual(claim_review.identity(self.root,self.folder),self.capture())
        self.assertTrue(claim_review.validate(self.root,self.folder))
        self.accept();self.assertEqual(claim_review.validate(self.root,self.folder),[])

    def test_reconcile_parent_and_explicit_criterion_alignment(self):
        self.accept();before=a.active_claims(self.plan());self.change('spec/requirements.json',lambda d:d['requirements'][0]['assumptions'].append('Local clarified premise'))
        with self.assertRaisesRegex(ValueError,'PLAN_RECONCILIATION_REQUIRED'):self.capture()
        a.reconcile_claims(self.root,self.folder);self.assertEqual(a.active_claims(self.plan())[0]['claim_key'],before[0]['claim_key'])
        self.assertNotEqual(a.active_claims(self.plan())[0]['version_digest'],before[0]['version_digest'])

    def test_legacy_format_still_usable_before_explicit_prepare(self):
        # Restore exact original bytes just in this isolated fixture, not a public downgrade API.
        path=self.folder/'verification.json';path.write_text(json.dumps(self.origin));self.assertEqual(v.load_plan(self.folder)['schema_version'],4)
        a.refuse_legacy(self.origin)

    def test_dirty_original_and_completed_prepare_refuse(self):
        path=self.folder/'verification.json';path.write_text(json.dumps(self.origin))
        with self.assertRaisesRegex(ValueError,'PREPARE_REQUIRED'):a.prepare(self.root,self.folder,self.approval)
        self.change('spec/requirements.json',lambda d:d['feature'].update(status='complete'))
        with self.assertRaisesRegex(ValueError,'PREPARE_REQUIRED'):a.prepare(self.root,self.folder,self.approval)

    def test_participant_inventory_required(self):
        (self.folder/'verification.json').write_text(json.dumps(self.origin))
        with self.assertRaisesRegex(ValueError,'PREPARE_REQUIRED'):a.prepare(self.root,self.folder,{'active_features':[]})

    def test_atomic_write_failure_preserves_plan(self):
        request=self.capture();review=self.review(request);before=(self.folder/'verification.json').read_bytes()
        with patch('check_runs.save',side_effect=OSError('atomic write failed')):
            with self.assertRaises(OSError):a.apply_assessment(self.root,self.folder,request,review)
        self.assertEqual((self.folder/'verification.json').read_bytes(),before)

    def test_restoration_only_before_new_fact_or_judgment(self):
        restored=a.restore_unstarted(self.root,self.folder,'Synthetic pre-use rollback')
        self.assertEqual(restored,self.origin)
        a.prepare(self.root,self.folder,self.approval)
        self.accept()
        with self.assertRaisesRegex(ValueError,'DOWNGRADE_UNSAFE'):a.restore_unstarted(self.root,self.folder,'Would lose judgment')

    def test_restoration_with_input_change_refuses(self):
        self.change('decisions.json',lambda d:d['decisions'].append({'id':'D-CHANGED'}))
        with self.assertRaisesRegex(ValueError,'DOWNGRADE_UNSAFE'):a.restore_unstarted(self.root,self.folder,'Changed input')

    def test_unsupported_composite_source_refuses_before_switch(self):
        doc=copy.deepcopy(self.origin);doc['items'][0]['history'][-1]['scope_ref']={'unsupported':'composite'}
        (self.folder/'verification.json').write_text(json.dumps(doc))
        self.h.helper.git('add','-A');self.commit('unsupported original')
        before=(self.folder/'verification.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'SOURCE_UNSUPPORTED'):a.prepare(self.root,self.folder,self.approval)
        self.assertEqual((self.folder/'verification.json').read_bytes(),before)

    def test_fresh_initialization_needs_no_fake_old_fact(self):
        (self.folder/'verification.json').unlink()
        a.prepare(self.root,self.folder,self.approval)
        self.assertEqual(self.plan()['acceptance']['origins'],[])
        self.assertTrue(all(not r['history'] for r in self.plan()['items']))
        self.assertFalse(a.resolve_claims(self.root,self.folder)['acceptance_eligible'])

    def test_failed_missing_terminal_has_no_old_green(self):
        self.accept();directory,_=runs.locate(self.root,self.folder.name);(directory/'result.json').unlink()
        self.assertFalse(a.resolve_claims(self.root,self.folder)['acceptance_eligible'])
        with self.assertRaisesRegex(ValueError,'WORKSPACE_BUSY'):a.apply_assessment(self.root,self.folder,self.capture(),self.review(self.capture()))

    def test_reuse_from_other_key_is_rejected(self):
        self.accept();request=self.capture();review=self.review(request);first,second=request['active_versions'][:2]
        review['assess']=[x for x in review['assess'] if x['claim_key']!=first['claim_key']]
        review['reuse']=[dict(claim_key=first['claim_key'],from_key=second['claim_key'],evidence='Wrong original',semantic_equivalence='Unsupported declaration')]
        with self.assertRaisesRegex(ValueError,'REVIEW_INCOMPLETE'):a.apply_assessment(self.root,self.folder,request,review)

    def test_partial_unknown_resolved_with_targeted_new_fact(self):
        request=self.capture();review=self.review(request,'unknown');a.apply_assessment(self.root,self.folder,request,review)
        negative=a.latest_event(self.plan(),'assessment')
        for row in self.plan()['items']:
            if row['mode']=='manual':
                frozen=self.capture()['world_digest']
                a.record_fact(self.root,self.folder,row['id'],'passed',frozen,self.h.helper.git('rev-parse','HEAD').strip(),'New observation covers previous unknown','Synthetic direct new proof')
        request=self.capture();review=self.review(request)
        review['barrier_resolutions']=[{'barrier_id':negative['id']+':'+c['claim_key'],'evidence':'New targeted observation','addresses':'Entire originally unknown scope is now executed'} for c in request['active_versions']]
        a.apply_assessment(self.root,self.folder,request,review)
        self.assertTrue(a.resolve_claims(self.root,self.folder)['acceptance_eligible'])
        # A later unrelated change must not require re-resolving the same gap.
        self.change('decisions.json',lambda d:d['decisions'].append({'id':'D-LATER'}))
        self.accept();self.assertTrue(a.resolve_claims(self.root,self.folder)['acceptance_eligible'])

    def test_unknown_root_row_and_request_fields_refuse(self):
        doc=self.plan();doc['items'][0]['unrecognized_scope']='must not ignore'
        with self.assertRaisesRegex(ValueError,'CONTRACT_UNSUPPORTED'):a.validate_document(doc)
        request=self.capture();review=self.review(request);review['extra']='ignored?'
        with self.assertRaisesRegex(ValueError,'REVIEW_INCOMPLETE'):a.apply_assessment(self.root,self.folder,request,review)

    def test_removal_needs_explicit_authority_disposition(self):
        self.change('spec/requirements.json',lambda d:d['requirements'][0].update(status='deprecated'))
        before=(self.folder/'verification.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'PLAN_RECONCILIATION_REQUIRED'):a.reconcile_claims(self.root,self.folder)
        self.assertEqual((self.folder/'verification.json').read_bytes(),before)

    def test_older_frozen_snapshot_rejects_after_new_assessment(self):
        old=self.capture();self.accept()
        with self.assertRaisesRegex(ValueError,'INPUTS_MOVED'):a.apply_assessment(self.root,self.folder,old,self.review(old,'unknown'))

    def test_event_history_and_saved_judgment_tamper_refuse(self):
        self.accept();doc=self.plan();event=doc['acceptance']['events'][-1]
        event['payload']['request']['from_event']='0'*64
        event['id']=a.stamp({k:v for k,v in event.items() if k!='id'})
        with self.assertRaisesRegex(ValueError,'CONTRACT_UNSUPPORTED'):a.validate_document(doc)

    def test_canonical_reader_entrypoints_agree(self):
        import subprocess
        self.accept();a.project_views(self.root,self.folder)
        scripts=Path(v.__file__).parent
        for name,args,code in [('verification.py',['status',str(self.root),self.folder.name],0),('claim_review.py',['check',str(self.root),self.folder.name],0),('verify-inputs.py',[str(self.root),self.folder.name],0),('feature-status.py',[str(self.root),self.folder.name],0),('render-workspace.py',[str(self.root),self.folder.name],0),('validate-feature.py',['--stage','check',str(self.root),self.folder.name],0),('audit-delivery.py',[str(self.root),self.folder.name],0)]:
            result=subprocess.run([sys.executable,str(scripts/name),*args],capture_output=True,text=True)
            self.assertEqual(result.returncode,code,(name,result.stdout,result.stderr))
            self.assertNotIn('invalid verification',result.stdout)
        self.assertEqual(self.h.counter.read_text(),'1')

    def test_device_failure_adapter_sees_original_and_new_negative(self):
        row=self.plan()['items'][0];doc=self.plan();doc['items'][0]['test_ids']=['DEVICE-1'];(self.folder/'verification.json').write_text(json.dumps(doc))
        a.reconcile_claims(self.root,self.folder)
        frozen=self.capture()['world_digest'];a.record_fact(self.root,self.folder,row['id'],'failed',frozen,self.h.helper.git('rev-parse','HEAD').strip(),'Current failure','Synthetic')
        self.assertTrue(a.negative_for_test(self.root,self.folder,'DEVICE-1'))

    def test_same_inputs_legacy_global_stale_candidate_reuses_facts(self):
        self.accept();self.change('decisions.json',lambda d:d['decisions'].append({'id':'D-LOCAL-COMPARISON','evidence':'Unrelated synthetic authority'}))
        old_stamp,_=v.context(self.root,self.folder,self.origin)
        stale=[r for r in self.origin['items'] if r['mode']=='manual' and v.state(r,old_stamp,v.manual_evidence_stamp(self.root,self.folder,r))=='stale']
        self.assertEqual(len(stale),3)
        request=self.capture();review=self.review(request)
        for x in review['change_findings']: x['classification']='unaffected_with_evidence'
        review['reuse']=[dict(claim_key=c['claim_key'],from_key=c['claim_key'],evidence='Complete isolated authority diff inspected',semantic_equivalence='Same criterion and source/test inputs') for c in request['active_versions']];review['assess']=[]
        a.apply_assessment(self.root,self.folder,request,review)
        self.assertEqual(len(review['assess']),0);self.assertTrue(a.resolve_claims(self.root,self.folder)['acceptance_eligible'])
        self.assertTrue(all(not row['history'] for row in self.plan()['items']));self.assertEqual(self.h.counter.read_text(),'1')

    def test_waiver_cannot_be_synthesized_from_pass(self):
        request=self.capture();review=self.review(request);review['assess'][0]['verdict']='approved_waiver'
        with self.assertRaisesRegex(ValueError,'REVIEW_INCOMPLETE'):a.apply_assessment(self.root,self.folder,request,review)

    def test_retirement_does_not_erase_unresolved_scope(self):
        self.accept();key=a.active_claims(self.plan())[0]['claim_key'];loc=a.active_claims(self.plan())[0]['locator']
        self.change('spec/requirements.json',lambda d:d['requirements'][0].update(status='deprecated'))
        a.reconcile_claims(self.root,self.folder,{loc:{'retire':True,'authority_evidence':'Synthetic owner explicitly removed scope'}})
        request=self.capture();review=self.review(request);a.apply_assessment(self.root,self.folder,request,review)
        self.assertIn('retire:'+key,[x.get('detail') for x in a.resolve_claims(self.root,self.folder)['blockers']])
        request=self.capture();review=self.review(request);review['barrier_resolutions']=[{'barrier_id':'retire:'+key,'authority_evidence':'Current deprecated source and owner removal','evidence':'Removed source traced in complete diff','addresses':'Original entire criterion has been explicitly removed, not silently lost'}]
        a.apply_assessment(self.root,self.folder,request,review)
        self.assertTrue(a.resolve_claims(self.root,self.folder)['acceptance_eligible'])

    def test_automatic_facts_bound_to_exact_attempt_and_assertion_ids(self):
        doc=self.plan();doc['items'][0].update(mode='automatic',gates=['unit'],coverage='Synthetic exact assertion binding',test_ids=['UT-1']);(self.folder/'verification.json').write_text(json.dumps(doc))
        a.reconcile_claims(self.root,self.folder);request,review=self.accept()
        old_ref=review['assess'][0]['fact_refs'][0];self.assertEqual(request['fact_refs'][old_ref]['ref']['container'],'check_attempt')
        self.h.execute();request=self.capture();review=self.review(request)
        self.assertNotIn(old_ref,request['fact_refs'])
        first=request['active_versions'][0];review['assess']=[x for x in review['assess'] if x['claim_key']!=first['claim_key']]
        for x in review['change_findings']:x['classification']='unaffected_with_evidence'
        review['reuse']=[{'claim_key':first['claim_key'],'from_key':first['claim_key'],'evidence':'Not a substitute for exact fact identity','semantic_equivalence':'Same criterion'}]
        with self.assertRaisesRegex(ValueError,'REVIEW_INCOMPLETE'):a.apply_assessment(self.root,self.folder,request,review)
        self.accept();self.assertTrue(a.resolve_claims(self.root,self.folder)['acceptance_eligible'])

    def test_affected_targets_cannot_use_reuse_action(self):
        self.accept();request=self.capture();review=self.review(request);key=request['active_versions'][0]['claim_key']
        # New affected declaration cannot be used as an exclusion proof.
        self.change('decisions.json',lambda d:d['decisions'].append({'id':'D-AFFECTED'}))
        request=self.capture();review=self.review(request);review['assess']=[x for x in review['assess'] if x['claim_key']!=key]
        review['reuse']=[{'claim_key':key,'from_key':key,'evidence':'Not exclusion','semantic_equivalence':'Unproven'}]
        with self.assertRaisesRegex(ValueError,'REVIEW_INCOMPLETE'):a.apply_assessment(self.root,self.folder,request,review)

    def test_unsigned_new_history_cannot_become_evidence(self):
        doc=self.plan();entry=copy.deepcopy(self.origin['items'][0]['history'][0]);doc['items'][0]['history'].append(entry)
        with self.assertRaisesRegex(ValueError,'CONTRACT_UNSUPPORTED'):a.validate_document(doc)
        doc=self.plan();doc['acceptance_contract']=True
        with self.assertRaisesRegex(ValueError,'CONTRACT_UNSUPPORTED'):a.validate_document(doc)

    def test_full_delivery_composition_keeps_non_acceptance_guards(self):
        self.accept();view=a.resolve_claims(self.root,self.folder)
        self.assertTrue(view['acceptance_eligible']);self.assertFalse(view['delivery_eligible'])
        manifest=a.compose_delivery(self.root,self.folder)
        self.assertTrue(manifest['delivery_eligible'],manifest['guard_results'])
        self.change('tasks.json',lambda d:d['tasks'][0].update(status='todo'))
        self.assertTrue(a.resolve_claims(self.root,self.folder)['acceptance_eligible'])
        manifest=a.compose_delivery(self.root,self.folder);self.assertFalse(manifest['delivery_eligible'])
        self.assertTrue(manifest['blockers'])

    def test_registration_control_does_not_change_semantic_world_but_is_validated(self):
        self.change('spec/requirements.json',lambda d:d['feature'].update(baseline={'version':1,'digest':'synthetic','deliveries':[]}))
        self.accept();frozen=self.capture()['world_digest']
        self.change('spec/requirements.json',lambda d:d['feature']['baseline']['deliveries'].append({'invalid':'not a valid registration'}))
        self.assertEqual(self.capture()['world_digest'],frozen)
        self.assertFalse(a.compose_delivery(self.root,self.folder)['delivery_eligible'])

    def test_shared_fix_writers_keep_workspace_and_plan_exclusion(self):
        @v.plan_mutation
        def foreign_writer(root,folder):
            with self.assertRaisesRegex(ValueError,'WORKSPACE_BUSY'):
                with a.mutation(root,folder):pass
        foreign_writer(self.root,self.folder)

    def test_device_negative_survives_review_staleness_and_held_lock(self):
        doc=self.plan();doc['items'][0]['test_ids']=['DEVICE-NEGATIVE'];(self.folder/'verification.json').write_text(json.dumps(doc));a.reconcile_claims(self.root,self.folder)
        request=self.capture();a.apply_assessment(self.root,self.folder,request,self.review(request,'partial'))
        with a.mutation(self.root,self.folder):
            self.assertTrue(a.negative_for_test(self.root,self.folder,'DEVICE-NEGATIVE'))

    def test_archived_feature_cannot_receive_new_fact_review_or_prepare(self):
        request=self.capture();review=self.review(request);before=(self.folder/'verification.json').read_bytes()
        self.change('spec/requirements.json',lambda d:d['feature'].update(archive={'archived':True,'history':[{'action':'archive','at':'2026-10-20T00:00:00+00:00','reason':'Synthetic archive','revision':self.h.helper.git('rev-parse','HEAD').strip(),'evidence':'Synthetic report','evidence_sha256':'0'*64}]}))
        with self.assertRaisesRegex(ValueError,'archived'):a.apply_assessment(self.root,self.folder,request,review)
        with self.assertRaisesRegex(ValueError,'archived'):a.record_fact(self.root,self.folder,self.plan()['items'][0]['id'],'passed',request['world_digest'],self.h.helper.git('rev-parse','HEAD').strip(),'No write','Synthetic')
        self.assertEqual((self.folder/'verification.json').read_bytes(),before)

    def test_reactivated_source_keeps_original_negative_identity(self):
        request=self.capture();review=self.review(request,'partial');a.apply_assessment(self.root,self.folder,request,review)
        old=a.active_claims(self.plan())[0]
        self.change('spec/requirements.json',lambda d:d['requirements'][0].update(status='deprecated'))
        a.reconcile_claims(self.root,self.folder,{old['locator']:{'retire':True,'authority_evidence':'Synthetic explicit removal'}})
        self.change('spec/requirements.json',lambda d:d['requirements'][0].update(status='confirmed'))
        a.reconcile_claims(self.root,self.folder)
        self.assertEqual(a.active_claims(self.plan())[0]['claim_key'],old['claim_key'])
        request=self.capture();review=self.review(request)
        with self.assertRaisesRegex(ValueError,'NEGATIVE_UNRESOLVED'):a.apply_assessment(self.root,self.folder,request,review)

    def test_known_dependency_mapping_changes_need_reconciliation(self):
        doc=self.plan();doc['items'][0].update(dependencies=['convert.py'],scope_reason='Actual source inspected');(self.folder/'verification.json').write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError,'PLAN_RECONCILIATION_REQUIRED'):self.capture()
        a.reconcile_claims(self.root,self.folder);self.assertEqual(a.active_claims(self.plan())[0]['execution_mapping']['dependencies'],['convert.py'])


if __name__=='__main__':unittest.main()
