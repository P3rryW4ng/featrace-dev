import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_verification
import verification as v
import check_runs as runs


class CheckRunTests(unittest.TestCase):
    def setUp(self):
        self.helper = test_verification.VerificationTests(); self.helper.setUp(); self.addCleanup(self.helper.doCleanups)
        self.root, self.folder = self.helper.root.resolve(), self.helper.folder.resolve()
        self.counter = self.root / '.agent-workflow/scratch/count'
        self.counter.parent.mkdir(exist_ok=True)
        self.command = [sys.executable, '-B', '-c', 'from pathlib import Path; p=Path(".agent-workflow/scratch/count"); p.write_text(str(int(p.read_text())+1) if p.exists() else "1")']
        self.helper.gates(self.command)
        runs.prepare(self.root, 'FEAT-001', [{'name':'unit','test_ids':['UT-1']}], 'Explicit fixture selection')
        v.sync(self.root, self.folder)

    def plan(self): return v.load_plan(self.folder)

    def execute(self):
        self.assertEqual(runs.run(self.root, 'FEAT-001'), 0)
        return runs.current(self.root, 'FEAT-001')

    def map_claim(self):
        doc = self.plan(); row = doc['items'][0]
        row.update(mode='automatic', gates=['unit'], coverage='Fixture assertion proof', test_ids=['UT-1'])
        (self.folder/'verification.json').write_text(json.dumps(doc)); return row['id']

    def adopt(self, ident):
        frozen=v.check_mapping_snapshot(self.root,self.folder,[ident])
        review={'input_digest':frozen['input_digest'],'item_ids':[ident],'reviewer':'Synthetic inspected fixture', 'status':'supported',
                'findings':[{'item_id':ident,'verdict':'supported','test_ids':['UT-1'],'assertion_evidence':'Fixture command output and actual assertion inspected', 'required_scope':'Exact fixture claim, not a real product','counterexample_check':'Unasserted expanded claims must not pass'}]}
        return v.adopt_checks(self.root,self.folder,review=review)

    def effective(self, row):
        stamp,_=v.context(self.root,self.folder,self.plan());return v.state(row,stamp,v.row_evidence_stamp(self.root,self.folder,row))

    def test_execution_rebind_after_record_change_without_command_and_idempotent(self):
        ident=self.map_claim();report=self.execute();self.adopt(ident)
        original=copy.deepcopy(self.plan());self.assertEqual(self.counter.read_text(),'1')
        decisions=json.loads((self.folder/'decisions.json').read_text());decisions['decisions'].append({'id':'D-FIXTURE','status':'approved','evidence':'changed narrative; requires mapping review'})
        (self.folder/'decisions.json').write_text(json.dumps(decisions))
        self.assertEqual(runs.current(self.root,'FEAT-001')['attempt_id'],report['attempt_id'])
        self.assertEqual(self.effective(self.plan()['items'][0]),'stale')
        self.adopt(ident);self.assertEqual(self.counter.read_text(),'1');after=self.plan()
        self.assertEqual(after['items'][0]['history'][0],original['items'][0]['history'][0]);self.assertEqual(len(after['items'][0]['history']),2)
        self.adopt(ident);self.assertEqual(self.plan(),after)
        original_review=after['items'][0]['history'][-1]['mapping_review']['review']
        v.adopt_checks(self.root,self.folder,review=original_review);self.assertEqual(self.plan(),after)

    def test_latest_failed_and_missing_terminal_never_search_old_green(self):
        self.execute();first=runs.locate(self.root,'FEAT-001')[0]
        config=json.loads((self.helper.base/'quality-gates.json').read_text());config['gates'][0]['command']=[sys.executable,'-c','raise SystemExit(7)']
        (self.helper.base/'quality-gates.json').write_text(json.dumps(config));self.assertEqual(runs.run(self.root,'FEAT-001'),2)
        with self.assertRaisesRegex(ValueError,'latest check attempt'):runs.current(self.root,'FEAT-001')
        latest,_=runs.locate(self.root,'FEAT-001');(latest/'result.json').unlink()
        with self.assertRaises((OSError,ValueError)):runs.current(self.root,'FEAT-001')
        with self.assertRaisesRegex(ValueError,'unfinished'):runs.run(self.root,'FEAT-001')
        self.assertTrue((first/'result.json').exists())

    def test_input_change_and_selection_change_expire_execution_but_prose_does_not(self):
        self.execute();cfg=json.loads((self.helper.base/'quality-gates.json').read_text());cfg['selection_reason']='new prose';cfg['gates'][0]['purpose']='new generated claim'
        (self.helper.base/'quality-gates.json').write_text(json.dumps(cfg));self.assertEqual(runs.view(self.root,'FEAT-001')['state'],'current')
        (self.root/'convert.py').write_text('changed source')
        self.assertEqual(runs.view(self.root,'FEAT-001')['state'],'unavailable')
        self.helper.git('checkout','--','convert.py');chosen=json.loads((self.folder/'check-selection.json').read_text());chosen['gates'][0]['test_ids']=['NEW']
        (self.folder/'check-selection.json').write_text(json.dumps(chosen));self.assertEqual(runs.view(self.root,'FEAT-001')['state'],'unavailable')

    def test_feature_isolation_and_workspace_lock(self):
        first=self.execute();other=self.folder.parent/'FEAT-002';other.mkdir();(other/'spec').mkdir();(other/'spec/requirements.json').write_text(json.dumps({'feature':{'id':'FEAT-002'},'requirements':[]}))
        runs.prepare(self.root,'FEAT-002',[{'name':'unit','test_ids':['OTHER']}],'Other feature')
        with runs.execution_lock(self.root):
            self.assertEqual(runs.view(self.root,'FEAT-001')['state'],'unavailable')
            with self.assertRaisesRegex(ValueError,'busy'):runs.run(self.root,'FEAT-002')
        self.assertEqual(runs.run(self.root,'FEAT-002'),0)
        self.assertEqual(runs.current(self.root,'FEAT-001')['attempt_id'],first['attempt_id'])
        self.assertNotEqual(runs.current(self.root,'FEAT-002')['attempt_id'],first['attempt_id'])
        self.assertFalse((self.helper.base/'quality-report.json').exists())

    def test_tampered_fact_and_removed_mode_refuse_without_legacy_fallback(self):
        self.execute();d,_=runs.locate(self.root,'FEAT-001');record=json.loads((d/'result.json').read_text());record['results'][0]['returncode']=7;(d/'result.json').write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,'corrupt'):runs.current(self.root,'FEAT-001')
        with self.assertRaisesRegex(ValueError,'corrupt'):runs.run(self.root,'FEAT-001')
        cfg=json.loads((self.helper.base/'quality-gates.json').read_text());del cfg['execution_contract'];(self.helper.base/'quality-gates.json').write_text(json.dumps(cfg))
        with self.assertRaisesRegex(ValueError,'no fallback'):runs.enabled(self.root)

    def test_mapping_review_drift_partial_and_unaffected_row_history(self):
        ident=self.map_claim();self.execute();self.adopt(ident)
        doc=self.plan();gate=doc['items'][-1];v.adopt_checks(self.root,self.folder,locked=False,allow_claims=False);gate_before=copy.deepcopy(self.plan()['items'][-1])
        doc=self.plan();doc['items'][0]['coverage']='Rechecked assertion evidence';(self.folder/'verification.json').write_text(json.dumps(doc))
        self.assertEqual(self.effective(self.plan()['items'][-1]),'passed');self.adopt(ident)
        self.assertEqual(self.plan()['items'][-1],gate_before)
        with self.assertRaises(ValueError):v.adopt_checks(self.root,self.folder,review={'item_ids':[ident],'status':'partial'})

    def test_runner_and_adoption_cli_complete_without_borrowing_project_report(self):
        self.helper.run_script('verification.py','run',self.root,'FEAT-001',expected=2)
        self.assertEqual(self.counter.read_text(),'1');self.assertEqual(self.effective(self.plan()['items'][-1]),'passed')
        self.assertEqual(self.plan()['schema_version'],4)
        out=self.helper.run_script('verify-inputs.py',self.root,'FEAT-001')
        self.assertIn('attempt_id',out);self.assertIn('current',out)
        with self.assertRaises((ValueError,OSError)):runs.selection(self.root,'UNKNOWN')

    def test_timeout_stops_owned_group_and_does_not_pass(self):
        cfg=json.loads((self.helper.base/'quality-gates.json').read_text());cfg['gates'][0].update(command=[sys.executable,'-c','import time;time.sleep(5)'],timeout_seconds=0.05)
        (self.helper.base/'quality-gates.json').write_text(json.dumps(cfg))
        self.assertEqual(runs.run(self.root,'FEAT-001'),2)
        start,result=runs.terminal(self.root,'FEAT-001');self.assertEqual(result['status'],'unavailable');self.assertTrue(result['lifecycle_safe'])
        self.assertEqual(result['results'][0]['error'],'TimeoutExpired')
        self.assertEqual(runs.view(self.root,'FEAT-001')['state'],'unavailable')

    def test_execution_drift_and_ignored_declared_input_are_not_reusable(self):
        cfg=json.loads((self.helper.base/'quality-gates.json').read_text());cfg['gates'][0]['command']=[sys.executable,'-c','from pathlib import Path;Path("convert.py").write_text("changed")']
        (self.helper.base/'quality-gates.json').write_text(json.dumps(cfg));self.assertEqual(runs.run(self.root,'FEAT-001'),2)
        self.assertEqual(runs.view(self.root,'FEAT-001')['state'],'unavailable')
        self.helper.git('checkout','--','convert.py');cfg['gates'][0]['command']=self.command;(self.helper.base/'quality-gates.json').write_text(json.dumps(cfg))
        self.helper.git('config','core.excludesFile','/dev/null')
        (self.root/'.git/info/exclude').write_text('local-input.txt\n');(self.root/'local-input.txt').write_text('one')
        (self.helper.base/'evidence-files.json').write_text(json.dumps({'files':['local-input.txt']}));self.execute()
        (self.root/'local-input.txt').write_text('two');self.assertEqual(runs.view(self.root,'FEAT-001')['state'],'unavailable')

    def test_terminal_save_crash_retains_start_blocks_retry_without_reexecution(self):
        real=runs.save
        def crash(root,path,value,**kwargs):
            if Path(path).name=='result.json':raise OSError('Synthetic terminal persistence interruption')
            return real(root,path,value,**kwargs)
        with patch.object(runs,'save',side_effect=crash):
            with self.assertRaises(OSError):runs.run(self.root,'FEAT-001')
        self.assertEqual(self.counter.read_text(),'1')
        with self.assertRaisesRegex(ValueError,'unfinished'):runs.run(self.root,'FEAT-001')
        self.assertEqual(self.counter.read_text(),'1')

    def test_stale_mapping_review_no_writes_and_new_claim_not_automatically_covered(self):
        ident=self.map_claim();self.execute();frozen=v.check_mapping_snapshot(self.root,self.folder,[ident])
        review={'input_digest':frozen['input_digest'],'item_ids':[ident],'reviewer':'fixture','status':'supported','findings':[]}
        doc=self.plan();doc['items'][0]['coverage']='Different inspected assertion';(self.folder/'verification.json').write_text(json.dumps(doc));before=(self.folder/'verification.json').read_bytes()
        with self.assertRaises(ValueError):v.adopt_checks(self.root,self.folder,review=review)
        self.assertEqual((self.folder/'verification.json').read_bytes(),before)
        v.adopt_checks(self.root,self.folder,allow_claims=False)
        self.assertEqual(self.plan()['items'][0]['history'],[])
        self.assertEqual(self.counter.read_text(),'1')

    def test_successful_fact_survives_result_registration_failure(self):
        ident=self.map_claim();self.execute();before=(self.folder/'verification.json').read_bytes()
        with patch.object(v,'save',side_effect=OSError('Synthetic registration failure')):
            with self.assertRaises(OSError):self.adopt(ident)
        self.assertEqual((self.folder/'verification.json').read_bytes(),before)
        self.adopt(ident);self.assertEqual(self.counter.read_text(),'1')

    def test_schema_and_mode_reject_legacy_readers(self):
        import io,tarfile,tempfile
        base=Path(__file__).resolve().parents[1]
        raw=subprocess.check_output(['git','archive','0a33739','skills/dev'],cwd=base)
        with tempfile.TemporaryDirectory() as work:
            old=Path(work)
            with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
                self.assertTrue(all(m.isfile() or m.isdir() for m in archive.getmembers()));archive.extractall(old)
            p=subprocess.run([sys.executable,'-B',str(old/'skills/dev/core/scripts/verification.py'),'status',str(self.root),'FEAT-001'],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0);self.assertIn('invalid verification identity/schema',p.stderr+p.stdout)
            p=subprocess.run([sys.executable,'-B',str(old/'skills/dev/core/scripts/project.py'),'validate-gates',str(self.root)],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0);self.assertIn('unsupported quality configuration field',p.stderr+p.stdout)


    def test_audit_final_review_status_and_stage_use_same_current_attempt(self):
        self.execute();v.adopt_checks(self.root,self.folder,allow_claims=False);self.helper.accept_manual()
        self.helper.run_script('audit-delivery.py',self.root,'FEAT-001')
        output=self.helper.run_script('feature-status.py',self.root,'FEAT-001');self.assertIn('CHECK_EXECUTION: current',output)
        from claim_review import identity
        first=identity(self.root,self.folder);self.assertTrue(all(c['result_status']=='passed' for c in first['claims']))
        spec=importlib.util.spec_from_file_location('fixture_stage',Path(v.__file__).with_name('stage_view.py'));stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)
        view=stage.capture(self.root,'FEAT-001','verify');self.assertIn('check-runs/',view['quality_report']['full_report_ref']);self.assertEqual(view['quality_report']['attempt_id'],runs.current(self.root,'FEAT-001')['attempt_id'])
        cfg=json.loads((self.helper.base/'quality-gates.json').read_text());cfg['gates'][0]['command']=[sys.executable,'-c','raise SystemExit(3)'];(self.helper.base/'quality-gates.json').write_text(json.dumps(cfg));runs.run(self.root,'FEAT-001')
        self.helper.run_script('audit-delivery.py',self.root,'FEAT-001',expected=1)
        self.assertIn('unavailable',self.helper.run_script('feature-status.py',self.root,'FEAT-001'))

    def test_plan_drift_after_read_refuses_adoption_without_overwrite(self):
        ident=self.map_claim();self.execute();real=runs.current;calls=[0]
        def changed(root,feature):
            out=real(root,feature);calls[0]+=1
            if calls[0]==2:
                doc=self.plan();doc['items'][0]['coverage']='Concurrent external coverage edit';(self.folder/'verification.json').write_text(json.dumps(doc))
            return out
        with patch.object(runs,'current',side_effect=changed):
            with self.assertRaises(ValueError):self.adopt(ident)
        self.assertEqual(self.plan()['items'][0]['coverage'],'Concurrent external coverage edit')
        self.assertEqual(self.plan()['items'][0]['history'],[])

    def test_symlink_and_unknown_input_refuse_before_any_command(self):
        local=self.root/'link.txt';local.symlink_to(self.root/'convert.py')
        with self.assertRaises(ValueError):runs.run(self.root,'FEAT-001')
        self.assertFalse(self.counter.exists());local.unlink()
        chosen=self.folder/'check-selection.json';value=chosen.read_bytes();chosen.unlink();chosen.symlink_to(self.helper.base/'quality-gates.json')
        with self.assertRaises(ValueError):runs.selection(self.root,'FEAT-001')
        chosen.unlink();chosen.write_bytes(value)

    def test_keyboard_interrupt_records_interruption_and_stops_remaining_checks(self):
        cfg=json.loads((self.helper.base/'quality-gates.json').read_text());cfg['gates'][0]['command']=[sys.executable,'-c','import time;time.sleep(5)'];(self.helper.base/'quality-gates.json').write_text(json.dumps(cfg))
        real=subprocess.Popen.communicate;called=[False]
        def interrupt(proc,*args,**kwargs):
            if not called[0]:called[0]=True;raise KeyboardInterrupt()
            return real(proc,*args,**kwargs)
        # Only the gate process is interrupted; Git captures also use communicate.
        real_gate=runs.run_gate
        def gate(*args):
            with patch.object(subprocess.Popen,'communicate',interrupt):return real_gate(*args)
        with patch.object(runs,'run_gate',side_effect=gate):self.assertEqual(runs.run(self.root,'FEAT-001'),2)
        _,result=runs.terminal(self.root,'FEAT-001');self.assertEqual(result['status'],'interrupted');self.assertTrue(result['lifecycle_safe'])

    def test_declared_success_is_not_accepted_if_process_group_unresolved(self):
        real=runs.run_gate
        def unresolved(*args):
            result,_=real(*args);return result,False
        with patch.object(runs,'run_gate',side_effect=unresolved):self.assertEqual(runs.run(self.root,'FEAT-001'),2)
        self.assertEqual(self.counter.read_text(),'1')
        with self.assertRaisesRegex(ValueError,'lifecycle'):runs.run(self.root,'FEAT-001')
        with self.assertRaisesRegex(ValueError,'lifecycle'):runs.prepare(self.root,'FEAT-001',[{'name':'unit','test_ids':['UT-1']}],'Do not reconfigure unresolved execution')

if __name__=='__main__':unittest.main()
