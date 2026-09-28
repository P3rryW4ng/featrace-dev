"""Create a synthetic project and a temporary Skill install for independent review.

Writes only under a newly created temporary directory, never to personal installs.
The printed paths are sufficient for dispatch; keep the oracle in the review report.
"""
import json, subprocess, tempfile, sys
from pathlib import Path
base=Path(tempfile.mkdtemp(prefix='featrace-verify-0523-'))
root=base/'project';root.mkdir()
skill_repo=Path(__file__).resolve().parents[3]
subprocess.run([sys.executable,str(skill_repo/'scripts/install.py'),'--agent','claude','--home',str(base/'home')],check=True)
skill=base/'home/.claude/skills/dev'
feature=root/'.agent-workflow/features/DEMO-PREVIEW'
(feature/'spec').mkdir(parents=True);(feature/'sources').mkdir()
(root/'src').mkdir();(root/'tests').mkdir()
(root/'.gitignore').write_text('.agent-workflow/project-baseline/\n.agent-workflow/features/*/sources/\n__pycache__/\n')
(root/'src/formatting.py').write_text('DISPLAY_LIMIT = 12\n\ndef preview(value):\n    return value[:DISPLAY_LIMIT]\n')
(root/'src/receipt.py').write_text('from src.formatting import DISPLAY_LIMIT\n\ndef receipt_reference(value):\n    return value[:DISPLAY_LIMIT]\n')
(root/'tests/test_preview.py').write_text('import unittest\nfrom src.formatting import preview\n\nclass PreviewTests(unittest.TestCase):\n    def test_short_input(self):\n        self.assertEqual(preview("abc"), "abc")\n')
(feature/'sources/prd.txt').write_text('Preview labels must display at most eight characters. Receipt reference formatting must remain unchanged.\n')
def write(path,obj):path.write_text(json.dumps(obj,indent=2)+'\n')
write(feature/'spec/requirements.json',{'feature':{'id':'DEMO-PREVIEW','title':'Shorter preview labels','status':'provisional','prd_paths':['sources/prd.txt','sources/layout.png'],'source_status':{'prd':'present','figma':'missing','api':'not_applicable'}},'requirements':[{'id':'R-1','statement':'Limit preview labels to eight characters; preserve existing receipt formatting','status':'confirmed','acceptance_criteria':['Preview shows at most 8 characters','Receipt references retain existing behavior']} ]})
write(feature/'spec/prd-intake.json',{'feature_id':'DEMO-PREVIEW','sources':[{'id':'S1','kind':'document','path':'sources/prd.txt'},{'id':'S2','kind':'image','path':'sources/layout.png'}]})
write(feature/'tasks.json',{'feature_id':'DEMO-PREVIEW','tasks':[{'id':'T-1','title':'Shorten preview label','requirement_ids':['R-1'],'status':'done'}]})
write(feature/'traceability.json',{'feature_id':'DEMO-PREVIEW','links':[{'requirement_id':'R-1','tasks':['T-1'],'code':['src/formatting.py'],'tests':['TEST-PREVIEW']}]})
write(feature/'decisions.json',{'feature_id':'DEMO-PREVIEW','decisions':[]})
def git(*a):return subprocess.check_output(['git','-C',str(root),*a],text=True).strip()
git('init','-q');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid');git('add','.');git('commit','-qm','baseline')
revision=git('rev-parse','HEAD')
(root/'src/formatting.py').write_text((root/'src/formatting.py').read_text().replace('12','8'))
git('add','.');git('commit','-qm','shorten preview labels')
q=root/'.agent-workflow/project-baseline';q.mkdir()
write(q/'quality-report.json',{'tested_at':'synthetic fixture; not a real measured run','project_snapshot':{'git_head':git('rev-parse','HEAD')},'results':[{'name':'compile','status':'passed','note':'synthetic fixture claim'}]})
output=subprocess.check_output([sys.executable,str(skill/'core/scripts/verify-handoff.py'),'capture',str(root),'DEMO-PREVIEW','--base',revision])
(base/'snapshot.json').write_bytes(output)
print(json.dumps({'pilot':str(base),'project':str(root),'skill':str(skill),'snapshot':str(base/'snapshot.json'),'result':str(base/'result.json')}))
