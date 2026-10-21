"""Synthetic storage round trips and correction safety, without business records."""
import copy
import json
import unittest
from unittest.mock import patch

import test_acceptance_contract as base
import acceptance_storage as codec
import acceptance_contract as a
import verification as v


class StorageCodecTests(unittest.TestCase):
    def document(self):
        manifest={"file-%05d"%i:{"sha256":"a"*64,"state":"file"} for i in range(3000)}
        return dict(schema_version=8, storage={"profile":7}, worlds=[dict(business=manifest,execution={"files":manifest}) for _ in range(4)], text={"ref":"ordinary user text","$snapshot_ref":"not a reference"})

    def test_repeated_large_snapshots_are_stored_once_and_exactly_restored(self):
        original=self.document(); encoded=codec.pack(original)
        self.assertEqual(codec.unpack(encoded),original)
        self.assertLess(len(json.dumps(encoded)),len(json.dumps(original))//3)
        self.assertEqual(codec.pack(codec.unpack(encoded)),encoded)

    def test_missing_object_refuses(self):
        data=codec.pack(self.document());data['objects'].pop(next(iter(data['objects'])))
        with self.assertRaisesRegex(ValueError,'STORAGE_INVALID'):codec.unpack(data)

    def test_modified_object_refuses(self):
        data=codec.pack(self.document()); key=next(iter(data['objects']));data['objects'][key]=['literal','different']
        with self.assertRaisesRegex(ValueError,'hash mismatch'):codec.unpack(data)

    def test_unreachable_object_refuses(self):
        data=codec.pack(self.document());item=['literal','unused'];data['objects'][codec.digest(item)]=item
        with self.assertRaisesRegex(ValueError,'unreachable'):codec.unpack(data)

    def test_bounded_expansion_refuses_but_literal_reference_text_is_preserved(self):
        data=codec.pack(self.document())
        with patch.object(codec,'MAX_BYTES',5000):
            with self.assertRaisesRegex(ValueError,'expansion'):codec.unpack(data)
        with patch.object(codec,'MAX_VISITS',5):
            with self.assertRaisesRegex(ValueError,'expansion'):codec.unpack(data)
        self.assertEqual(codec.unpack(data)['text'],self.document()['text'])

    def test_old_documents_are_not_rewritten(self):
        data={'schema_version':7,'anything':'unchanged'}
        self.assertIs(codec.pack(data),data);self.assertIs(codec.unpack(data),data)

    def test_wrong_envelope_or_node_refuses(self):
        data=codec.pack(self.document());data['extra']=True
        with self.assertRaisesRegex(ValueError,'STORAGE_INVALID'):codec.unpack(data)
        data=codec.pack(self.document());data['root']=['ref','not-present']
        with self.assertRaisesRegex(ValueError,'STORAGE_INVALID'):codec.unpack(data)


    def test_encoded_and_restored_snapshots_have_no_mutable_aliases(self):
        original=self.document();encoded=codec.pack(original);stored=copy.deepcopy(encoded)
        restored=codec.unpack(encoded)
        restored['worlds'][0]['business']['file-00000']['sha256']='changed'
        self.assertEqual(restored['worlds'][1]['business']['file-00000']['sha256'],'a'*64)
        self.assertEqual(encoded,stored)
        original['worlds'][0]['business']['file-00000']['sha256']='external mutation'
        self.assertEqual(encoded,stored)
        self.assertEqual(codec.unpack(encoded)['worlds'][0]['business']['file-00000']['sha256'],'a'*64)


class StorageAcceptanceTests(unittest.TestCase):
    def setUp(self):
        fixture=base.AcceptanceContractTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.x=fixture;self.root=fixture.root;self.folder=fixture.folder
        self.approval={'snapshot_storage':1,'evidence':'Synthetic explicit storage approval','hosts':[{'name':'synthetic host','snapshot_storage_capable':True}]}

    def prepare(self):
        self.x.h.helper.git('add','-A');self.x.commit('recoverable pre-storage original')
        return a.prepare_storage(self.root,self.folder,self.approval)

    def review(self,request,verdict='supported',kind=None):
        review=self.x.review(request,verdict)
        review['review_context']={'host':'synthetic test host','context_id':'separate synthetic context','reviewer':'synthetic reviewer'}
        if kind:
            for item in review['assess']:item['negative_kind']=kind
        return review

    def negative(self,kind='evidence_gap'):
        self.prepare();request=self.x.capture();review=self.review(request,'partial',kind)
        a.apply_assessment(self.root,self.folder,request,review)
        return request,review

    def correction(self,old):
        request=self.x.capture();review=self.review(request)
        event=a.latest_event(a.load(self.folder),'assessment')
        review['barrier_resolutions']=[dict(barrier_id=event['id']+':'+item['claim_key'],kind='judgment_correction',error_kind='scope_overreach',
            original_scope={k:item[k] for k in ('source_basis','required_scope','observed_scope')},addresses='Original claim requires excluding modification influence, not executing all old behavior',evidence='Exact same original facts establish the bounded claim') for item in old['assess']]
        return request,review

    def test_prepare_preserves_events_facts_and_original_digests_without_execution(self):
        self.x.accept();before=self.x.plan();count=self.x.h.counter.read_text();after=self.prepare()
        self.assertEqual(after['schema_version'],8)
        self.assertEqual(after['acceptance'],before['acceptance']);self.assertEqual(after['items'],before['items'])
        raw=json.loads((self.folder/'verification.json').read_text())
        self.assertEqual(raw['storage_contract'],1);self.assertNotIn('acceptance',raw)
        self.assertEqual(v.load_plan(self.folder),after)
        self.assertTrue(a.resolve_claims(self.root,self.folder)['acceptance_eligible'])
        self.assertEqual(self.x.h.counter.read_text(),count)

    def test_uncommitted_or_missing_host_authorization_refuses_no_write(self):
        original=(self.folder/'verification.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'PREPARE_REQUIRED'):a.prepare_storage(self.root,self.folder,self.approval)
        self.assertEqual((self.folder/'verification.json').read_bytes(),original)
        self.x.h.helper.git('add','-A');self.x.commit('original')
        bad=copy.deepcopy(self.approval);bad['hosts'][0].pop('snapshot_storage_capable')
        with self.assertRaisesRegex(ValueError,'PREPARE_REQUIRED'):a.prepare_storage(self.root,self.folder,bad)
        self.assertEqual((self.folder/'verification.json').read_bytes(),original)

    def test_typed_static_fact_preserves_observation_and_registration_times(self):
        self.prepare();doc=self.x.plan();row=next(x for x in doc['items'] if x['mode']=='manual');stamp,head=v.context(self.root,self.folder,doc)
        v.record(self.root,self.folder,row['id'],'passed',stamp,head,'Synthetic static exclusion of influence, no runtime execution','fixture diff',evidence_kind='static_analysis',observed_at='2026-01-01T00:00:00+00:00')
        fact=self.x.plan()['items'][doc['items'].index(row)]['history'][-1]
        self.assertEqual(fact['evidence_kind'],'static_analysis');self.assertNotEqual(fact['observed_at'],fact['at'])
        self.assertEqual(fact['tested_revision'],head)

    def test_typed_fact_invalid_time_refuses(self):
        self.prepare();doc=self.x.plan();row=next(x for x in doc['items'] if x['mode']=='manual');stamp,head=v.context(self.root,self.folder,doc)
        original=(self.folder/'verification.json').read_bytes()
        for time in ['3000-01-01T00:00:00+00:00','2026-01-01']:
            with self.assertRaisesRegex(ValueError,'observation time'):v.record(self.root,self.folder,row['id'],'passed',stamp,head,'actual','evidence',evidence_kind='static_analysis',observed_at=time)
        self.assertEqual((self.folder/'verification.json').read_bytes(),original)

    def test_same_context_correction_keeps_negative_without_new_execution(self):
        _,negative=self.negative();before=self.x.plan();count=self.x.h.counter.read_text();request,review=self.correction(negative)
        a.apply_assessment(self.root,self.folder,request,review)
        after=self.x.plan();self.assertTrue(a.resolve_claims(self.root,self.folder)['acceptance_eligible'])
        self.assertEqual(after['acceptance']['events'][:-1],before['acceptance']['events']);self.assertEqual(after['items'],before['items'])
        self.assertEqual(self.x.h.counter.read_text(),count)

    def test_old_unclassified_negative_cannot_be_corrected(self):
        self.prepare();request=self.x.capture();review=self.review(request,'partial');a.apply_assessment(self.root,self.folder,request,review)
        request,correction=self.correction(review)
        with self.assertRaisesRegex(ValueError,'classified review error'):a.apply_assessment(self.root,self.folder,request,correction)

    def test_observed_failure_classification_cannot_be_corrected(self):
        _,old=self.negative('observed_failure');request,review=self.correction(old)
        with self.assertRaisesRegex(ValueError,'classified review error'):a.apply_assessment(self.root,self.folder,request,review)

    def test_changed_scope_or_different_context_cannot_be_corrected(self):
        _,old=self.negative();request,review=self.correction(old)
        review['review_context']['context_id']='another actual context'
        with self.assertRaisesRegex(ValueError,'REVIEW_NOT_INDEPENDENT'):a.apply_assessment(self.root,self.folder,request,review)
        request,review=self.correction(old);review['barrier_resolutions'][0]['original_scope']['required_scope']='modified original'
        with self.assertRaisesRegex(ValueError,'original reasoning'):a.apply_assessment(self.root,self.folder,request,review)

    def test_readiness_uses_same_decoded_profile(self):
        self.prepare()
        import verification_policy as policy
        status=policy.delivery_readiness(self.root,self.folder.name)
        self.assertEqual(status['route'],'acceptance_v1');self.assertNotIn('explicit_schema7_preparation',status['missing'])

    def test_prepare_refuses_completed_work(self):
        self.x.change('spec/requirements.json',lambda d:d['feature'].update(status='complete'))
        with self.assertRaises(ValueError):self.prepare()

    def test_fact_failure_cannot_be_relabelled_as_review_error(self):
        self.prepare();doc=self.x.plan();row=next(x for x in doc['items'] if x['mode']=='manual');stamp,head=v.context(self.root,self.folder,doc)
        v.record(self.root,self.folder,row['id'],'failed',stamp,head,'Actual synthetic failure','fixture failure')
        stamp,head=v.context(self.root,self.folder,self.x.plan())
        v.record(self.root,self.folder,row['id'],'passed',stamp,head,'Later synthetic positive','fixture later')
        request=self.x.capture();negative=self.review(request,'partial','evidence_gap');a.apply_assessment(self.root,self.folder,request,negative)
        request,review=self.correction(negative)
        with self.assertRaisesRegex(ValueError,'failed/unavailable'):a.apply_assessment(self.root,self.folder,request,review)

    def test_new_world_cannot_use_same_input_correction(self):
        _,old=self.negative();self.x.change('spec/requirements.json',lambda d:d['feature'].update(status_note='New authority input'))
        request,review=self.correction(old)
        with self.assertRaisesRegex(ValueError,'same actual context'):a.apply_assessment(self.root,self.folder,request,review)

    def test_original_missing_or_changed_refuses(self):
        self.prepare();doc=self.x.plan();doc['storage']['origin']['sha256']='0'*64
        (self.folder/'verification.json').write_text(json.dumps(codec.pack(doc)))
        with self.assertRaisesRegex(ValueError,'ORIGIN_UNAVAILABLE'):v.load_plan(self.folder)

    def test_old_reader_rejects_packed_format(self):
        self.prepare();raw=json.loads((self.folder/'verification.json').read_text())
        self.assertEqual(raw['schema_version'],8)
        # Exact old schema6/7 document surface is intentionally absent.
        self.assertNotIn('acceptance_contract',raw)
        self.assertNotIn('items',raw)
        self.assertNotIn('feature_id',raw)

    def test_changed_actual_reviewer_context_is_not_a_correction(self):
        _,old=self.negative();request,review=self.correction(old)
        proofpath=self.root/review['reviewer_evidence_ref']['path'];proof=json.loads(proofpath.read_text());proof['context_id']='different actual context'
        proofpath.write_text(json.dumps(proof));review['reviewer_evidence_ref']['sha256']=a.byte_hash(proofpath.read_bytes());review['review_context']['context_id']=proof['context_id']
        with self.assertRaisesRegex(ValueError,'same actual context'):a.apply_assessment(self.root,self.folder,request,review)

    def test_new_preparation_can_explicitly_choose_storage_without_migrating_old(self):
        # The main preparation entry is idempotent for an already prepared old contract.
        original=(self.folder/'verification.json').read_bytes()
        approval=dict(self.x.approval,snapshot_storage=1)
        approval['hosts']=[dict(approval['hosts'][0],snapshot_storage_capable=True)]
        a.prepare(self.root,self.folder,approval)
        self.assertEqual((self.folder/'verification.json').read_bytes(),original)

    def test_typed_fact_does_not_silently_enable_for_old_contract(self):
        doc=self.x.plan();row=next(x for x in doc['items'] if x['mode']=='manual');stamp,head=v.context(self.root,self.folder,doc)
        with self.assertRaisesRegex(ValueError,'schema8'):v.record(self.root,self.folder,row['id'],'passed',stamp,head,'static','diff',evidence_kind='static_analysis',observed_at='2026-01-01T00:00:00Z')
        self.assertEqual(self.x.plan(),doc)


    def test_unscoped_profile_cannot_become_scoped_by_its_envelope_number(self):
        import verification_policy as policy
        self.prepare();self.x.change('spec/requirements.json',lambda d:d['feature'].update(verification_policy=1))
        before=(self.folder/'verification.json').read_bytes();count=self.x.h.counter.read_text()
        with self.assertRaisesRegex(ValueError,'DELIVERY_PREPARE_REQUIRED'):policy.require_execution_route(self.root,self.folder.name)
        view=policy.delivery_readiness(self.root,self.folder.name)
        self.assertEqual(view['state'],'preparation_required');self.assertIn('explicit_schema7_preparation',view['missing'])
        self.assertEqual((self.folder/'verification.json').read_bytes(),before);self.assertEqual(self.x.h.counter.read_text(),count)


class ScopedStorageTests(unittest.TestCase):
    def setUp(self):
        import test_verification_policy
        import check_runs
        self.p=test_verification_policy.VerificationPolicyTests();self.p.setUp();self.addCleanup(self.p.doCleanups)
        self.p.root=self.p.root.resolve();self.p.folder=self.p.folder.resolve()
        self.p.persist();check_runs.prepare(self.p.root,'FEAT-001',[{'name':'unit','test_ids':['UT-1']}],'Explicit fixture preparation')
        v.sync(self.p.root,self.p.folder);self.p.h.git('add','-A');self.p.h.git('commit','-qm','Original sources')
        self.approval={'active_features':['FEAT-001'],'snapshot_storage':1,'hosts':[{'name':'synthetic capable host','schema6_capable':True,'verification_policy_capable':True,'snapshot_storage_capable':True}],'evidence':'Explicit storage fixture opt-in'}

    def test_fresh_scoped_storage_uses_real_gate_and_same_resolver(self):
        import verification_policy as policy
        import check_runs
        doc=a.prepare(self.p.root,self.p.folder,self.approval)
        self.assertEqual(doc['schema_version'],8);self.assertEqual(a.profile(doc),7)
        self.assertEqual(policy.delivery_readiness(self.p.root,'FEAT-001')['state'],'structurally_ready')
        policy.require_execution_route(self.p.root,'FEAT-001')
        self.assertEqual(check_runs.run(self.p.root,'FEAT-001'),0)
        request,_=a.capture_assessment(self.p.root,self.p.folder)
        self.assertTrue(request['fact_refs']);self.assertFalse(a.resolve_claims(self.p.root,self.p.folder)['acceptance_eligible'])
        # Generated views use the same expanded contract; no additional physical gate.
        count=(self.p.folder/'check-head.json').read_bytes()
        a.project_views(self.p.root,self.p.folder)
        self.assertEqual((self.p.folder/'check-head.json').read_bytes(),count)

    def test_missing_capability_refuses_without_rewriting_original(self):
        before=(self.p.folder/'verification.json').read_bytes();self.approval['hosts'][0].pop('snapshot_storage_capable')
        with self.assertRaisesRegex(ValueError,'PREPARE_REQUIRED'):a.prepare(self.p.root,self.p.folder,self.approval)
        self.assertEqual((self.p.folder/'verification.json').read_bytes(),before)
