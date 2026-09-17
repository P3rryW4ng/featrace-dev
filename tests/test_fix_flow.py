import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from intake_helpers import attach_intake, CORE

class FixFlowTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.folder=self.root/'.agent-workflow/features/FEAT-001'
        (self.folder/'sources').mkdir(parents=True)
        (self.folder/'spec').mkdir()
        (self.folder/'sources/prd-original.txt').write_text('Uppercase the supplied text.')
        self.req={'feature':{'id':'FEAT-001','status':'provisional','source_status':{'prd':'present','api':'not_applicable','figma':'not_applicable'},'source_notes':{'api':'local computation','figma':'no UI'}},
                  'requirements':[{'id':'R-1','title':'Uppercase','statement':'Return uppercase text','status':'confirmed','sources':[{'type':'prd','ref':'sources/prd-original.txt'}],'acceptance_criteria':['abc becomes ABC'],'tasks':['T-1'],'tests':['UT-1'],'assumptions':[]}]}
        self.write('spec/requirements.json',self.req)
        self.write('tasks.json',{'feature_id':'FEAT-001','tasks':[{'id':'T-1','title':'Implement','status':'done','requirement_ids':['R-1'],'test_evidence':['UT-1 passed in fixture']}]})
        self.write('decisions.json',{'feature_id':'FEAT-001','decisions':[]})
        self.write('traceability.json',{'feature_id':'FEAT-001','links':[{'requirement_id':'R-1','task_id':'T-1','code':['convert.py'],'tests':['UT-1']}]})
        attach_intake(self.folder,self.req)
    def write(self,name,data):
        (self.folder/name).write_text(json.dumps(data))
    def run_script(self,name,*args,expected=0):
        proc=subprocess.run([sys.executable,str(CORE/name),*map(str,args)],capture_output=True,text=True)
        self.assertEqual(proc.returncode,expected,proc.stdout+proc.stderr)
        return proc.stdout
    def record(self,description='Output is lowercase'):
        return self.run_script('record-fix.py',self.root,'FEAT-001',description)
    def fix(self):
        return json.loads((self.folder/'fixes.json').read_text())
    def save_fix(self,item):
        self.write('fixes.json',{'feature_id':'FEAT-001','fixes':[item]})
    def resolved(self,kind='implementation_defect'):
        self.record(); item=self.fix()['fixes'][0]
        item.update(status='verified',kind=kind,expected='ABC',actual='abc',reproduction='input abc',
                    root_cause='lowercase transform used',resolution='use uppercase transform',
                    requirement_ids=['R-1'],task_ids=['T-1'],evidence=['input abc produced abc'],verification=['UT-1: abc -> ABC passed'],regression_test_ids=['UT-1'],tested_revision='fixture-revision-1')
        self.save_fix(item)
        return item
    def test_register_from_description_and_render(self):
        old_req=(self.folder/'spec/requirements.json').read_bytes()
        self.assertIn('FIX_RECORDED: FIX-001',self.record())
        self.assertIn('FIX_ALREADY_RECORDED',self.record())
        item=self.fix()['fixes'][0]
        self.assertEqual((item['status'],item['kind']),('reported','unclassified'))
        self.assertFalse(item['expected']);self.assertFalse(item['actual'])
        self.assertEqual(old_req,(self.folder/'spec/requirements.json').read_bytes())
        self.assertIn('Output is lowercase',(self.folder/'fixes.md').read_text())
        self.run_script('validate-feature.py','--stage','develop',self.root,'FEAT-001')
        self.run_script('validate-feature.py','--stage','check',self.root,'FEAT-001',expected=1)
        self.assertIn('unresolved=1/1',self.run_script('feature-status.py',self.root,'FEAT-001'))
    def test_code_bug_verified_without_prd_change(self):
        old_req=(self.folder/'spec/requirements.json').read_bytes()
        self.resolved()
        self.run_script('validate-feature.py','--stage','check',self.root,'FEAT-001')
        self.run_script('render-workspace.py',self.root,'FEAT-001')
        self.assertIn('UT-1: abc -> ABC passed',(self.folder/'fixes.md').read_text())
        self.assertEqual(old_req,(self.folder/'spec/requirements.json').read_bytes())
    def test_verification_and_links_required(self):
        item=self.resolved();item['verification']=[];item['requirement_ids']=['R-missing'];self.save_fix(item)
        output=self.run_script('validate-feature.py','--stage','check',self.root,'FEAT-001',expected=1)
        self.assertIn('verification evidence required',output)
        self.assertIn('invalid requirement_ids',output)
    def test_requirement_change_needs_approved_decision_and_reference(self):
        item=self.resolved('requirement_change');item['source_refs']=['new request dated 2026-09-17'];self.save_fix(item)
        output=self.run_script('validate-feature.py','--stage','check',self.root,'FEAT-001',expected=1)
        self.assertIn('approved decision',output)
        self.write('decisions.json',{'feature_id':'FEAT-001','decisions':[{'id':'D-1','status':'approved','chosen':'new behavior'}]})
        item['decision_ids']=['D-1'];item['approval_ref']='product confirmation in D-1';self.save_fix(item)
        self.run_script('validate-feature.py','--stage','check',self.root,'FEAT-001')
    def test_navigation_can_have_task_gap_and_code_defect(self):
        from fixes import validate_fixes
        item={'id':'FIX-007','description':'Back reopens current page',
              'status':'verified','kind':'task_description_gap',
              'contributing_kinds':['implementation_defect'],
              'expected':'Back returns to the previous page',
              'actual':'Current page closes and opens again',
              'reproduction':'Open A, open B, tap Back',
              'root_cause':'task omitted back behavior and navigation code reopens B',
              'resolution':'clarify T-NAV and fix back-stack navigation',
              'evidence':['observed A → B → Back → B'],
              'requirement_ids':['R-NAV'],'task_ids':['T-NAV'],
              'decision_ids':['D-BACK'],
              'task_changes':[{'task_id':'T-NAV','before':'implement B page','after':'implement B page; Back returns to A'}],
              'verification':['UI-BACK passed on fixture'],
              'regression_test_ids':['UI-BACK'],
              'tested_revision':'fixture-revision-2'}
        requirements=[{'id':'R-NAV','tests':['UI-BACK']}]
        tasks=[{'id':'T-NAV'}]
        decisions=[{'id':'D-BACK','status':'approved','chosen':'return to previous page'}]
        self.save_fix(item)
        errors,_=validate_fixes(self.folder,'FEAT-001',requirements,tasks,decisions,'check')
        self.assertEqual(errors,[])
        item['task_changes']=[];self.save_fix(item)
        errors,_=validate_fixes(self.folder,'FEAT-001',requirements,tasks,decisions,'check')
        self.assertTrue(any('task description gap needs' in e for e in errors))
        item['task_changes']=[{'task_id':'T-NAV','before':'implement B page','after':'Back returns to A'}]
        item['regression_test_ids']=[];self.save_fix(item)
        errors,_=validate_fixes(self.folder,'FEAT-001',requirements,tasks,decisions,'check')
        self.assertTrue(any('regression test or explicit waiver' in e for e in errors))

    def test_regression_test_must_be_declared_or_waived(self):
        item=self.resolved()
        item['regression_test_ids']=['UNKNOWN-TEST']
        self.save_fix(item)
        output=self.run_script('validate-feature.py','--stage','check',self.root,'FEAT-001',expected=1)
        self.assertIn('regression_test_ids must name declared requirement tests',output)
        item['regression_test_ids']=[]
        item['regression_waiver']='UI test harness unavailable; manual A to B to Back check performed'
        self.save_fix(item)
        self.run_script('validate-feature.py','--stage','check',self.root,'FEAT-001')

    def test_legacy_without_fixes_remains_valid(self):
        self.run_script('validate-feature.py','--stage','check',self.root,'FEAT-001')
        self.run_script('render-workspace.py',self.root,'FEAT-001')
        self.assertTrue((self.folder/'fixes.md').exists())
    def test_invalid_record_rejected(self):
        self.write('fixes.json',{'feature_id':'FEAT-001','fixes':[{'id':'FIX-001','description':'bad','status':'verified','kind':'requirement_change','decision_ids':None}]})
        self.run_script('validate-feature.py','--stage','check',self.root,'FEAT-001',expected=1)
    def test_completed_feature_reopens_on_report(self):
        self.req['feature']['status']='complete'
        self.write('spec/requirements.json',self.req)
        self.record()
        req=json.loads((self.folder/'spec/requirements.json').read_text())
        self.assertEqual(req['feature']['status'],'provisional')
        self.assertEqual(self.fix()['fixes'][0]['previous_feature_status'],'complete')

    def test_recurrence_creates_new_id(self):
        item=self.resolved();self.assertEqual(item['id'],'FIX-001')
        self.assertIn('FIX_RECORDED: FIX-002',self.record())
if __name__=='__main__': unittest.main()
