import json
import unittest
from unittest.mock import patch
import test_verification
from stage_cost import location,mutate,status,usage


class StageCostTests(unittest.TestCase):
    def setUp(self):
        self.helper=test_verification.VerificationTests();self.helper.setUp();self.addCleanup(self.helper.doCleanups)
        self.root,self.folder=self.helper.root,self.helper.folder
        (self.root/'.agent-workflow/.gitignore').write_text('/scratch/\n')
        _,_,self.path=location(self.root,'FEAT-001')

    def test_serial_intervals_separate_waits_and_unknown_usage_without_changing_acceptance(self):
        before=(self.folder/'verification.json').read_bytes()
        with patch('stage_cost.time.monotonic',return_value=100),patch('stage_cost.time.time',return_value=1000):
            mutate(self.root,self.folder,self.path,'start','test')
        with patch('stage_cost.time.monotonic',return_value=112),patch('stage_cost.time.time',return_value=1012):
            mutate(self.root,self.folder,self.path,'stop')
            mutate(self.root,self.folder,self.path,'start','waiting')
        with patch('stage_cost.time.monotonic',return_value=117),patch('stage_cost.time.time',return_value=1017):
            mutate(self.root,self.folder,self.path,'stop')
        result=status(self.root,'FEAT-001')
        self.assertEqual(result['wall_seconds_by_category']['test'],12)
        self.assertEqual(result['wall_seconds_by_category']['waiting'],5)
        self.assertIsNone(result['intervals'][0]['usage']['tokens']);self.assertIsNone(result['intervals'][0]['usage']['cost'])
        self.assertEqual(before,(self.folder/'verification.json').read_bytes())

    def test_account_context_counts_overlap_and_clock_change_are_not_measurement(self):
        for measured in ({'scope':'account','source':'quota','tokens':{'output':100}},
                         {'scope':'session','source':'context window','tokens':{'input':240000}},
                         {'scope':'interval','source':'fixture','tokens':{'output':True}}):
            with self.assertRaises(ValueError):usage(measured)
        mutate(self.root,self.folder,self.path,'start','verify')
        with self.assertRaisesRegex(ValueError,'already active'):mutate(self.root,self.folder,self.path,'start','test')
        doc=json.loads(self.path.read_text());doc['active']['monotonic']=10**20;self.path.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError,'clock/boot'):mutate(self.root,self.folder,self.path,'stop')
        self.assertIsNotNone(json.loads(self.path.read_text())['active'])

    def test_status_is_read_only_and_nonignored_telemetry_is_optional_unavailable(self):
        self.assertFalse(self.path.exists());self.assertEqual(status(self.root,'FEAT-001')['interval_count'],0);self.assertFalse(self.path.exists())
        (self.root/'.agent-workflow/.gitignore').unlink()
        with self.assertRaisesRegex(ValueError,'Git ignored'):location(self.root,'FEAT-001')

    def test_explicit_provider_usage_keeps_currency_scope_and_source(self):
        measured={'scope':'interval','source':'synthetic provider run output','tokens':{'output':50},'cost':{'value':0.02,'currency':'USD'}}
        mutate(self.root,self.folder,self.path,'start','record_maintenance')
        mutate(self.root,self.folder,self.path,'stop',measured=measured)
        result=status(self.root,'FEAT-001');self.assertEqual(result['intervals'][0]['usage'],measured)

    def test_optional_journal_does_not_contend_with_verification_lock(self):
        import fcntl
        scratch=self.root/'.agent-workflow/scratch';scratch.mkdir(exist_ok=True)
        with (scratch/'verification-FEAT-001.lock').open('a') as stream:
            fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            mutate(self.root,self.folder,self.path,'start','waiting')
            mutate(self.root,self.folder,self.path,'stop')
        self.assertEqual(status(self.root,'FEAT-001')['interval_count'],1)
