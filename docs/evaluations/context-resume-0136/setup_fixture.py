from pathlib import Path
import copy,json,shutil,sys,tempfile,hashlib
repo=Path(__file__).resolve().parents[3];sys.path.insert(0,str(repo/'tests'))
from test_stage_view import StageViewTests
from stage_view import capture
from verification import load_plan,context,record
home=Path(tempfile.mkdtemp(prefix='featrace-context-0136-'))
f=StageViewTests();f.setUp()
try:
 for label in ('alpha','beta'):
  root=home/label;shutil.copytree(f.root,root)
  folder=root/'.agent-workflow/features/FEAT-001'
  (root/'.agent-workflow/.gitignore').write_text('/scratch/\n')
  scratch=root/'.agent-workflow/scratch/resume';scratch.mkdir(parents=True)
  doc=load_plan(folder);stamp,head=context(root,folder,doc);row=doc['items'][0]
  record(root,folder,row['id'],'passed',stamp,head,'Earlier fixture claimed uppercase result','Earlier fixture assertion summary only')
  record(root,folder,row['id'],'unavailable',stamp,head,'Original expectation not fully exercised','Actual check asserts arithmetic only; conversion execution absent')
  # Add realistic obsolete report; it cannot supersede canonical results.
  (folder/'delivery-report.md').write_text('# Earlier report\nAll checks passed. Ready for delivery.\n')
  view=capture(root,'FEAT-001','verify',['T-FOCUS'])
  (scratch/'starting-view.json').write_text(json.dumps(view,ensure_ascii=False,indent=2))
  if label=='beta':
   p=folder/'decisions.json';d=json.loads(p.read_text());d['decisions'][2]['question']='Current product choice now also affects the focus task';d['decisions'][2]['requirement_ids']=['R-1'];p.write_text(json.dumps(d))
  (scratch/'result').mkdir()
 def inventory(root):
  return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and '.git' not in p.parts and '.agent-workflow/scratch' not in p.as_posix() and '__pycache__' not in p.parts}
 before={label:inventory(home/label) for label in ('alpha','beta')}
 (home/'before.json').write_text(json.dumps(before,indent=2))
 # Reproducible byte accounting; deliberately synthetic and not token/cost data.
 root=home/'alpha';folder=root/'.agent-workflow/features/FEAT-001'
 small=capture(root,'FEAT-001','verify',['T-FOCUS'])
 original=(folder/'verification.json').read_bytes();doc=json.loads(original)
 for i in range(120):
  e=copy.deepcopy(doc['items'][0]['history'][-1]);e['at']='synthetic-old-attempt-'+str(i);e['evidence']='Old synthetic attempt '+str(i)+' '+('history '*500)
  doc['items'][0]['history'].insert(0,e)
 (folder/'verification.json').write_text(json.dumps(doc))
 large=capture(root,'FEAT-001','verify',['T-FOCUS'])
 (folder/'verification.json').write_bytes(original)
 files=['SKILL.md','core/references/orchestration.md','core/references/workflow.md','core/references/technical-test.md','core/references/verification-workflow.md','core/references/stage-inputs.md']
 metrics={'reference_files':[{'file':p,'bytes':(repo/'skills/dev'/p).stat().st_size} for p in files], 'small_view_metrics':small['metrics'],'history_heavy_view_metrics':large['metrics'], 'history_added_entries':120,'metric_scope':'serialized bytes only; not actual reads, context, tokens, cost or net benefit'}
 # Separate sizing clone; never mutate the two handoff cases after freezing.
 sizing=home/'sizing';shutil.copytree(home/'alpha',sizing)
 sizing_folder=sizing/'.agent-workflow/features/FEAT-001'
 sizing_before=capture(sizing,'FEAT-001','verify',['T-FOCUS'])
 for name in ['task-review.json','regression-review.json']:
  p=sizing_folder/name
  doc=json.loads(p.read_text()) if p.exists() else {'feature_id':'FEAT-001'}
  doc['history']=[{'notes':'SYNTHETIC_OLD_REVIEW_BODY '+('old details '*800)} for _ in range(20)]
  p.write_text(json.dumps(doc))
 sizing_after=capture(sizing,'FEAT-001','verify',['T-FOCUS'])
 metrics['review_history_probe']={'before':sizing_before['metrics'],'after':sizing_after['metrics'],
  'task_review_history_embedded':'SYNTHETIC_OLD_REVIEW_BODY' in json.dumps(sizing_after['task_review']),
  'regression_history_embedded':'SYNTHETIC_OLD_REVIEW_BODY' in json.dumps(sizing_after['historical_regression']),
  'scope':'synthetic optional history field probe; capture readability is not schema/audit validity or measured runtime cost'}
 (home/'metrics.json').write_text(json.dumps(metrics,indent=2))
 print(str(home));print(json.dumps(metrics))
finally:f.doCleanups()
