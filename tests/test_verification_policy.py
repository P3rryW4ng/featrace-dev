"""Synthetic boundary tests, not a semantic review or UI/device certification."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

import test_verification
import verification_policy as p
import delivery_metadata as meta
import project


class VerificationPolicyTests(unittest.TestCase):
    def setUp(self):
        h=test_verification.VerificationTests();h.setUp();self.addCleanup(h.doCleanups)
        self.h=h;self.root=h.root;self.folder=h.folder;self.req=copy.deepcopy(h.req);self.impact=copy.deepcopy(h.doc)
        self.req['feature']['verification_policy']=1
        self.base=h.base;self.catalog={'policy_contract':{'schema_version':1,'rules':[]}}
        self.save_catalog()
        self.plan=dict(schema_version=1,environment='test',operations=['test'],units=[self.unit()],
                       checks=[self.check()],interactions=[],background=[],prior_findings=[],gate_map={'unit':['DISPLAY']},overlap_reasons={},policy_digest=None)
        self.impact['verification_plan']=self.plan;self.config=json.loads((self.base/'quality-gates.json').read_text())
        self.refresh_policy()

    def unit(self,ident='UI',paths=None,claims=None):
        return dict(id=ident,category='B',paths=paths or ['convert.py'],claims=claims or ['R-1:1'],sharing='local',effects=['presentation'],reason='Synthetic local appearance only',evidence='Inspected renderer and one consumer',tags=[])

    def check(self,ident='DISPLAY',units=None,claims=None):
        return dict(id=ident,units=units or ['UI'],claims=claims or ['R-1:1'],kind='display',reason='Compare the changed target layout',source='Synthetic user visual request')

    def save_catalog(self): (self.base/'quality-candidates.json').write_text(json.dumps(self.catalog))
    def refresh_policy(self):
        self.save_catalog();paths=sorted({x for u in self.plan['units'] for x in u['paths']})
        self.plan['policy_digest']=p.combined_policy(self.root,paths,self.plan['operations'],'test')['digest']
    def validate(self,stage='check',config=True):
        return p.validate_plan(self.root,self.folder,self.req,self.impact,self.config if config else None,stage)
    def persist(self):
        (self.folder/'spec/requirements.json').write_text(json.dumps(self.req));(self.folder/'impact.json').write_text(json.dumps(self.impact))
    def rule(self,**changes):
        path=self.base/'policy-source.md';path.write_text('Synthetic reviewed policy')
        rule=dict(id='RULE-1',source={'path':'.agent-workflow/project-baseline/policy-source.md','sha256':hashlib.sha256(path.read_bytes()).hexdigest()},scope={'paths':['convert.py'],'operations':['test'],'environment':'test'},kind='gate',disposition='follow',reason='Synthetic required check',authority='User scoped test authorization',enforced=False,reconciled=False,gate_names=['unit'],permission='allowed')
        rule.update(changes);return rule

    def test_local_display_selects_only_target_no_execution(self):
        before=list(self.folder.rglob('*'));result=self.validate()
        self.assertEqual(result['categories'],['B']);self.assertEqual(result['checks'],1)
        self.assertEqual(list(self.folder.rglob('*')),before)
        self.assertFalse((self.root/'.agent-workflow/scratch/count').exists())

    def test_shared_display_does_not_require_business_tests(self):
        self.plan['units'][0].update(category='C',sharing='shared',evidence='Two inspected render consumers, behavior unchanged')
        self.assertEqual(self.validate()['categories'],['C'])

    def test_ui_label_cannot_hide_state_or_shared_use(self):
        self.plan['units'][0]['effects'].append('state')
        with self.assertRaisesRegex(ValueError,'cannot hide'):self.validate()
        self.plan['units'][0]['effects']=['presentation'];self.plan['units'][0]['sharing']='shared'
        with self.assertRaisesRegex(ValueError,'local display'):self.validate()

    def test_comment_with_acceptance_change_is_not_nonruntime(self):
        self.plan['units'][0].update(category='A',effects=['acceptance'])
        with self.assertRaisesRegex(ValueError,'non-runtime'):self.validate()

    def test_unknown_is_draft_investigation_not_all_suite(self):
        self.plan['units'][0].update(category='U',sharing='unknown')
        self.assertEqual(self.validate('draft')['unresolved'],['UI'])
        with self.assertRaisesRegex(ValueError,'unknown impact'):self.validate()

    def test_mixed_units_require_joint_check_for_shared_path(self):
        self.plan['units'].append(self.unit('BEHAVIOR'));self.plan['units'][1].update(category='D',effects=['state'])
        self.plan['checks'].append(dict(self.check('LOGIC',['BEHAVIOR']),kind='behavior'))
        with self.assertRaisesRegex(ValueError,'interaction assessment'):self.validate()
        self.plan['interactions']=[dict(units=['UI','BEHAVIOR'],effect='interacting',check_ids=['DISPLAY'],evidence='State controls rendering')]
        with self.assertRaisesRegex(ValueError,'combined check'):self.validate()
        self.plan['checks'][0]['units'].append('BEHAVIOR')
        self.assertEqual(self.validate()['checks'],2)

    def test_cross_boundary_cannot_be_marked_local_behavior(self):
        self.plan['units'][0].update(category='D',effects=['contract']);self.plan['checks'][0]['kind']='behavior'
        with self.assertRaisesRegex(ValueError,'requires E'):self.validate()
        self.plan['units'][0]['category']='E';self.assertEqual(self.validate()['categories'],['E'])

    def test_new_changed_file_requires_classification(self):
        (self.root/'new.py').write_text('new behavior')
        with self.assertRaisesRegex(ValueError,'no classified unit'):self.validate()

    def test_expanded_check_needs_known_unit_and_claim(self):
        self.plan['checks'].append(self.check('UNRELATED',['OTHER']))
        with self.assertRaisesRegex(ValueError,'unknown check units'):self.validate()

    def test_display_and_claim_coverage_required(self):
        self.plan['checks'][0]['kind']='static'
        with self.assertRaisesRegex(ValueError,'target display'):self.validate()
        self.plan['checks'][0]['kind']='display';self.plan['units'][0]['claims'].append('B-1')
        with self.assertRaisesRegex(ValueError,'claim omitted'):self.validate()

    def test_old_unprepared_contract_is_not_silently_enabled(self):
        del self.req['feature']['verification_policy'];del self.impact['verification_plan']
        self.assertIsNone(p.validate_plan(self.root,self.folder,self.req,self.impact,self.config))

    def test_policy_missing_stops_new_plan(self):
        (self.base/'quality-candidates.json').unlink()
        with self.assertRaisesRegex(ValueError,'constraints unreviewed'):self.validate()

    def test_changed_applicable_rule_stops_but_unrelated_rule_does_not(self):
        rule=self.rule();self.catalog['policy_contract']['rules']=[rule];self.refresh_policy();self.validate()
        (self.base/'policy-source.md').write_text('changed')
        with self.assertRaisesRegex(ValueError,'source changed'):self.validate()
        rule['scope']['paths']=['unrelated/**'];self.refresh_policy();self.validate()

    def test_unresolved_or_unreconciled_rule_cannot_be_ignored(self):
        rule=self.rule(disposition='replace',enforced=True,authority='User approved replacement')
        self.catalog['policy_contract']['rules']=[rule];self.refresh_policy()
        with self.assertRaisesRegex(ValueError,'not reconciled'):self.validate()
        rule['reconciled']=True;self.refresh_policy();self.validate()
        rule['disposition']='pending';self.refresh_policy()
        with self.assertRaisesRegex(ValueError,'unresolved policy'):self.validate()

    def test_missing_resolution_authority_stops(self):
        self.catalog['policy_contract']['rules']=[self.rule(disposition='not_applicable',authority='')];self.refresh_policy()
        with self.assertRaisesRegex(ValueError,'authority required'):self.validate()

    def test_build_permission_is_not_lost_under_test_selection(self):
        rule=self.rule(permission='ask');rule['scope']['operations']=['build']
        self.catalog['policy_contract']['rules']=[rule];self.plan['operations'].append('build');self.refresh_policy()
        with self.assertRaisesRegex(ValueError,'permission ask'):self.validate()
        rule['permission']='allowed';rule['authority']='Current user authorizes test build';self.refresh_policy();self.validate()

    def test_mandatory_gate_and_unrelated_selection(self):
        self.catalog['policy_contract']['rules']=[self.rule(gate_names=['required'])];self.refresh_policy()
        with self.assertRaisesRegex(ValueError,'mandatory project gate'):self.validate()
        self.catalog['policy_contract']['rules']=[];self.refresh_policy()
        self.config['gates'].append(dict(self.config['gates'][0],name='unrelated'))
        with self.assertRaisesRegex(ValueError,'exactly selected'):self.validate()

    def test_duplicate_suite_has_to_be_reconciled(self):
        self.config['gates'].append(dict(self.config['gates'][0],name='unit-again'))
        self.plan['gate_map']['unit-again']=['DISPLAY']
        with self.assertRaisesRegex(ValueError,'duplicate physical'):self.validate()
        self.config['gates'][1]['command']=[sys.executable,'-c','print(2)']
        with self.assertRaisesRegex(ValueError,'unavoidable project obligation'):self.validate()
        self.plan['overlap_reasons']['unit|unit-again']='Synthetic enforced pair cannot be split; reviewed project rule'
        with self.assertRaisesRegex(ValueError,'unavoidable project obligation'):self.validate()
        self.catalog['policy_contract']['rules']=[self.rule(gate_names=['unit','unit-again'])];self.refresh_policy()
        self.validate()

    def test_plan_is_enforced_before_real_command(self):
        self.persist();self.plan['units'][0]['effects'].append('state');self.persist()
        with self.assertRaisesRegex(ValueError,'cannot hide'):project.quality_snapshot(self.root.resolve(),self.config)
        self.assertFalse((self.base/'quality-report.json').exists())

    def test_plan_enforces_in_contract_two_selection(self):
        import check_runs
        self.h.git('add','-A');self.h.git('commit','-qm','Synthetic workflow inputs')
        check_runs.prepare(self.root,'FEAT-001',[{'name':'unit','test_ids':['UT-1']}],'Synthetic selection')
        self.persist();self.plan['gate_map']={};self.persist()
        with self.assertRaisesRegex(ValueError,'exactly selected'):check_runs.selection(self.root,'FEAT-001')

    def test_followup_parent_unchanged_and_not_cloned(self):
        self.req['feature']['status']='complete';self.persist();self.h.git('add','-A');self.h.git('commit','-qm','Original delivery')
        original=(self.folder/'spec/requirements.json').read_bytes();head=self.h.git('rev-parse','HEAD').strip()
        context=p.followup_context(self.root,'FEAT-001',head,'Synthetic accepted delivery report')
        p.validate_followup(self.root,context)
        self.assertEqual((self.folder/'spec/requirements.json').read_bytes(),original)
        self.assertNotIn('requirements',context)
        request=self.root/'.agent-workflow/scratch/request.md';request.parent.mkdir(exist_ok=True);request.write_text('Change only the local icon')
        scripts=Path(p.__file__).parent
        run=subprocess.run([sys.executable,str(scripts/'init-change.py'),str(self.root),'FEAT-001-C1','--kind','change','--request-file',str(request),'--parent','FEAT-001','--delivery-revision',head,'--delivery-evidence','Synthetic accepted delivery report'],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)
        child=json.loads((self.folder.parent/'FEAT-001-C1/spec/requirements.json').read_text())
        self.assertEqual(child['requirements'],[]);self.assertEqual(child['feature']['change_context'],context)
        self.assertEqual(child['feature']['verification_policy'],1);self.assertEqual((self.folder/'spec/requirements.json').read_bytes(),original)

    def test_followup_requires_committed_complete_parent(self):
        head=self.h.git('rev-parse','HEAD').strip()
        with self.assertRaisesRegex(ValueError,'complete delivery'):p.followup_context(self.root,'FEAT-001',head,'Report')
        self.req['feature']['status']='complete';self.persist()
        with self.assertRaisesRegex(ValueError,'commit the parent'):p.followup_context(self.root,'FEAT-001',head,'Report')

    def test_background_changes_are_separate_and_cannot_be_dropped(self):
        self.req['feature']['status']='complete';self.persist();self.h.git('add','-A');self.h.git('commit','-qm','Parent accepted')
        delivered=self.h.git('rev-parse','HEAD').strip()
        (self.root/'state.py').write_text('historical merged change');self.h.git('add','state.py');self.h.git('commit','-qm','Unrelated merge')
        context=p.followup_context(self.root,'FEAT-001',delivered,'Accepted report')
        self.req['feature'].update(status='drafted',change_context=context)
        self.impact['base_revision']=context['scope_base_revision']
        with self.assertRaisesRegex(ValueError,'classify all background'):self.validate()
        self.plan['background']=[dict(paths=['state.py'],effect='affected',claims=[],evidence='Changed shared state')]
        with self.assertRaisesRegex(ValueError,'current regression claims'):self.validate()
        self.plan['background'][0].update(effect='unaffected',evidence='Inspected old state and all relevant consumers; local renderer independent')
        self.assertEqual(self.validate()['background_paths'],1)
        self.plan['background'][0]['effect']='unknown'
        with self.assertRaisesRegex(ValueError,'unknown impact'):self.validate()

    def test_followup_cannot_omit_parent_failure_or_open_fix(self):
        self.req['feature']['status']='complete';self.persist()
        plan=json.loads((self.folder/'verification.json').read_text());plan['items'][0]['history'].append({'status':'failed','actual':'Observed failure'})
        (self.folder/'verification.json').write_text(json.dumps(plan))
        (self.folder/'fixes.json').write_text(json.dumps({'feature_id':'FEAT-001','fixes':[{'id':'FIX-OLD','status':'resolved'}]}))
        self.h.git('add','-A');self.h.git('commit','-qm','Historical delivery with subsequent visible negatives')
        context=p.followup_context(self.root,'FEAT-001',self.h.git('rev-parse','HEAD').strip(),'Original delivered identity inspected')
        self.assertEqual(len(context['parent_findings']),2)
        self.req['feature'].update(status='drafted',change_context=context);self.impact['base_revision']=context['scope_base_revision']
        with self.assertRaisesRegex(ValueError,'do not escape prior'):self.validate()
        self.plan['prior_findings']=[dict(id=x['id'],effect='unknown',claims=[],evidence='Relevance requires investigation') for x in context['parent_findings']]
        with self.assertRaisesRegex(ValueError,'unknown impact'):self.validate()
        for finding in self.plan['prior_findings']:finding.update(effect='covered',claims=['R-1:1'],evidence='Current objective includes this regression and needs actual new evidence')
        self.validate()
        context['parent_findings']=[]
        with self.assertRaisesRegex(ValueError,'parent negative inventory'):p.validate_followup(self.root,context)

    def test_original_context_tamper_or_wrong_baseline_rejected(self):
        self.req['feature']['status']='complete';self.persist();self.h.git('add','-A');self.h.git('commit','-qm','Delivery')
        context=p.followup_context(self.root,'FEAT-001',self.h.git('rev-parse','HEAD').strip(),'Accepted report')
        context['background_paths']=['hidden.py']
        with self.assertRaisesRegex(ValueError,'background inventory'):p.validate_followup(self.root,context)

    def test_actual_contract_report_not_version_label(self):
        self.assertEqual(p.entry_status(self.root,'FEAT-001')['verification_schema'],1)
        self.req['feature']['status']='complete';self.persist()
        self.assertEqual(p.entry_status(self.root,'FEAT-001')['route'],'historical_delivery_or_explicit_followup')

    def test_pure_display_cannot_add_unrelated_business_check(self):
        self.plan['checks'].append(dict(self.check('BUSINESS'),kind='behavior'))
        with self.assertRaisesRegex(ValueError,'project-rule basis'):self.validate()
        self.plan['checks'][-1]['source']='policy:REQUIRED'
        with self.assertRaisesRegex(ValueError,'no applicable'):self.validate()
        rule=self.rule(id='REQUIRED');self.catalog['policy_contract']['rules']=[rule];self.refresh_policy();self.validate()

    def test_scoped_schema7_hosts_and_legacy_fallback_refuse(self):
        import acceptance_contract as acceptance
        import check_runs
        import verification
        self.persist();check_runs.prepare(self.root,'FEAT-001',[{'name':'unit','test_ids':['UT-1']}],'Explicit synthetic test contract')
        verification.sync(self.root,self.folder);self.h.git('add','-A');self.h.git('commit','-qm','Scoped sources committed')
        approval={'active_features':['FEAT-001'],'hosts':[{'name':'synthetic capable reader','schema6_capable':True}],'evidence':'Explicit fixture opt-in'}
        with self.assertRaisesRegex(ValueError,'schema7 capable'):acceptance.prepare(self.root,self.folder,approval)
        self.assertIn('schema7',' '.join(verification.validate_verification(self.root,self.folder,self.req,'check')))
        approval['hosts'][0]['verification_policy_capable']=True
        doc=acceptance.prepare(self.root,self.folder,approval)
        self.assertEqual(doc['schema_version'],7);acceptance.validate_document(doc)
        self.assertFalse(acceptance.resolve_claims(self.root,self.folder)['acceptance_eligible'])
        doc['schema_version']=6
        with self.assertRaisesRegex(ValueError,'cannot silently enable'):acceptance.capture_assessment(self.root,self.folder,doc=doc)

    def test_regular_inventory_exposes_actual_contract_but_source_inventory_stays_minimal(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('scope_verify_inputs',Path(p.__file__).with_name('verify-inputs.py'))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        normal=module.collect(self.root.resolve(),self.folder.name)
        minimal=module.collect(self.root.resolve(),self.folder.name,include_acceptance=False)
        self.assertEqual(normal['contract_route']['verification_schema'],1)
        self.assertFalse(normal['contract_route']['automatic_preparation'])
        self.assertNotIn('contract_route',minimal)

    def test_scoped_plan_cannot_prepare_legacy_batch(self):
        import manual_scope
        self.persist()
        with self.assertRaisesRegex(ValueError,'schema7'):manual_scope.prepare(self.root,self.folder)

    def test_new_feature_opt_in_does_not_modify_existing_feature(self):
        request=self.root/'.agent-workflow/scratch/new.md';request.parent.mkdir(exist_ok=True);request.write_text('New display requirement')
        before=(self.folder/'spec/requirements.json').read_bytes()
        run=subprocess.run([sys.executable,str(Path(p.__file__).parent/'init-change.py'),str(self.root),'NEW-UI','--kind','change','--request-file',str(request),'--verification-policy'],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)
        child=json.loads((self.folder.parent/'NEW-UI/spec/requirements.json').read_text())
        self.assertEqual(child['feature']['verification_policy'],1);self.assertNotIn('change_context',child['feature'])
        self.assertEqual((self.folder/'spec/requirements.json').read_bytes(),before)


class ReviewedReuseTests(unittest.TestCase):
    def test_current_batch_judgment_can_be_cited_but_stale_ref_cannot(self):
        import test_manual_scope
        import claim_review
        h=test_manual_scope.ManualScopeTests();h.setUp();self.addCleanup(h.doCleanups)
        h.apply();snapshot=claim_review.identity(h.root,h.folder)
        reuse=snapshot['review_work']['reuse_applicability'];self.assertEqual(len(reuse),3)
        findings=[dict(id=c['id'],verdict='supported',source_basis='Prior finding inspected',required_scope='Same complete criterion',observed_scope='Current preserved original observation',evidence_ref=c['manual_scope']['review_ref'],counterexample_check='Checked for changed input and contradictions',applicability_ref=c['manual_scope']['review_ref']) for c in snapshot['claims']]
        review=dict(feature_id=h.folder.name,input_digest=snapshot['input_digest'],reviewer='Synthetic final reviewer',findings=findings)
        (h.folder/'claim-review.json').write_text(json.dumps(review))
        self.assertEqual(claim_review.validate(h.root,h.folder),[])
        review['findings'][0]['applicability_ref']+='wrong'
        (h.folder/'claim-review.json').write_text(json.dumps(review))
        self.assertIn('stale/unsupported',' '.join(claim_review.validate(h.root,h.folder)))
        (h.root/'convert.py').write_text('changed actual behavior')
        self.assertEqual(claim_review.identity(h.root,h.folder)['review_work']['reuse_applicability'],[])

    def test_typed_metadata_preserves_schema5_original_judgment(self):
        import test_manual_scope
        import manual_scope
        h=test_manual_scope.ManualScopeTests();h.setUp();self.addCleanup(h.doCleanups);h.apply()
        before=manual_scope.view(h.root,h.folder)
        revision=h.h.git('rev-parse','HEAD').strip();h.h.git('update-ref','refs/remotes/origin/synthetic',revision)
        meta.record(h.root,h.folder,revision,'refs/remotes/origin/synthetic')
        self.assertEqual(manual_scope.view(h.root,h.folder),before)


class PublicationMetadataTests(unittest.TestCase):
    def test_typed_publication_does_not_stale_acceptance_but_free_note_does(self):
        import test_acceptance_contract
        import acceptance_contract as a
        h=test_acceptance_contract.AcceptanceContractTests();h.setUp();self.addCleanup(h.doCleanups)
        h.accept();before=(h.folder/'verification.json').read_bytes();revision=h.h.helper.git('rev-parse','HEAD').strip()
        h.h.helper.git('update-ref','refs/remotes/origin/fixture',revision)
        result=meta.record(h.root,h.folder,revision,'refs/remotes/origin/fixture')
        self.assertEqual(result['publication_observation'],'contained_in_observed_tracking_ref')
        self.assertEqual((h.folder/'verification.json').read_bytes(),before)
        self.assertTrue(a.resolve_claims(h.root,h.folder)['acceptance_eligible'])
        data=json.loads((h.folder/'delivery-metadata.json').read_text());data['business_waiver']='Ignore missing behavior'
        (h.folder/'delivery-metadata.json').write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'unsupported delivery metadata'):a.capture_assessment(h.root,h.folder)

    def test_publication_cannot_mutate_archived_feature(self):
        h=test_verification.VerificationTests();h.setUp();self.addCleanup(h.doCleanups)
        req=json.loads((h.folder/'spec/requirements.json').read_text());req['feature']['archive']={'archived':True,'history':[]}
        (h.folder/'spec/requirements.json').write_text(json.dumps(req))
        with self.assertRaises(ValueError):meta.record(h.root,h.folder,'a'*40,'refs/remotes/origin/test')
        self.assertFalse((h.folder/'delivery-metadata.json').exists())

    def test_publication_rejects_free_prose_and_nonremote_ref(self):
        value=dict(schema_version=1,feature_id='F',code_revision='a'*40,tracking_ref='main',tracking_revision='a'*40,observed_at='2026-10-21T00:00:00+00:00')
        with self.assertRaisesRegex(ValueError,'remote-tracking'):meta.validate(value,'F')
        value['tracking_ref']='refs/remotes/origin/main';value['note']='approve missing behavior'
        with self.assertRaisesRegex(ValueError,'unsupported delivery'):meta.validate(value,'F')
