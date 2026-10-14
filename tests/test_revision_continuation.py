import copy
import json
import unittest
import test_revisions as fixtures
from revisions import inspect, validate_continuation


class RevisionContinuationTests(unittest.TestCase):
    setUp = fixtures.RevisionTests.setUp
    write = fixtures.RevisionTests.write
    run_script = fixtures.RevisionTests.run_script
    cmd = fixtures.RevisionTests.cmd
    doc = fixtures.RevisionTests.doc
    proposal = fixtures.RevisionTests.proposal
    propose = fixtures.RevisionTests.propose
    apply = fixtures.RevisionTests.apply
    review = fixtures.RevisionTests.review
    gates = fixtures.RevisionTests.gates

    def continuation(self, after='Return uppercase text using the newly confirmed spacing rule'):
        b = self.doc()['feature']['baseline']
        p = self.proposal()
        p.update(continues_revision=b['applied'][-1]['id'],
                 continuation_reason='Product corrected the unfinished intent; preserve earlier applied history',
                 kind='requirement_change', decision_ids=['D-002'])
        p['changes'][0]['after'] = after
        return p

    def confirm(self, status='approved'):
        d = json.loads((self.folder/'decisions.json').read_text())
        d['decisions'] = [x for x in d['decisions'] if x['id'] != 'D-002']
        d['decisions'].append({'id':'D-002','status':status,'chosen':'Use corrected current spacing rule',
                               'approval_ref':'Synthetic product confirmation, not an invented delivery'})
        self.write('decisions.json', d)

    def test_multiple_unverified_revisions_preserve_proposals_and_no_fictitious_delivery(self):
        self.apply(); self.confirm()
        first = (self.folder/'revisions/CHG-001.json').read_bytes()
        for rid, after in [('CHG-002','Updated product rule'),('CHG-003','Final product rule')]:
            self.propose(self.continuation(after)); self.cmd('apply','--revision',rid)
        d=self.doc(); b=d['feature']['baseline']
        self.assertEqual(b['version'],4); self.assertEqual(b['deliveries'],[])
        self.assertEqual(d['feature']['status'],'provisional')
        self.assertEqual(b['applied'][1]['continues_revision'],'CHG-001')
        self.assertEqual(b['applied'][2]['continues_revision'],'CHG-002')
        self.assertEqual((self.folder/'revisions/CHG-001.json').read_bytes(),first)
        self.assertEqual(json.loads(self.cmd('status'))['verified_version'],0)
        self.assertEqual(d['requirements'][0]['acceptance_criteria'],self.req['requirements'][0]['acceptance_criteria'])
        self.assertEqual(inspect(self.folder.resolve(),d)[2],[])
        self.run_script('render-workspace.py',self.root,'FEAT-001')
        self.assertIn('Continues unverified CHG-002',(self.folder/'revisions.md').read_text())

    def test_missing_wrong_incomplete_or_stale_continuation_refuses_before_writes(self):
        self.apply(); self.confirm(); valid=self.continuation(); original=(self.folder/'spec/requirements.json').read_bytes()
        variants=[]
        p=copy.deepcopy(valid);p.pop('continues_revision');p.pop('continuation_reason');variants.append(p)
        p=copy.deepcopy(valid);p['continues_revision']='CHG-999';variants.append(p)
        p=copy.deepcopy(valid);p['continuation_reason']='';variants.append(p)
        p=copy.deepcopy(valid);p['base_digest']='stale';variants.append(p)
        p=copy.deepcopy(valid);p['changes'][0]['before']='old product text';variants.append(p)
        for p in variants:
            self.propose(p,expected=1)
            self.assertEqual((self.folder/'spec/requirements.json').read_bytes(),original)
        self.assertEqual(len(list((self.folder/'revisions').glob('CHG-*.json'))),1)

    def test_pending_decision_and_changed_preserved_source_cannot_apply(self):
        self.apply(); self.confirm('pending'); p=self.continuation()
        source=self.root/'clarification.txt';source.write_text('Synthetic changed product direction')
        self.propose(p,'--source',source); original=(self.folder/'spec/requirements.json').read_bytes()
        self.cmd('apply','--revision','CHG-002',expected=1)
        self.assertEqual((self.folder/'spec/requirements.json').read_bytes(),original)
        self.confirm(); record=json.loads((self.folder/'revisions/CHG-002.json').read_text())
        (self.folder/record['source_files'][0]['path']).write_text('tampered source')
        self.cmd('apply','--revision','CHG-002',expected=1)
        self.assertEqual((self.folder/'spec/requirements.json').read_bytes(),original)

    def test_only_one_pending_revision_and_cancel_keeps_current_baseline(self):
        self.apply(); self.confirm(); self.propose(self.continuation())
        self.propose(self.continuation('Another updated rule'),expected=1)
        self.cmd('cancel','--revision','CHG-002','--reason','Withdraw this pending correction')
        self.assertEqual(self.doc()['feature']['baseline']['version'],2)
        self.propose(self.continuation('Replacement corrected rule'))
        self.cmd('apply','--revision','CHG-003')
        self.assertEqual(self.doc()['feature']['baseline']['applied'][-1]['continues_revision'],'CHG-001')
        self.assertEqual(self.doc()['feature']['baseline']['cancelled'][0]['id'],'CHG-002')

    def test_applied_continuation_and_proposal_tampering_are_rejected(self):
        self.apply(); self.confirm(); self.propose(self.continuation()); self.cmd('apply','--revision','CHG-002')
        original=self.doc();bad=copy.deepcopy(original);bad['feature']['baseline']['applied'][-1]['continues_revision']='CHG-999'
        with self.assertRaisesRegex(ValueError,'continuation'):inspect(self.folder.resolve(),bad)
        path=self.folder/'revisions/CHG-002.json';p=json.loads(path.read_text());p['continuation_reason']='rewritten history';path.write_text(json.dumps(p))
        self.cmd('status',expected=1)

    def test_only_latest_baseline_can_deliver_and_old_quality_result_is_stale(self):
        self.apply(); self.review(); self.gates(); self.confirm()
        self.propose(self.continuation()); self.cmd('apply','--revision','CHG-002');self.review()
        self.cmd('verify','--code-revision',self.head,expected=1)
        self.assertEqual(self.doc()['feature']['baseline']['deliveries'],[])
        self.gates();self.cmd('verify','--code-revision',self.head)
        self.assertEqual([x['version'] for x in self.doc()['feature']['baseline']['deliveries']],[3])
        self.assertEqual(self.doc()['feature']['status'],'provisional')

    def test_delivered_baseline_uses_normal_revision_not_unverified_marker(self):
        self.apply(); self.review(); self.gates(); self.cmd('verify','--code-revision',self.head);self.confirm()
        self.propose(self.continuation(),expected=1)
        p=self.continuation();p.pop('continues_revision');p.pop('continuation_reason')
        self.propose(p);self.cmd('apply','--revision','CHG-002')
        self.assertNotIn('continues_revision',self.doc()['feature']['baseline']['applied'][-1])

    def test_surviving_earlier_field_cannot_silently_drop_its_test_obligations(self):
        p=self.proposal();p['test_ids']=['UT-1','UT-EARLY'];self.propose(p);self.cmd('apply','--revision','CHG-001');self.confirm()
        p=self.continuation();p['changes']=[{'requirement_id':'R-1','field':'title',
            'before':self.doc()['requirements'][0]['title'],'after':'Clarified uppercase title'}]
        with self.assertRaisesRegex(ValueError,'UT-EARLY'):
            validate_continuation(p,self.doc()['feature']['baseline'],inspect(self.folder.resolve(),self.doc())[1],required=True)
        self.propose(p,expected=1)
        p['test_ids']=['UT-1','UT-EARLY'];self.propose(p);self.cmd('apply','--revision','CHG-002')
        self.review();self.gates(ids=['UT-1'])
        self.run_script('validate-feature.py','--stage','check',self.root,'FEAT-001')
        self.cmd('verify','--code-revision',self.head,expected=1)
        self.assertEqual(self.doc()['feature']['baseline']['deliveries'],[])

    def test_replaced_field_does_not_force_obsolete_test_meaning(self):
        p=self.proposal();p['test_ids']=['UT-OLD'];self.propose(p);self.cmd('apply','--revision','CHG-001');self.confirm()
        p=self.continuation();p['test_ids']=['UT-NEW'];self.propose(p);self.cmd('apply','--revision','CHG-002')
        self.assertEqual(self.doc()['feature']['baseline']['version'],3)
        self.assertEqual(self.doc()['feature']['baseline']['deliveries'],[])

    def test_restoring_a_retired_requirement_restores_surviving_test_obligations(self):
        p=self.proposal();p['test_ids']=['UT-1','UT-EARLY'];self.propose(p);self.cmd('apply','--revision','CHG-001');self.confirm()
        p=self.continuation();p['changes']=[{'requirement_id':'R-1','field':'status','before':'confirmed','after':'deprecated'}]
        self.propose(p);self.cmd('apply','--revision','CHG-002')
        p=self.continuation();p['changes']=[{'requirement_id':'R-1','field':'status','before':'deprecated','after':'confirmed'}]
        with self.assertRaisesRegex(ValueError,'UT-EARLY'):
            validate_continuation(p,self.doc()['feature']['baseline'],inspect(self.folder.resolve(),self.doc())[1],required=True)
        self.propose(p,expected=1)
        p['test_ids']=['UT-1','UT-EARLY'];self.propose(p);self.cmd('apply','--revision','CHG-003')
        self.assertEqual(self.doc()['requirements'][0]['status'],'confirmed')
        self.assertEqual(self.doc()['feature']['baseline']['deliveries'],[])
