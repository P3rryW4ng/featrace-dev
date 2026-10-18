import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_verification
import verification as v
import manual_scope as m


class ManualScopeTests(unittest.TestCase):
    def setUp(self):
        self.make_fixture()

    def make_fixture(self, count=1):
        self.h = test_verification.VerificationTests(); self.h.setUp(); self.addCleanup(self.h.doCleanups)
        self.root, self.folder = self.h.root.resolve(), self.h.folder.resolve()
        if count != 1:
            from intake_helpers import attach_intake
            req=json.loads((self.folder/'spec/requirements.json').read_text());req['requirements'][0]['acceptance_criteria']=['Fixture AC %d: abc becomes ABC' % i for i in range(count)]
            attach_intake(self.folder,req);v.sync(self.root,self.folder)
        (self.root/'other.py').write_text('unrelated = 1\n')
        self.h.doc['allowed_paths'].append('other.py'); self.h.save()
        self.h.git('add', '-A'); self.commit('initial contract')
        self.base = self.h.git('rev-parse', 'HEAD').strip()
        (self.folder/'evidence').mkdir(); (self.folder/'evidence/origin.txt').write_text('Synthetic original clean tree/package: '+self.base)
        from contextlib import nullcontext
        with (patch.object(v, 'render') if count != 1 else nullcontext()):
            for row in v.load_plan(self.folder)['items']:
                if row['mode'] == 'manual':
                    stamp, head = v.context(self.root,self.folder,v.load_plan(self.folder))
                    v.record(self.root,self.folder,row['id'],'passed',stamp,head,'Synthetic complete fixture observation','evidence/origin.txt')
        self.original = copy.deepcopy(v.load_plan(self.folder))
        self.h.git('add', '.agent-workflow'); self.commit('record originals')
        self.records_at = self.h.git('rev-parse', 'HEAD').strip()
        (self.root/'other.py').write_text('unrelated = 2\n'); self.h.git('add','other.py'); self.commit('unrelated business change')
        req=json.loads((self.folder/'spec/requirements.json').read_text());req['requirements'][0]['assumptions'].append('Sibling rule explanation; reviewer must verify actual independence')
        from intake_helpers import attach_intake
        attach_intake(self.folder, req)
        m.prepare(self.root,self.folder)
        self.ids=[r['id'] for r in v.load_plan(self.folder)['items'] if r['mode']=='manual']

    def commit(self, message):
        self.h.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm',message)

    def capture(self, ids=None):
        return m.capture(self.root,self.folder,[{'item_id':i,'contract_revision':self.records_at} for i in (ids or self.ids)])

    def review(self, snap):
        return {'input_digest':snap['input_digest'],'independent_context':True,'reviewer':'Synthetic independent review fixture',
                'apply_ids':[t['item_id'] for t in snap['targets']],
                'assessments':{c:{'evidence':'Actual fixture diff inspected; original conversion and state unchanged'} for t in snap['targets'] for c in t['changes']},
                'findings':[{'item_id':t['item_id'],'verdict':'supported','assessment_refs':{c:'unaffected' for c in t['changes']},
                             'dependencies':['convert.py','state.py'],'claim_evidence':'Original fixture observation matches complete current claim',
                             'dependency_evidence':'Changed isolated other.py has no conversion caller/import relationship',
                             'contract_evidence':'Whole parent and sibling assumption inspected; no shared condition changed',
                             'environment_evidence':'Synthetic non-device fixture has no external state',
                             'counterexample':'A converter/shared initializer change would require new evidence',
                             **({'contract_record':{'revision':t['contract_revision'],'tested_revision':t['original']['tested_revision'],'explanation':'Archived original result saved in subsequent workflow-only commit; every intervening business tree matched'}} if 'contract_record' in t else {}),
                             'original_identity':{'revision':self.base,'worktree_verified':True,'evidence_refs':['evidence/origin.txt'],'explanation':'Synthetic archived clean original identity'}} for t in snap['targets']]}

    def apply(self, snap=None, review=None):
        snap = snap or self.capture(); return m.apply(self.root,self.folder,snap,review or self.review(snap))

    def states(self):
        doc=v.load_plan(self.folder);stamp,_=v.context(self.root,self.folder,doc);shared=v.check_currency(self.root,self.folder)
        return {r['id']:v.state(r,stamp,v.row_evidence_stamp(self.root,self.folder,r,shared)) for r in doc['items']}

    def test_batch_keeps_original_history_and_exact_repeat_and_recapture_idempotent(self):
        snap=self.capture();review=self.review(snap);self.apply(snap,review)
        doc=v.load_plan(self.folder);self.assertTrue(all(self.states()[i]=='retained' for i in self.ids))
        for row in doc['items']:self.assertEqual(row['history'],next(r for r in self.original['items'] if r['id']==row['id'])['history'])
        self.apply(snap,review);self.assertEqual(v.load_plan(self.folder),doc)
        newer=self.capture();self.apply(newer,self.review(newer));self.assertEqual(v.load_plan(self.folder),doc)
        self.assertEqual(len(doc['manual_scope_reviews']),1)
        scope=m.view(self.root,self.folder,doc)['items'][self.ids[0]]
        self.assertIsNone(scope['observed_at']);self.assertEqual(scope['original_registered_at'],doc['items'][0]['history'][0]['at'])
        self.assertNotIn('Synthetic complete fixture observation',json.dumps(doc['manual_scope_reviews']))
        self.assertIn('Manual applicability',(self.folder/'verification.md').read_text())

    def test_mixed_supported_unknown_and_affected_only_adopts_selected_subset(self):
        snap=self.capture();review=self.review(snap);review['findings'][1]['verdict']='unknown';review['findings'][2]['verdict']='affected';review['apply_ids']=[self.ids[0]]
        self.apply(snap,review);states=self.states();self.assertEqual(states[self.ids[0]],'retained');self.assertEqual(states[self.ids[1]],'stale');self.assertEqual(states[self.ids[2]],'stale')
        doc=v.load_plan(self.folder);before=copy.deepcopy(doc)
        repeat=self.capture();same=copy.deepcopy(review);same['input_digest']=repeat['input_digest']
        self.apply(repeat,same);self.assertEqual(v.load_plan(self.folder),before)
        invalid=self.capture();bad=self.review(invalid);bad['findings'][0]['verdict']='partial'
        with self.assertRaises(ValueError):self.apply(invalid,bad)
        self.assertEqual(v.load_plan(self.folder),before)

    def test_actual_failure_or_unavailable_never_borrows_older_green(self):
        self.apply();doc=v.load_plan(self.folder);stamp,head=v.context(self.root,self.folder,doc)
        v.record(self.root,self.folder,self.ids[0],'failed',stamp,head,'Observed incorrect fixture result','Synthetic failure evidence')
        self.assertNotEqual(self.states()[self.ids[0]],'retained')
        with self.assertRaisesRegex(ValueError,'latest passed'):self.capture([self.ids[0]])
        self.assertEqual(self.states()[self.ids[1]],'retained')

    def test_code_or_authority_or_archive_change_stales_scope_without_reexecution(self):
        self.apply();(self.root/'convert.py').write_text('changed')
        self.assertTrue(all(self.states()[i]=='stale' for i in self.ids))
        self.h.git('checkout','--','convert.py');self.assertTrue(all(self.states()[i]=='retained' for i in self.ids))
        (self.folder/'evidence/origin.txt').write_text('Changed original identity')
        self.assertTrue(all(self.states()[i]=='stale' for i in self.ids))
        self.assertFalse((self.folder/'check-runs').exists())

    def test_progress_and_other_row_outcome_do_not_resign_supported_fact(self):
        self.apply();doc=v.load_plan(self.folder);history=copy.deepcopy(doc['items'][0]['history'])
        req=json.loads((self.folder/'spec/requirements.json').read_text());req['feature']['status']='complete';(self.folder/'spec/requirements.json').write_text(json.dumps(req))
        self.assertTrue(all(self.states()[i]=='retained' for i in self.ids))
        self.assertEqual(v.load_plan(self.folder)['items'][0]['history'],history)
        req['feature']['status_note']='New undecided behavioral limit';(self.folder/'spec/requirements.json').write_text(json.dumps(req))
        self.assertTrue(all(self.states()[i]=='stale' for i in self.ids))

    def test_shared_dependency_change_allowed_to_review_but_not_automatically_supported(self):
        (self.root/'state.py').write_text('shared state changed\n');self.h.git('add','state.py');self.commit('shared dependency changed')
        snap=self.capture();review=self.review(snap)
        key=next(c for c in review['assessments'] if c.endswith(':state.py'));review['findings'][0]['assessment_refs'][key]='unknown'
        before=(self.folder/'verification.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'contradicts'):self.apply(snap,review)
        self.assertEqual((self.folder/'verification.json').read_bytes(),before)
        review['findings'][0]['environment_evidence']=''
        with self.assertRaises(ValueError):self.apply(snap,review)

    def test_capture_and_save_drift_missing_assessments_and_self_review_refused(self):
        snap=self.capture();review=self.review(snap);before=(self.folder/'verification.json').read_bytes()
        for key in ['independent_context','assessments']:
            bad=copy.deepcopy(review);bad[key]=False if key=='independent_context' else {}
            with self.assertRaises(ValueError):self.apply(snap,bad)
            self.assertEqual((self.folder/'verification.json').read_bytes(),before)
        doc=v.load_plan(self.folder);doc['items'][0]['coverage']='Concurrent mapping edit';v.save(self.folder/'verification.json',doc)
        moved=(self.folder/'verification.json').read_bytes()
        with self.assertRaises(ValueError):self.apply(snap,review)
        self.assertEqual((self.folder/'verification.json').read_bytes(),moved)

    def test_corrupt_event_cross_claim_reference_and_origin_mutation_rejected(self):
        self.apply();doc=v.load_plan(self.folder)
        bad=copy.deepcopy(doc);bad['manual_scope_reviews'][0]['review']['reviewer']='Changed';v.save(self.folder/'verification.json',bad)
        with self.assertRaises(ValueError):v.load_plan(self.folder)
        bad=copy.deepcopy(doc);bad['items'][0]['manual_scope_ref']['item_id']=self.ids[1];v.save(self.folder/'verification.json',bad)
        with self.assertRaises(ValueError):v.load_plan(self.folder)
        bad=copy.deepcopy(doc);bad['items'][0]['manual_scope_ref']='corrupt';v.save(self.folder/'verification.json',bad)
        with self.assertRaises(ValueError):v.load_plan(self.folder)
        bad=copy.deepcopy(doc);bad['items'][0]['history'][0]['actual']='Mutated old observation';v.save(self.folder/'verification.json',bad)
        with self.assertRaises(ValueError):v.load_plan(self.folder)

    def test_cli_old_installed_reader_refuses_schema_and_sync_preserves_mode(self):
        self.h.run_script('evidence_carry.py','prepare-batch',self.root,'FEAT-001')
        v.sync(self.root,self.folder);self.assertEqual(v.load_plan(self.folder)['schema_version'],5)
        import io, tarfile
        raw=subprocess.check_output(['git','archive','d2d0850','skills/dev'],cwd=Path(__file__).resolve().parents[1])
        with tempfile.TemporaryDirectory() as work:
            with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
                self.assertTrue(all(x.isfile() or x.isdir() for x in archive.getmembers()));archive.extractall(work)
            old=Path(work)/'skills/dev/core/scripts/verification.py'
            p=subprocess.run([sys.executable,'-B',str(old),'status',str(self.root),'FEAT-001'],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0);self.assertIn('schema',p.stderr)

    def test_new_execution_mode_and_schema_five_survive_run_and_adoption(self):
        import check_runs
        check_runs.prepare(self.root,'FEAT-001',[{'name':'unit','test_ids':['UT-1']}],'Synthetic mode-2 check selection')
        v.sync(self.root,self.folder)
        self.assertEqual(v.run(self.root,self.folder),2)
        doc=v.load_plan(self.folder);self.assertEqual(doc['schema_version'],5);self.assertEqual(doc['execution_contract'],2)
        self.apply();self.assertTrue(all(self.states()[i]=='retained' for i in self.ids))

    def test_new_negative_is_not_erased_by_fresh_reviewer_or_missing_pointer(self):
        snap=self.capture();review=self.review(snap);review['findings'][1]['verdict']='unknown';review['apply_ids']=[self.ids[0],self.ids[2]]
        self.apply(snap,review);doc=v.load_plan(self.folder)
        newer=self.capture();positive=self.review(newer)
        with self.assertRaisesRegex(ValueError,'negative assessment'):self.apply(newer,positive)
        self.assertEqual(v.load_plan(self.folder),doc)
        bad=copy.deepcopy(doc);bad['items'][1].pop('manual_scope_ref');v.save(self.folder/'verification.json',bad)
        with self.assertRaisesRegex(ValueError,'latest assessment'):v.load_plan(self.folder)

    def test_unrelated_row_mapping_and_workflow_commit_preserve_other_claim(self):
        self.apply();doc=v.load_plan(self.folder);doc['items'][1]['coverage']='Different description for this row only';v.save(self.folder/'verification.json',doc)
        states=self.states();self.assertEqual(states[self.ids[0]],'retained');self.assertEqual(states[self.ids[1]],'stale')
        self.h.git('add','.agent-workflow');self.commit('workflow-only record commit')
        self.assertEqual(self.states()[self.ids[0]],'retained')

    def test_unknown_declared_input_and_busy_workspace_do_not_certify(self):
        self.apply()
        from check_runs import execution_lock
        with execution_lock(self.root):self.assertTrue(all(self.states()[i]=='stale' for i in self.ids))
        (self.h.base/'evidence-files.json').write_text(json.dumps({'files':['missing-required.txt']}))
        self.assertTrue(all(self.states()[i]=='stale' for i in self.ids))

    def test_batch_save_failure_and_verification_lock_leave_original_bytes(self):
        snap=self.capture();review=self.review(snap);before=(self.folder/'verification.json').read_bytes()
        with patch.object(v,'save',side_effect=OSError('Synthetic save failure')):
            with self.assertRaises(OSError):self.apply(snap,review)
        self.assertEqual((self.folder/'verification.json').read_bytes(),before)
        import fcntl
        lock=self.root/'.agent-workflow/scratch/verification-FEAT-001.lock'
        with lock.open('a') as stream:
            fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError,'busy'):self.apply(snap,review)
        self.assertEqual((self.folder/'verification.json').read_bytes(),before)
        self.apply(snap,review)

    def test_forty_six_claims_share_inputs_one_save_and_no_new_history(self):
        self.make_fixture(44);self.assertEqual(len(self.ids),46)
        snap=self.capture();review=self.review(snap);original=v.load_plan(self.folder)
        with patch.object(m,'inputs',wraps=m.inputs) as reads, patch.object(v,'save',wraps=v.save) as saves:
            self.apply(snap,review)
        self.assertEqual(saves.call_count,1);self.assertLessEqual(reads.call_count,6)
        doc=v.load_plan(self.folder);self.assertEqual(len(doc['manual_scope_reviews']),1)
        self.assertEqual([r['history'] for r in doc['items']],[r['history'] for r in original['items']])
        self.assertTrue(all(self.states()[i]=='retained' for i in self.ids))

    def test_audit_status_views_and_final_claim_review_bind_same_scope(self):
        self.h.run_script('verification.py','run',self.root,'FEAT-001',expected=2)
        self.apply();self.h.run_script('audit-delivery.py',self.root,'FEAT-001')
        self.assertIn('MANUAL_APPLICABILITY:',self.h.run_script('feature-status.py',self.root,'FEAT-001'))
        inputs=json.loads(self.h.run_script('verify-inputs.py',self.root,'FEAT-001'))
        self.assertEqual(inputs['manual_scope']['items'][self.ids[0]]['state'],'current')
        from claim_review import identity
        claims=identity(self.root,self.folder);self.assertEqual(len(claims['claims']),3)
        self.assertTrue(all(c['result_status']=='retained' and c['manual_scope']['state']=='current' for c in claims['claims']))
        self.assertEqual(len(claims['manual_scope_review_refs']),1)
        import stage_view
        stage=stage_view.capture(self.root,'FEAT-001','verify')
        self.assertIn('manual_scope',json.dumps(stage))
        self.h.run_script('archive-preflight.py',self.root,'FEAT-001')
        self.assertIn('Reviewed manual applicability',(self.folder/'delivery-report.md').read_text())
        snap=self.capture();bad=self.review(snap);bad['findings'][0]['verdict']='unknown';bad['apply_ids']=self.ids[1:]
        self.apply(snap,bad);self.h.run_script('audit-delivery.py',self.root,'FEAT-001',expected=1)

    def test_missing_original_or_late_business_contract_record_refused(self):
        bad=[{'item_id':self.ids[0],'contract_revision':self.h.git('rev-parse','HEAD').strip()}]
        with self.assertRaisesRegex(ValueError,'business tree changed'):m.capture(self.root,self.folder,bad)
        (self.folder/'evidence/origin.txt').unlink()
        snap=self.capture();review=self.review(snap)
        with self.assertRaisesRegex(ValueError,'archived original identity'):self.apply(snap,review)

    def test_symlink_feature_and_corrupt_mode_refused(self):
        alias=self.root/'.agent-workflow/features/ALIAS';alias.symlink_to(self.folder,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'symlink'):m.capture(self.root,alias,[])
        doc=v.load_plan(self.folder);doc['execution_contract']=3;v.save(self.folder/'verification.json',doc)
        with self.assertRaisesRegex(ValueError,'unsupported automatic'):v.load_plan(self.folder)

    def test_schema_five_corrections_keep_history_and_need_scope_reassessment(self):
        self.apply()
        from result_corrections import capture,apply
        row=v.load_plan(self.folder)['items'][0];original=copy.deepcopy(row['history'])
        change=[{'item_id':self.ids[0],'history_index':0,'field':'evidence','replacement':'Precise archived identity citation: evidence/origin.txt',
                 'reason':'Synthetic description-only correction','support_refs':['.agent-workflow/features/FEAT-001/evidence/origin.txt']}]
        frozen=capture(self.root,self.folder,change)
        review={'input_digest':frozen['input_digest'],'status':'supported','independent_context':True,'reviewer':'Synthetic note reviewer',
                'scope_evidence':'Only descriptive evidence citation changed', 'identity_unchanged':'Original fixture identity preserved',
                'coverage_unchanged':'No asserted behavior changed', 'counterexample':'Adding claims would invalidate note correction',
                'corrections':[{'item_id':self.ids[0],'history_index':0,'field':'evidence','status':'metadata_only','evidence':'Exact original citation inspected'}]}
        import tempfile
        with tempfile.TemporaryDirectory() as work:
            a,b=Path(work)/'capture.json',Path(work)/'review.json';a.write_text(json.dumps(frozen));b.write_text(json.dumps(review))
            apply(self.root,self.folder,a,b)
        doc=v.load_plan(self.folder);self.assertEqual(doc['schema_version'],5);self.assertEqual(doc['items'][0]['history'],original)
        self.assertEqual(self.states()[self.ids[0]],'stale');self.assertEqual(self.states()[self.ids[1]],'retained')

    def test_one_shared_change_can_affect_one_claim_without_blocking_supported_subset(self):
        snap=self.capture();review=self.review(snap);first=review['findings'][0]
        key=next(c for c in first['assessment_refs'] if c.startswith('project:'))
        first['assessment_refs'][key]='affected';first['verdict']='affected';review['apply_ids']=self.ids[1:]
        self.apply(snap,review)
        states=self.states();self.assertEqual(states[self.ids[0]],'stale');self.assertTrue(all(states[i]=='retained' for i in self.ids[1:]))
