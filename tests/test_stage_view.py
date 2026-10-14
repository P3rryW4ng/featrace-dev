import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path
import test_verification
from stage_view import capture, check
from verification import sync, load_plan, context, record


class StageViewTests(unittest.TestCase):
    def setUp(self):
        self.helper = test_verification.VerificationTests(); self.helper.setUp(); self.addCleanup(self.helper.doCleanups)
        self.root, self.folder = self.helper.root, self.helper.folder
        req=json.loads((self.folder/'spec/requirements.json').read_text())
        self.parent=copy.deepcopy(req['requirements'][0])
        req['requirements'].append({'id':'R-OTHER','statement':'Unrelated story','status':'confirmed',
                                   'acceptance_criteria':['Other output'],'tasks':['T-OTHER'],'tests':['TEST-OTHER'],'sources':[],
                                   'assumptions':['Large unrelated assumption '+('x'*8000)]})
        (self.folder/'spec/requirements.json').write_text(json.dumps(req))
        tasks={'feature_id':'FEAT-001','tasks':[{'id':'T-FOCUS','requirement_ids':['R-1'],'title':'Current task'},
                                             {'id':'T-OTHER','requirement_ids':['R-OTHER'],'title':'Unrelated task'}]}
        (self.folder/'tasks.json').write_text(json.dumps(tasks))
        (self.folder/'decisions.json').write_text(json.dumps({'feature_id':'FEAT-001','decisions':[
            {'id':'D-SHARED','status':'approved','question':'Global constraint without structured scope'},
            {'id':'D-OTHER','status':'approved','requirement_ids':['R-OTHER'],'question':'Unrelated constraint'},
            {'id':'D-PENDING','status':'pending','requirement_ids':['R-OTHER'],'question':'Global unresolved choice'}]}))
        sync(self.root,self.folder)

    def tree(self):
        return {p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file() and '.git' not in p.parts}

    def test_task_projection_preserves_full_parent_shared_rules_and_global_unknowns(self):
        before=self.tree(); view=capture(self.root,'FEAT-001','test',['T-FOCUS'])
        self.assertEqual(view['requirements'][0],self.parent)
        self.assertEqual(view['omitted_requirements'],['R-OTHER'])
        self.assertEqual({d['id'] for d in view['decisions']},{'D-SHARED','D-PENDING'})
        self.assertIn('unresolved_decision: D-PENDING',view['global_attention'])
        self.assertIn('B-2',{b['id'] for b in view['impact']['behaviors']})
        self.assertEqual(before,self.tree())
        self.assertIsNone(view['metrics']['tokens']);self.assertIsNone(view['metrics']['cost'])
        self.assertLess(view['metrics']['projected_payload_bytes'],view['metrics']['canonical_record_bytes'])

    def test_handoff_rejects_source_code_canonical_or_payload_drift(self):
        for target in ('convert.py','.agent-workflow/features/FEAT-001/decisions.json',
                       '.agent-workflow/features/FEAT-001/sources/prd-original.txt'):
            view=capture(self.root,'FEAT-001','verify',['T-FOCUS'])
            path=self.root/target;original=path.read_bytes() if path.exists() else None
            if target.endswith('.json'):
                value=json.loads(path.read_text());value['decisions'][0]['question']+=' updated';path.write_text(json.dumps(value))
            else:path.parent.mkdir(parents=True,exist_ok=True);path.write_text('changed input')
            with self.assertRaises(ValueError):check(self.root,'FEAT-001',view)
            if original is None:path.unlink()
            else:path.write_bytes(original)
        view=capture(self.root,'FEAT-001','verify',['T-FOCUS']);view['requirements'][0]['statement']='forged claim'
        with self.assertRaisesRegex(ValueError,'content changed'):check(self.root,'FEAT-001',view)

    def test_verify_uses_effective_state_and_latest_result_not_only_passed_prose(self):
        doc=load_plan(self.folder);stamp,head=context(self.root,self.folder,doc);row=doc['items'][0]
        record(self.root,self.folder,row['id'],'passed',stamp,head,'Partial fixture observation','Only one fixture input inspected')
        record(self.root,self.folder,row['id'],'unavailable',stamp,head,'Full expected outcome not observed','Scope mismatch preserved')
        view=capture(self.root,'FEAT-001','verify',item_ids=[row['id']])
        result=next(r for r in view['claims'] if r['id']==row['id'])
        self.assertEqual(result['effective_state'],'unavailable');self.assertEqual(result['latest_result']['actual'],'Full expected outcome not observed')
        self.assertEqual(result['history_entries'],2);self.assertIn('/history',result['history_ref'])
        self.assertNotIn('Only one fixture input inspected',json.dumps(view))

    def test_missing_uncertain_scope_and_no_projection_scope_do_not_hide_information(self):
        view=capture(self.root,'FEAT-001','verify');self.assertEqual(len(view['requirements']),2)
        (self.folder/'verification.json').unlink()
        view=capture(self.root,'FEAT-001','test',['T-FOCUS'])
        self.assertIn('verification_plan_missing; return to ordinary Verify preparation',view['global_attention'])
        self.assertEqual(view['claims'],[])
        with self.assertRaisesRegex(ValueError,'unknown task'):capture(self.root,'FEAT-001','test',['T-NONE'])

    def test_shared_preservation_expands_linked_requirement_instead_of_trimming_it(self):
        impact=json.loads((self.folder/'impact.json').read_text());impact['behaviors'][1]['requirement_ids']=['R-OTHER']
        (self.folder/'impact.json').write_text(json.dumps(impact));sync(self.root,self.folder)
        view=capture(self.root,'FEAT-001','test',['T-FOCUS'])
        self.assertEqual({r['id'] for r in view['requirements']},{'R-1','R-OTHER'})
        self.assertEqual(view['omitted_requirements'],[])

    def test_cli_output_can_be_checked_without_mutating_canonical_records(self):
        script=Path(__file__).parents[1]/'skills/dev/core/scripts/stage_view.py';snapshot=self.root/'.agent-workflow/view.json'
        before=(self.folder/'verification.json').read_bytes()
        result=subprocess.run([sys.executable,str(script),'capture',str(self.root),'FEAT-001','--stage','test','--task','T-FOCUS'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);snapshot.write_text(result.stdout)
        # Disposable outputs must be in ignored scratch: this fixture intentionally leaves its output untracked.
        snapshot.unlink();folder=self.root/'.agent-workflow/scratch';folder.mkdir(exist_ok=True)
        (self.root/'.agent-workflow/.gitignore').write_text('/scratch/\n');snapshot=folder/'view.json'
        result=subprocess.run([sys.executable,str(script),'capture',str(self.root),'FEAT-001','--stage','test','--task','T-FOCUS'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);snapshot.write_text(result.stdout)
        result=subprocess.run([sys.executable,str(script),'check',str(self.root),'FEAT-001','--snapshot',str(snapshot)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('STAGE_VIEW_CURRENT',result.stdout)
        self.assertEqual(before,(self.folder/'verification.json').read_bytes())

    def test_unrelated_failed_claim_is_globally_visible_without_loading_its_history(self):
        doc=load_plan(self.folder);stamp,head=context(self.root,self.folder,doc)
        row=next(r for r in doc['items'] if r['source'].startswith('requirement:R-OTHER:'))
        record(self.root,self.folder,row['id'],'failed',stamp,head,'Wrong unrelated result','Synthetic execution failure')
        view=capture(self.root,'FEAT-001','test',['T-FOCUS'])
        self.assertNotIn(row['id'],{r['id'] for r in view['claims']})
        self.assertIn('unresolved_acceptance: '+row['id']+': failed',view['global_attention'])
        self.assertEqual(next(r for r in view['global_claim_states'] if r['id']==row['id'])['effective_state'],'failed')

    def test_cross_requirement_decision_expands_its_full_parent_authority(self):
        path=self.folder/'decisions.json';doc=json.loads(path.read_text())
        doc['decisions'].append({'id':'D-CROSS','status':'approved','requirement_ids':['R-1','R-OTHER'],'question':'Shared conditional rule'})
        path.write_text(json.dumps(doc))
        view=capture(self.root,'FEAT-001','verify',['T-FOCUS'])
        self.assertEqual({r['id'] for r in view['requirements']},{'R-1','R-OTHER'})
