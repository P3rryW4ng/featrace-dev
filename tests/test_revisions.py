import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
import test_fix_flow
from intake_helpers import attach_intake
from revisions import inspect, semantics, digest
from prd_intake import review_digest


class RevisionTests(unittest.TestCase):
    write = test_fix_flow.FixFlowTests.write
    run_script = test_fix_flow.FixFlowTests.run_script

    def setUp(self):
        test_fix_flow.FixFlowTests.setUp(self)
        self.req['feature'].update(title='Uppercase', status='complete')
        self.write('spec/requirements.json', self.req)
        self.write('decisions.json', {'feature_id':'FEAT-001','decisions':[{'id':'D-001','status':'approved','chosen':'Preserve spacing in uppercase output'}]})
        (self.folder/'delivery-report.md').write_text('Synthetic acceptance; UT-1 passed; manual inspection completed.')
        subprocess.run(['git','init',str(self.root)], capture_output=True,check=True)
        (self.root/'README.md').write_text('Synthetic project')
        subprocess.run(['git','-C',str(self.root),'add','README.md'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(self.root),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','fixture'],check=True,capture_output=True)
        self.head=subprocess.check_output(['git','-C',str(self.root),'rev-parse','HEAD'],text=True).strip()
        self.cmd('init', '--reason','Original requirements reviewed and confirmed')

    def cmd(self, action, *args, expected=0):
        return self.run_script('revise.py',action,self.root,'FEAT-001',*args,expected=expected)

    def doc(self):
        return json.loads((self.folder/'spec/requirements.json').read_text())

    def proposal(self):
        b=self.doc()['feature']['baseline']
        return {'base_version':b['version'],'base_digest':b['digest'],'kind':'clarification',
                'reason':'Clarify whitespace handling','decision_ids':['D-001'],
                'evidence':['D-001 chosen value'],'impact_review':'Update conversion and UT-1; no navigation changes',
                'preserved_behavior':'Existing uppercase conversion stays unchanged',
                'task_ids':['T-1'],'code_paths':['convert.py'],'test_ids':['UT-1'],
                'changes':[{'requirement_id':'R-1','field':'statement','before':self.doc()['requirements'][0]['statement'],
                            'after':'Return uppercase text and preserve spacing'}]}

    def propose(self, data=None, *args, expected=0):
        file=self.root/'proposal.json';file.write_text(json.dumps(data or self.proposal()))
        return self.cmd('propose','--input',file,*args,expected=expected)

    def apply(self):
        self.propose()
        self.cmd('apply','--revision','CHG-001')

    def review(self):
        attach_intake(self.folder,self.doc())

    def gates(self, ids=None, bind=True):
        base=self.root/'.agent-workflow/project-baseline';base.mkdir(exist_ok=True)
        (base/'quality-gates.json').write_text(json.dumps({'gates':[{'name':'uppercase','command':[sys.executable,'-c','assert "ab c".upper() == "AB C"'],'test_ids':ids or ['UT-1']}]}))
        self.run_script('project.py','check',self.root,*(['--feature','FEAT-001'] if bind else []))

    def test_init_preserves_original_meaning_and_no_fake_delivery(self):
        d=self.doc();b=d['feature']['baseline']
        self.assertEqual(b['version'],1)
        self.assertEqual(b['initial_requirements'],semantics(self.req['requirements']))
        self.assertEqual(b['deliveries'],[])
        self.assertEqual(d['feature']['status'],'provisional')
        self.assertIn('ALREADY_REGISTERED',self.cmd('init'))

    def test_propose_preserves_baseline_and_duplicate_does_not_create(self):
        original=(self.folder/'spec/requirements.json').read_bytes()
        self.propose()
        self.assertEqual(original,(self.folder/'spec/requirements.json').read_bytes())
        self.assertIn('ALREADY_RECORDED',self.propose())
        self.assertEqual(len(list((self.folder/'revisions').glob('CHG-*.json'))),1)
        self.run_script('validate-feature.py','--stage','develop',self.root,'FEAT-001',expected=1)
        self.run_script('validate-feature.py','--stage','check',self.root,'FEAT-001',expected=1)
        self.assertEqual(json.loads(self.cmd('status'))['pending'],['CHG-001'])

    def test_pending_confirmation_cannot_apply(self):
        self.propose()
        self.write('decisions.json',{'feature_id':'FEAT-001','decisions':[{'id':'D-001','status':'pending'}]})
        before=(self.folder/'spec/requirements.json').read_bytes()
        self.cmd('apply','--revision','CHG-001',expected=1)
        self.assertEqual(before,(self.folder/'spec/requirements.json').read_bytes())

    def test_apply_updates_only_target_and_marks_unverified(self):
        self.apply();d=self.doc()
        self.assertEqual(d['requirements'][0]['statement'],'Return uppercase text and preserve spacing')
        self.assertEqual(d['requirements'][0]['acceptance_criteria'],self.req['requirements'][0]['acceptance_criteria'])
        self.assertEqual(d['feature']['baseline']['version'],2)
        self.assertEqual(json.loads(self.cmd('status'))['verified_version'],0)
        self.assertEqual(d['feature']['status'],'provisional')
        self.run_script('validate-feature.py','--stage','develop',self.root,'FEAT-001',expected=1) # stale semantic PRD review
        self.review()
        self.run_script('validate-feature.py','--stage','develop',self.root,'FEAT-001')
        self.propose(expected=1) # another implementation must wait for this delivery

    def test_stale_version_or_before_rejected_without_changes(self):
        for field in ('base_version','base_digest','before'):
            proposal=self.proposal()
            if field=='before':proposal['changes'][0]['before']='wrong'
            else:proposal[field]=9 if field=='base_version' else 'stale'
            self.propose(proposal,expected=1)
        self.assertFalse((self.folder/'revisions').exists())

    def test_cancel_preserves_baseline_and_history(self):
        self.propose();self.cmd('cancel','--revision','CHG-001','--reason','Product withdrew proposal')
        d=self.doc();self.assertEqual(d['feature']['baseline']['version'],1)
        self.assertEqual(d['requirements'],self.req['requirements'])
        self.assertEqual(len(d['feature']['baseline']['cancelled']),1)
        self.assertTrue((self.folder/'revisions/CHG-001.json').exists())
        self.run_script('validate-feature.py','--stage','develop',self.root,'FEAT-001')

    def test_direct_semantic_drift_and_applied_record_tamper_detected(self):
        d=self.doc();d['requirements'][0]['statement']='Different rule';self.write('spec/requirements.json',d)
        self.cmd('status',expected=1)
        d['requirements'][0]['statement']=self.req['requirements'][0]['statement'];self.write('spec/requirements.json',d)
        self.apply()
        path=self.folder/'revisions/CHG-001.json';record=json.loads(path.read_text());record['reason']='Changed history';path.write_text(json.dumps(record))
        self.cmd('status',expected=1)

    def test_task_links_and_workflow_progress_do_not_change_semantic_version(self):
        d=self.doc();d['requirements'][0]['tasks']=['T-2'];d['feature']['status']='drafted'
        self.write('spec/requirements.json',d)
        self.assertEqual(json.loads(self.cmd('status'))['baseline_version'],1)

    def test_sources_preserved_and_modified_source_blocks_apply(self):
        src=self.root/'update.html';src.write_text('<p>Preserve spacing</p>')
        original=(self.folder/'sources/prd-original.txt').read_bytes()
        self.propose(None,'--source',src)
        record=json.loads((self.folder/'revisions/CHG-001.json').read_text())
        copied=self.folder/record['source_files'][0]['path']
        self.assertEqual(copied.read_bytes(),src.read_bytes())
        self.assertEqual(original,(self.folder/'sources/prd-original.txt').read_bytes())
        copied.write_text('tampered')
        self.cmd('apply','--revision','CHG-001',expected=1)

    def test_old_or_unbound_checks_cannot_verify_new_baseline(self):
        self.gates();self.apply();self.review()
        self.cmd('verify','--code-revision',self.head,expected=1)
        self.gates(bind=False)
        self.cmd('verify','--code-revision',self.head,expected=1)
        self.assertFalse(self.doc()['feature']['baseline']['deliveries'])

    def test_verify_records_version_code_and_evidence_without_auto_complete(self):
        self.apply();self.review();self.gates()
        self.cmd('verify','--code-revision',self.head)
        d=self.doc();delivery=d['feature']['baseline']['deliveries'][0]
        self.assertEqual(delivery['version'],2);self.assertEqual(delivery['code_revision'],self.head)
        self.assertEqual(d['feature']['status'],'provisional')
        d['feature']['status']='complete';self.write('spec/requirements.json',d)
        self.run_script('validate-feature.py','--stage','check',self.root,'FEAT-001')
        self.run_script('render-workspace.py',self.root,'FEAT-001')
        self.assertIn('applied v2',(self.folder/'revisions.md').read_text())
        self.assertIn('confirmed=2, verified=2',self.run_script('feature-status.py',self.root,'FEAT-001'))

    def test_false_complete_unselected_tests_and_wrong_revision_rejected(self):
        self.apply();self.review();d=self.doc();d['feature']['status']='complete';self.write('spec/requirements.json',d)
        self.run_script('validate-feature.py','--stage','check',self.root,'FEAT-001',expected=1)
        d['feature']['status']='provisional';self.write('spec/requirements.json',d)
        self.gates(ids=['UT-OTHER'])
        self.cmd('verify','--code-revision',self.head,expected=1)
        self.gates()
        self.cmd('verify','--code-revision','not-a-commit',expected=1)

    def test_new_requirement_and_retirement_are_explicit(self):
        proposal=self.proposal();added=copy.deepcopy(self.req['requirements'][0]);added.update(id='R-2',title='Additional rule')
        proposal['changes']=[{'requirement_id':'R-2','field':'$requirement','before':None,'after':added},
                             {'requirement_id':'R-1','field':'status','before':'confirmed','after':'deprecated'}]
        self.propose(proposal);self.cmd('apply','--revision','CHG-001')
        self.assertEqual([x['status'] for x in self.doc()['requirements']],['deprecated','confirmed'])
        self.cmd('status')

    def test_code_bug_does_not_revise_requirements(self):
        before=self.doc()['feature']['baseline']
        self.run_script('record-fix.py',self.root,'FEAT-001','Implementation produces lowercase')
        self.assertEqual(self.doc()['feature']['baseline'],before)
        self.assertEqual(json.loads(self.cmd('status'))['pending'],[])

    def test_original_aspect_is_preserved_with_explicit_supersession(self):
        self.apply()
        req=self.doc()
        intake=json.loads((self.folder/'spec/prd-intake.json').read_text())
        old=intake['items'][0]['aspects'][0]
        original=dict(old)
        old.update(superseded_by='CHG-001', supersession_reason='Approved D-001 expands spacing behavior')
        intake['units'].append({'id':'U-2','source':'revisions/CHG-001.json','locator':'changes[0].after','kind':'text','status':'read'})
        target=req['requirements'][0]['statement']
        intake['items'].append({'id':'S-2','unit_id':'U-2','quote':target,'context':'Confirmed revision D-001',
            'related_ids':['S-1'],'kind':'rule','disposition':'mapped','aspects':[{'kind':'behavior','text':target,
                'requirement_id':'R-1','field':'statement','target_text':target,'review':'verified'}]})
        req['requirements'][0]['source_item_ids']=['S-1','S-2']
        self.write('spec/requirements.json',req)
        intake['review']['digest']=review_digest(self.folder,intake,req)
        self.write('spec/prd-intake.json',intake)
        self.run_script('validate-feature.py','--stage','develop',self.root,'FEAT-001')
        self.assertEqual(old['target_text'],original['target_text'])
        self.assertEqual(intake['items'][0]['quote'],'Uppercase the supplied text.')
        old['superseded_by']='CHG-999'
        self.write('spec/prd-intake.json',intake)
        self.run_script('validate-feature.py','--stage','develop',self.root,'FEAT-001',expected=1)

    def test_check_detects_requirement_drift_during_execution(self):
        self.gates()
        base=self.root/'.agent-workflow/project-baseline'
        code="import json;from pathlib import Path;p=Path('.agent-workflow/features/FEAT-001/spec/requirements.json');d=json.loads(p.read_text());d['requirements'][0]['statement']='unreviewed edit';p.write_text(json.dumps(d))"
        (base/'quality-gates.json').write_text(json.dumps({'gates':[{'name':'mutates-baseline','command':[sys.executable,'-c',code],'test_ids':['UT-1']}]}))
        self.run_script('project.py','check',self.root,'--feature','FEAT-001',expected=2)
        self.run_script('audit-delivery.py',self.root,'FEAT-001',expected=1)
