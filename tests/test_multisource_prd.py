import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from intake_helpers import CORE
from prd_intake import validate_intake

class MultiSourceTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)/'project';self.root.mkdir()
        self.doc=Path(tmp.name)/'rules.md';self.doc.write_text('Submit creates an order.')
        self.html=Path(tmp.name)/'prototype.html';self.html.write_text('<button>Submit</button>')
        self.feature=self.root/'.agent-workflow/features/F-1'
    def init(self,*paths):
        run=subprocess.run([sys.executable,str(CORE/'init-feature.py'),'F-1',str(paths[0]),str(self.root),*[arg for p in paths[1:] for arg in ('--source',str(p))]],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        return json.loads((self.feature/'spec/prd-intake.json').read_text())
    def validate(self,intake):
        (self.feature/'spec/prd-intake.json').write_text(json.dumps(intake))
        req=json.loads((self.feature/'spec/requirements.json').read_text())
        return validate_intake(self.feature,req,'develop',require_review=False)[0]
    def test_document_only_and_html_only(self):
        intake=self.init(self.doc)
        self.assertEqual([s['kind'] for s in intake['sources']],['document'])
        self.assertTrue((self.feature/intake['sources'][0]['path']).is_file())
        with tempfile.TemporaryDirectory() as temp:
            other=Path(temp)
            run=subprocess.run([sys.executable,str(CORE/'init-feature.py'),'H-1',str(self.html),str(other)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            reg=json.loads((other/'.agent-workflow/features/H-1/spec/prd-intake.json').read_text())
            self.assertEqual(reg['sources'][0]['kind'],'html')
    def test_both_sources_and_uncovered_source_blocks(self):
        intake=self.init(self.doc,self.html)
        self.assertEqual([s['kind'] for s in intake['sources']],['document','html'])
        intake['inventory_complete']=True
        intake['units']=[{'id':'U-1','source':intake['sources'][0]['path'],'locator':'p1','kind':'text','status':'read'}]
        errors=self.validate(intake)
        self.assertTrue(any('source has no reading unit' in e for e in errors))
        self.assertTrue(any('HTML has no interaction inventory' in e for e in errors))
    def test_interaction_requires_observed_transition(self):
        intake=self.init(self.html)
        source=intake['sources'][0]['path'];intake['inventory_complete']=True
        intake['units']=[{'id':'U-1','source':source,'locator':'submit button','kind':'interaction','status':'read'}]
        self.assertTrue(any('observed interaction' in e for e in self.validate(intake)))
        intake['units'][0].update(trigger='click Submit',before='form filled',after='success toast',observation='browser session on local HTML')
        self.assertFalse(any('observed interaction' in e for e in self.validate(intake)))
    def test_static_html_needs_scoped_rationale(self):
        intake=self.init(self.html);source=intake['sources'][0]['path']
        intake['inventory_complete']=True
        intake['units']=[{'id':'U-1','source':source,'locator':'static page','kind':'text','status':'read'}]
        self.assertTrue(any('HTML has no interaction inventory' in e for e in self.validate(intake)))
        intake['sources'][0]['interaction_scope']='static informational mock; no controls available'
        self.assertFalse(any('HTML has no interaction inventory' in e for e in self.validate(intake)))

    def test_declared_paths_cannot_silently_drop_source(self):
        intake=self.init(self.doc,self.html)
        intake['sources'].pop()
        self.assertTrue(any('prd_paths' in e for e in self.validate(intake)))

    def test_source_bytes_and_registration_change_review_digest(self):
        from prd_intake import review_digest
        intake=self.init(self.doc,self.html)
        req=json.loads((self.feature/'spec/requirements.json').read_text())
        old=review_digest(self.feature,intake,req)
        (self.feature/intake['sources'][1]['path']).write_text('<button>Cancel</button>')
        self.assertNotEqual(old,review_digest(self.feature,intake,req))
        intake['sources'].pop()
        self.assertNotEqual(old,review_digest(self.feature,intake,req))
    def test_combined_evidence_review_and_conflict_gate(self):
        intake=self.init(self.doc,self.html)
        document, html=(row['path'] for row in intake['sources'])
        target='Submitting a filled form creates an order and shows confirmation'
        req={'feature':{'id':'F-1','title':'Order','status':'provisional','source_status':{'prd':'present','api':'not_applicable','figma':'not_applicable'},'source_notes':{'api':'local fixture','figma':'HTML source supplies interaction'},'prd_path':document,'prd_paths':[document,html]},
             'requirements':[{'id':'R-1','title':'Submit','status':'confirmed','statement':target,'source_item_ids':['S-1','S-2'],'sources':[{'type':'prd','ref':document},{'type':'prd','ref':html}],'acceptance_criteria':['Confirmation visible after submit'],'tasks':['T-1'],'tests':['UT-1'],'assumptions':[]}]}
        (self.feature/'spec/requirements.json').write_text(json.dumps(req))
        (self.feature/'tasks.json').write_text(json.dumps({'feature_id':'F-1','tasks':[{'id':'T-1','title':'Implement submit','status':'planned','requirement_ids':['R-1']}]}))
        intake['inventory_complete']=True
        intake['units']=[{'id':'U-1','source':document,'locator':'paragraph 1','kind':'text','status':'read'},
                         {'id':'U-2','source':html,'locator':'button Submit','kind':'interaction','status':'read','trigger':'click Submit','before':'filled form','after':'confirmation shown','observation':'observed in fixture browser'}]
        intake['items']=[{'id':sid,'unit_id':uid,'quote':quote,'context':'Order submission flow','related_ids':['S-2' if sid=='S-1' else 'S-1'],'kind':'rule','disposition':'mapped','aspects':[{'kind':'behavior','text':quote,'requirement_id':'R-1','field':'statement','target_text':target,'review':'verified'}]}
                         for sid,uid,quote in [('S-1','U-1','Submit creates an order'),('S-2','U-2','Confirmation shown after click')]]
        self.assertEqual(self.validate(intake),[])
        review=subprocess.run([sys.executable,str(CORE/'review-prd.py'),str(self.root),'F-1','--reviewer','fixture','--notes','Checked both synthetic sources'],capture_output=True,text=True)
        self.assertEqual(review.returncode,0,review.stdout+review.stderr)
        valid=subprocess.run([sys.executable,str(CORE/'validate-feature.py'),'--stage','develop',str(self.root),'F-1'],capture_output=True,text=True)
        self.assertEqual(valid.returncode,0,valid.stdout+valid.stderr)
        decisions=self.feature/'decisions.json'
        decisions.write_text(json.dumps({'feature_id':'F-1','decisions':[{'id':'D-1','status':'pending','sources':[document,html]}]}))
        conflict=subprocess.run([sys.executable,str(CORE/'validate-feature.py'),'--stage','develop',str(self.root),'F-1'],capture_output=True,text=True)
        self.assertNotEqual(conflict.returncode,0)
        self.assertIn('unresolved decision',conflict.stdout)

    def test_duplicate_and_missing_input_leave_no_workspace(self):
        for second in (self.doc,Path(self.doc.parent/'missing.md')):
            run=subprocess.run([sys.executable,str(CORE/'init-feature.py'),'F-1',str(self.doc),str(self.root),'--source',str(second)],capture_output=True,text=True)
            self.assertNotEqual(run.returncode,0)
            self.assertFalse(self.feature.exists())
if __name__=='__main__':unittest.main()
