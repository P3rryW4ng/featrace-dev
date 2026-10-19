import sys,json,copy,contextlib,io
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tests'))
import test_check_runs as t
import verification as v
import check_runs as runs
x=t.CheckRunTests();x.setUp()
try:
 with contextlib.redirect_stdout(io.StringIO()):
  ident=x.map_claim(); first=x.execute();x.adopt(ident);v.adopt_checks(x.root,x.folder,allow_claims=False)
  before=copy.deepcopy(x.plan()); p=x.folder/'spec/requirements.json'; req=json.loads(p.read_text())
  req['requirements'][0]['acceptance_criteria'][0]+=' (synthetic clarified scope)'
  p.write_text(json.dumps(req)); d=x.folder/'decisions.json'; dec=json.loads(d.read_text());dec['decisions'].append({'id':'D-PROBE','status':'approved','evidence':'Synthetic clarification, not product authority'});d.write_text(json.dumps(dec))
  v.sync(x.root,x.folder)
  current=runs.current(x.root,'FEAT-001'); doc=x.plan(); rows=[r for r in doc['items'] if r['source'].startswith('gate:')]
  state_before=x.effective(rows[0]); old_retired=any(r['id']==ident for r in doc['retired'])
  new=next(r for r in doc['items'] if r['source']==before['items'][0]['source']);new.update(mode='automatic',gates=['unit'],coverage='Synthetic scope mapping inspected',test_ids=['UT-1']);(x.folder/'verification.json').write_text(json.dumps(doc))
  x.adopt(new['id']);v.adopt_checks(x.root,x.folder,allow_claims=False)
  result={'synthetic_only':True,'same_attempt':current['attempt_id']==first['attempt_id'],'physical_executions':int(x.counter.read_text()),'old_row_retired':old_retired,'generated_gate_after_semantics':state_before,'new_claim_after_explicit_review':x.effective(next(r for r in x.plan()['items'] if r['id']==new['id'])),'gate_after_adoption':x.effective(x.plan()['items'][-1]),'original_history_preserved':next(r for r in x.plan()['retired'] if r['id']==ident)['history']==before['items'][0]['history']}
 print(json.dumps(result,indent=2));assert result['same_attempt'] and result['physical_executions']==1 and result['original_history_preserved'] and state_before=='stale' and result['new_claim_after_explicit_review']=='passed'
finally:x.doCleanups()
