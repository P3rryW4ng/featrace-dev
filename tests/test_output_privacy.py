import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).parents[1]/'skills/dev/core/scripts/output_privacy.py'
spec = importlib.util.spec_from_file_location('privacy', SCRIPT)
privacy = importlib.util.module_from_spec(spec); spec.loader.exec_module(privacy)


class OutputPrivacyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
        self.git('init');self.git('config','user.name','Synthetic');self.git('config','user.email','fixture@example.invalid')
        (self.root/'.gitignore').write_text('/scratch/\n');(self.root/'scratch').mkdir()
        self.marker='SYNTHETIC_ACCOUNT_7613'
        (self.root/'scratch/known.json').write_text(json.dumps({'values':[{'kind':'account_identifier','value':self.marker}]}))

    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.root),*args],stderr=subprocess.DEVNULL)

    def scan(self,*names,**kwargs):
        return privacy.scan(self.root,list(names),**kwargs)

    def test_known_values_in_review_and_receipt_prose_only_report_positions(self):
        (self.root/'review.json').write_text(json.dumps({'assessment':'Private source account '+self.marker}))
        before=(self.root/'review.json').read_bytes()
        r,c=self.scan('review.json',known_name='scratch/known.json')
        self.assertEqual(c,1);self.assertEqual(r['findings'][0]['confidence'],'known_value')
        self.assertEqual(r['findings'][0]['target'],1)
        self.assertNotIn(self.marker,json.dumps(r));self.assertNotIn('review.json',json.dumps(r))
        self.assertEqual(before,(self.root/'review.json').read_bytes())

    def test_known_markers_match_json_escape_variant_without_echo(self):
        marker='SYNTHETIC_账号_123'
        (self.root/'scratch/known.json').write_text(json.dumps({'values':[{'kind':'account_identifier','value':marker}]}))
        (self.root/'review.json').write_text(json.dumps({'body':marker},ensure_ascii=True))
        r,c=self.scan('review.json',known_name='scratch/known.json');self.assertEqual(c,1)
        self.assertNotIn(marker,json.dumps(r));self.assertNotIn('\\u8d26',json.dumps(r))

    def test_labeled_identifiers_and_credentials_are_candidates_not_authority(self):
        (self.root/'report.md').write_text('userId: 987654321\nAuthorization: Bearer synthetic_test_credential_abcdef\n')
        r,c=self.scan('report.md');self.assertEqual(c,1)
        self.assertTrue(all(f['confidence']=='candidate' for f in r['findings']))
        self.assertNotIn('987654321',json.dumps(r));self.assertNotIn('synthetic_test_',json.dumps(r))
        self.assertEqual({x['line'] for x in r['findings']},{1,2})

    def test_placeholders_hashes_and_unlabeled_unknown_values_do_not_claim_safe(self):
        (self.root/'clean.json').write_text(json.dumps({'userId':'[REDACTED]','access_token':'<token>',
            'deviceSerial':'*****','commit':'a'*40,'sha256':'b'*64,'testCount':21,'body':self.marker}))
        r,c=self.scan('clean.json');self.assertEqual(c,0);self.assertEqual(r['status'],'no_matches')
        self.assertIn('not privacy approval',r['note'])
        # Unknown unlabeled identifiers require actual known-value input, never fake coverage.
        r,c=self.scan('clean.json',known_name='scratch/known.json');self.assertEqual(c,1)

    def test_staged_only_new_lines_ignore_unchanged_and_removed_sensitive_history(self):
        p=self.root/'report.md';p.write_text('userId: old_private_identity\nremove access_token: previous_private_token\nsummary old\n')
        self.git('add','.gitignore','report.md');self.git('commit','-m','baseline')
        p.write_text('userId: old_private_identity\nsummary new\n');self.git('add','report.md')
        r,c=self.scan('report.md',staged=True);self.assertEqual(c,0)
        p.write_text(p.read_text()+'accountId: new_private_identity\n');self.git('add','report.md')
        r,c=self.scan('report.md',staged=True);self.assertEqual(c,1)
        self.assertEqual({f['line'] for f in r['findings']},{3})

    def test_worktree_leak_not_staged_is_not_misreported_as_index_content(self):
        p=self.root/'report.md';p.write_text('safe summary\n');self.git('add','.gitignore','report.md');self.git('commit','-m','baseline')
        p.write_text(self.marker);r,c=self.scan('report.md',staged=True,known_name='scratch/known.json');self.assertEqual(c,0)
        r,c=self.scan('report.md',known_name='scratch/known.json');self.assertEqual(c,1)

    def test_staged_new_file_with_literal_pathspec_name_is_checked(self):
        p=self.root/'[private].md';p.write_text(self.marker);self.git('add','--','[private].md')
        r,c=self.scan('[private].md',staged=True,known_name='scratch/known.json');self.assertEqual(c,1)
        self.assertEqual(r['targets'][0]['scope'],'staged_additions')

    def test_binary_git_attribute_does_not_hide_valid_text_additions(self):
        (self.root/'.gitattributes').write_text('report.md -diff\n')
        (self.root/'report.md').write_text('userId: synthetic_account_123\n')
        self.git('add','.gitattributes','report.md')
        r,c=self.scan('report.md',staged=True);self.assertEqual(c,1)
        self.assertEqual(r['findings'][0]['line'],1)

    def test_unicode_separator_remains_staged_file_content(self):
        (self.root/'report.md').write_text('safe\u2028'+self.marker+'\n')
        self.git('add','report.md')
        r,c=self.scan('report.md',staged=True,known_name='scratch/known.json')
        self.assertEqual(c,1);self.assertEqual(r['findings'][0]['line'],1)

    def test_git_interhunk_configuration_cannot_shift_locations(self):
        p=self.root/'report.md';p.write_text('old\n2\n3\n4\n5\nold\n')
        self.git('add','report.md');self.git('commit','-m','base')
        self.git('config','diff.interHunkContext','10')
        p.write_text('new\n2\n3\n4\n5\nuserId: synthetic_account_123\n');self.git('add','report.md')
        r,c=self.scan('report.md',staged=True);self.assertEqual(c,1)
        self.assertEqual(r['findings'][0]['line'],6)

    def test_fifo_returns_unavailable_without_waiting_for_writer(self):
        import os
        os.mkfifo(self.root/'pipe')
        run=subprocess.run([sys.executable,str(SCRIPT),str(self.root),'--file','pipe'],capture_output=True,timeout=2)
        self.assertEqual(run.returncode,2)
        self.assertEqual(json.loads(run.stdout)['status'],'unavailable')

    def test_staged_deleted_file_adds_no_new_exposure(self):
        p=self.root/'report.md';p.write_text('userId: old_identity\n');self.git('add','report.md');self.git('commit','-m','base')
        self.git('rm','report.md');r,c=self.scan('report.md',staged=True);self.assertEqual(c,0)
        self.assertEqual(r['targets'][0]['scope'],'staged_deletion')

    def test_partial_unreadable_binary_or_symlink_targets_are_unavailable(self):
        (self.root/'binary').write_bytes(b'\x00opaque')
        (self.root/'link').symlink_to(self.root/'scratch/known.json')
        (self.root/'fine').write_text('safe')
        for name in ['binary','link','missing','../outside']:
            r,c=self.scan('fine',name);self.assertEqual(c,2);self.assertEqual(r['status'],'unavailable')

    def test_known_file_must_be_ignored_and_errors_never_echo_bad_values(self):
        (self.root/'notignored.json').write_text(json.dumps({'values':[{'kind':'credential','value':self.marker}]}))
        with self.assertRaisesRegex(privacy.ScanError,'ignored'):
            self.scan('notignored.json',known_name='notignored.json')
        (self.root/'scratch/known.json').write_text(json.dumps({'values':[{'kind':self.marker,'value':'anything'}]}))
        with self.assertRaises(privacy.ScanError) as e:self.scan('notignored.json',known_name='scratch/known.json')
        self.assertNotIn(self.marker,str(e.exception))

    def test_changes_during_scan_refuse_clean_result(self):
        (self.root/'report.md').write_text('safe');original=privacy.collect;count=[0]
        def collect(*args):
            count[0]+=1
            if count[0]==2:(self.root/'report.md').write_text(self.marker)
            return original(*args)
        with patch.object(privacy,'collect',collect):r,c=self.scan('report.md')
        self.assertEqual(c,2);self.assertEqual(r['reason'],'input_changed')

    def test_locations_are_bounded_and_hidden_values_cannot_leak_in_paths(self):
        (self.root/(self.marker+'.txt')).write_text((self.marker+'\n')*200)
        r,c=self.scan(self.marker+'.txt',known_name='scratch/known.json');self.assertEqual(c,1)
        self.assertTrue(r['targets'][0]['positions_truncated']);self.assertEqual(len(r['findings']),100)
        self.assertNotIn(self.marker,json.dumps(r))

    def test_cli_exit_codes_and_readonly_index_and_files(self):
        p=self.root/'review.json';p.write_text(json.dumps({'evidence':self.marker}));self.git('add','review.json')
        original=p.read_bytes();index=(self.root/'.git/index').read_bytes()
        x=subprocess.run([sys.executable,'-B',str(SCRIPT),str(self.root),'--staged','--file','review.json','--known-values','scratch/known.json'],capture_output=True,text=True)
        self.assertEqual(x.returncode,1);self.assertNotIn(self.marker,x.stdout+x.stderr)
        self.assertEqual(p.read_bytes(),original);self.assertEqual((self.root/'.git/index').read_bytes(),index)
        x=subprocess.run([sys.executable,'-B',str(SCRIPT),str(self.root),'--bad',self.marker],capture_output=True,text=True)
        self.assertEqual(x.returncode,2);self.assertNotIn(self.marker,x.stdout+x.stderr)

    def test_oversized_text_is_unavailable_without_partial_clean(self):
        (self.root/'large').write_text('x'*(privacy.MAX_BYTES+1))
        r,c=self.scan('large');self.assertEqual(c,2);self.assertEqual(r['targets'][0]['reason'],'input_too_large')
