"""Synthetic workflow facts, not Android rendering or dependency inference."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import test_verification as legacy_fixture
import test_manual_scope as scope_fixture
import test_check_runs as check_fixture
import verification as v
import manual_scope as m
from intake_helpers import attach_intake


class AcceptanceContinuationTests(unittest.TestCase):
    def inventory(self, root, folder, **kwargs):
        spec=importlib.util.spec_from_file_location('continuation_inventory',Path(v.__file__).with_name('verify-inputs.py'))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module.collect(root,folder.name,**kwargs)

    def thirty_seven(self):
        h=legacy_fixture.VerificationTests();h.setUp();self.addCleanup(h.doCleanups)
        root,folder=h.root.resolve(),h.folder.resolve()
        req=v.read(folder/'spec/requirements.json')
        req['requirements'][0]['statement']='Six occupied-message consumers follow parent line format; independent state behaviors remain unchanged'
        req['requirements'][0]['acceptance_criteria']=['Occupied message consumer %d uses parent format'%i if i<6 else 'Separate unchanged state behavior %d'%i for i in range(35)]
        attach_intake(folder,req)
        files={'values-en.json':{'occupied':'Already occupied. Try another email.'},'values-zh.json':{'occupied':'Already occupied. Try another email.'}}
        for name,value in files.items():(root/name).write_text(json.dumps(value))
        (root/'ui.py').write_text('# Read occupied resource in six synthetic branches\n')
        (root/'ui_expectations.py').write_text('expected_lines = 1\n')
        h.doc['allowed_paths']+=list(files)+['ui.py','ui_expectations.py'];h.doc['inspected_paths']+=list(files)+['ui.py','ui_expectations.py'];h.save();v.sync(root,folder)
        h.git('add','-A');h.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','synthetic original inputs')
        base=h.git('rev-parse','HEAD').strip();(folder/'evidence').mkdir();(folder/'evidence/origin.txt').write_text('Synthetic original input identity '+base)
        plan=v.load_plan(folder);manual=[row for row in plan['items'] if row['mode']=='manual'];self.assertEqual(len(manual),37)
        stamp,head=v.context(root,folder,plan)
        with patch.object(v,'render'):
            for i,row in enumerate(manual):
                waived=i>=28
                v.record(root,folder,row['id'],'waived' if waived else 'passed',stamp,head,
                         'Synthetic waiver only; no execution' if waived else 'Synthetic original workflow observation; not Android UI',
                         'Fixture original authorization: unchanged unrelated scope; reason, risk and follow-up accepted' if waived else 'evidence/origin.txt')
        original=copy.deepcopy(v.load_plan(folder));h.git('add','.agent-workflow');h.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','save original observations')
        records_at=h.git('rev-parse','HEAD').strip()
        for name,value in files.items():value['occupied']='Already occupied.\nTry another email.';(root/name).write_text(json.dumps(value))
        (root/'ui.py').write_text('# Same resource lookup; explicit line break now supplied\n');(root/'ui_expectations.py').write_text('expected_lines = 2\n')
        h.git('add',*files,'ui.py','ui_expectations.py');h.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','synthetic localized newline and expected value')
        req=v.read(folder/'spec/requirements.json');req['requirements'][0]['statement']+='; occupied messages now use two explicit lines'
        attach_intake(folder,req);v.sync(root,folder)
        return h,root,folder,base,records_at,original,manual

    def states(self,root,folder):
        doc=v.load_plan(folder);stamp,_=v.context(root,folder,doc);current=v.check_currency(root,folder)
        return {r['id']:v.state(r,stamp,v.row_evidence_stamp(root,folder,r,current)) for r in doc['items']}

    def test_parent_change_legacy_stales_37_but_existing_batch_retains_22_in_one_write(self):
        h,root,folder,base,records_at,original,manual=self.thirty_seven();states=self.states(root,folder)
        self.assertTrue(all(states[r['id']]=='stale' for r in manual))
        from evidence_carry import input_snapshot
        with self.assertRaisesRegex(ValueError,'full parent'):input_snapshot(root,folder,manual[7]['id'],records_at)
        m.prepare(root,folder);ids=[r['id'] for r in manual[:28]]
        snap=m.capture(root,folder,[{'item_id':i,'contract_revision':records_at} for i in ids])
        # Use the existing synthetic review shape; this attests supplied facts,
        # never proves dependency completeness or actual device layout.
        helper=scope_fixture.ManualScopeTests();helper.base=base
        review=helper.review(snap)
        for f in review['findings']:
            if f['item_id'] in ids[:6]:
                f['verdict']='affected';f['dependencies']+=['values-en.json','values-zh.json','ui.py']
                for c in f['assessment_refs']:
                    if c.endswith((':values-en.json',':values-zh.json')):f['assessment_refs'][c]='affected'
        review['apply_ids']=ids[6:]
        with patch.object(v,'save',wraps=v.save) as saves,patch.object(v,'render',wraps=v.render) as renders:m.apply(root,folder,snap,review)
        self.assertEqual(saves.call_count,1);self.assertEqual(renders.call_count,1)
        states=self.states(root,folder);self.assertEqual(sum(states[i]=='retained' for i in ids),22)
        self.assertTrue(all(states[i]=='stale' for i in ids[:6]))
        self.assertTrue(all(states[r['id']]=='stale' for r in manual[28:]))
        doc=v.load_plan(folder);self.assertEqual([r['history'] for r in doc['items']],[r['history'] for r in original['items']])
        with self.assertRaisesRegex(ValueError,'passed/retained'):m.capture(root,folder,[{'item_id':manual[-1]['id'],'contract_revision':records_at}])
        from claim_review import identity
        self.assertEqual(len(identity(root,folder)['claims']),37)
        self.assertFalse((folder/'check-runs').exists());self.assertFalse((h.base/'quality-report.json').exists())
        print('SYNTHETIC_NEWLINE: legacy_stale=37 retained=22 affected=6 waiver_authority_checks=9 shared_saves=1; no new test execution')

    def test_replaced_claim_is_not_a_batch_source_but_unchanged_rows_are_candidates(self):
        x=scope_fixture.ManualScopeTests();x.setUp();self.addCleanup(x.doCleanups)
        req=v.read(x.folder/'spec/requirements.json');req['requirements'][0]['acceptance_criteria'][0]+='; two explicit lines'
        attach_intake(x.folder,req);v.sync(x.root,x.folder)
        doc=v.load_plan(x.folder);new=next(r for r in doc['items'] if r['source'].startswith('requirement:'))
        self.assertFalse(new['history']);self.assertIn(x.ids[0],[r['id'] for r in doc['retired']])
        with self.assertRaisesRegex(ValueError,'latest passed'):m.capture(x.root,x.folder,[{'item_id':new['id']}])
        snap=x.capture(x.ids[1:]);x.apply(snap,x.review(snap))
        self.assertTrue(all(x.states()[i]=='retained' for i in x.ids[1:]));self.assertEqual(x.states()[new['id']],'not_run')

    def test_unknown_shared_consumer_or_environment_cannot_be_supported(self):
        x=scope_fixture.ManualScopeTests();x.setUp();self.addCleanup(x.doCleanups);snap=x.capture();review=x.review(snap)
        f=review['findings'][0];key=next(iter(f['assessment_refs']));f['assessment_refs'][key]='unknown'
        with self.assertRaisesRegex(ValueError,'contradicts'):x.apply(snap,review)
        f['verdict']='unknown';f['environment_evidence']='Shared consumers or narrow-width wrapping unverified; no real Android rendering evidence'
        review['apply_ids']=x.ids[1:];x.apply(snap,review);self.assertEqual(x.states()[x.ids[0]],'stale')
        guide=self.inventory(x.root,x.folder)['continuation']['manual_applicability']
        self.assertNotIn(x.ids[0],guide['review_candidates']);self.assertIn(x.ids[0],guide['prior_negative_assessments'])

    def test_ordinary_inventory_routes_matching_execution_without_running_it(self):
        x=check_fixture.CheckRunTests();x.setUp();self.addCleanup(x.doCleanups)
        ident=x.map_claim();first=x.execute();x.adopt(ident)
        decisions=v.read(x.folder/'decisions.json');decisions['decisions'].append({'id':'D-ROUTE','status':'approved','evidence':'Synthetic clarified interpretation, not a new actual assertion'})
        (x.folder/'decisions.json').write_text(json.dumps(decisions));before=(x.folder/'verification.json').read_bytes()
        inventory=self.inventory(x.root,x.folder);continuation=inventory['continuation']
        self.assertEqual(continuation['attempt_id'],first['attempt_id']);self.assertIn(ident,continuation['claim_review_targets'])
        self.assertEqual(x.counter.read_text(),'1');self.assertEqual((x.folder/'verification.json').read_bytes(),before)
        minimal=self.inventory(x.root,x.folder,include_acceptance=False);self.assertNotIn('continuation',minimal)
        import subprocess,tempfile
        old=subprocess.check_output(['git','show','4c61d353f1:skills/dev/core/scripts/verify-inputs.py'],cwd=Path(__file__).resolve().parents[1])
        with tempfile.TemporaryDirectory() as work:
            path=Path(work)/'old_inventory.py';path.write_bytes(old)
            spec=importlib.util.spec_from_file_location('old_continuation_inventory',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            self.assertEqual(module.collect(x.root,x.folder.name,include_acceptance=False),minimal)


    def test_ordinary_inventory_classifies_legacy_candidates_waivers_and_new_claims(self):
        x=scope_fixture.ManualScopeTests();x.setUp();self.addCleanup(x.doCleanups)
        doc=v.load_plan(x.folder);doc.pop('manual_scope_contract');doc.pop('manual_scope_reviews');doc['schema_version']=1;v.save(x.folder/'verification.json',doc)
        stamp,head=v.context(x.root,x.folder,doc);v.record(x.root,x.folder,x.ids[-1],'waived',stamp,head,'Synthetic approved unrelated exception','Reason risk follow-up and unchanged fixture authority')
        req=v.read(x.folder/'spec/requirements.json');req['requirements'][0]['statement']+='; new clarification';attach_intake(x.folder,req)
        before=(x.folder/'verification.json').read_bytes();inventory=self.inventory(x.root,x.folder);manual=inventory['continuation']['manual_applicability']
        self.assertEqual(manual['contract'],'legacy');self.assertIn(x.ids[0],manual['review_candidates']);self.assertIn(x.ids[-1],manual['waiver_authority_checks'])
        self.assertEqual((x.folder/'verification.json').read_bytes(),before);self.assertNotIn('manual_scope_contract',v.load_plan(x.folder))

    def test_ordinary_inventory_never_routes_latest_failure_to_adoption(self):
        x=check_fixture.CheckRunTests();x.setUp();self.addCleanup(x.doCleanups);x.execute()
        config=v.read(x.helper.base/'quality-gates.json');config['gates'][0]['command']=[sys.executable,'-c','raise SystemExit(9)']
        (x.helper.base/'quality-gates.json').write_text(json.dumps(config));self.assertEqual(check_fixture.runs.run(x.root,'FEAT-001'),2)
        before=(x.folder/'verification.json').read_bytes();guide=self.inventory(x.root,x.folder)['continuation']
        self.assertEqual(guide['execution_state'],'unavailable');self.assertIn('failed',guide['reason']);self.assertNotIn('claim_review_targets',guide)
        self.assertEqual(before,(x.folder/'verification.json').read_bytes())

    def test_ordinary_inventory_exposes_unsynced_plan_without_mutating_it(self):
        x=scope_fixture.ManualScopeTests();x.setUp();self.addCleanup(x.doCleanups)
        req=v.read(x.folder/'spec/requirements.json');req['requirements'][0]['acceptance_criteria'].append('New unexecuted claim')
        attach_intake(x.folder,req);before=(x.folder/'verification.json').read_bytes()
        guide=self.inventory(x.root,x.folder)['continuation'];self.assertEqual(guide['state'],'unavailable');self.assertIn('stale',guide['reason'])
        self.assertEqual(before,(x.folder/'verification.json').read_bytes())
        v.sync(x.root,x.folder);new=next(r for r in v.load_plan(x.folder)['items'] if not r['history'] and r['mode']=='manual')
        guide=self.inventory(x.root,x.folder)['continuation']['manual_applicability'];self.assertIn(new['id'],guide['new_or_adverse_claims']);self.assertNotIn(new['id'],guide['review_candidates'])
