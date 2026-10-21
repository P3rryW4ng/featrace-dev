import contextlib
import hashlib
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


class StreamingPrivacyTests(unittest.TestCase):
    setUp = OutputPrivacyTests.setUp
    git = OutputPrivacyTests.git
    scan = OutputPrivacyTests.scan
    # Reuse the setup/helpers, not a second copy of the inherited test methods.
    def large_json(self, path, size):
        row=b'  {"path":"synthetic/file.kt","sha256":"'+b'a'*64+b'"},\n'
        count=(size-8)//len(row)
        with path.open('wb') as stream:
            stream.write(b'[\n')
            while count:
                n=min(count,2048);stream.write(row*n);count-=n
            stream.write(b' '*(size-stream.tell()-6)+b'null]\n')
        self.assertEqual(path.stat().st_size,size)

    def test_58mb_record_full_and_staged_detect_tail_without_mutation(self):
        p=self.root/'large.json';self.large_json(p,58_328_693);self.git('add','large.json')
        def sha():
            h=hashlib.sha256()
            with p.open('rb') as f:
                for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
            return h.digest()
        before=sha();index=(self.root/'.git/index').read_bytes()
        for staged in (False,True):
            r,c=self.scan('large.json',staged=staged,known_name='scratch/known.json')
            self.assertEqual(c,0,r);self.assertEqual(r['status'],'no_matches')
        self.assertEqual(before,sha());self.assertEqual(index,(self.root/'.git/index').read_bytes())
        with p.open('ab') as f:f.write(self.marker.encode()+b'\n')
        self.git('add','large.json')
        for staged in (False,True):
            r,c=self.scan('large.json',staged=staged,known_name='scratch/known.json')
            self.assertEqual(c,1);self.assertTrue(any(f['confidence']=='known_value' for f in r['findings']))
            self.assertNotIn(self.marker,json.dumps(r))

    def test_large_old_and_new_blobs_scan_only_new_lines(self):
        p=self.root/'history.json';self.large_json(p,18*1024*1024)
        with p.open('ab') as f:f.write(b'userId: old_private_fixture\n')
        self.git('add','history.json');self.git('commit','-qm','Large synthetic history')
        with p.open('ab') as f:f.write(b'new safe summary\n')
        self.git('add','history.json')
        r,c=self.scan('history.json',staged=True);self.assertEqual(c,0,r)
        with p.open('ab') as f:f.write(b'uid: new_private_fixture\n')
        self.git('add','history.json')
        r,c=self.scan('history.json',staged=True);self.assertEqual(c,1)
        self.assertEqual(len(r['findings']),1)

    def test_known_value_across_blocks_lines_and_json_escapes(self):
        marker='甲\n乙\n丙'
        (self.root/'scratch/known.json').write_text(json.dumps({'values':[{'kind':'contact','value':marker}]}))
        (self.root/'lines').write_text('safe\n甲\n乙\n丙\n')
        (self.root/'escaped').write_text(json.dumps({'body':marker}))
        for name in ('lines','escaped'):
            self.git('add',name)
            for staged in (False,True):
                with patch.object(privacy,'SCAN_BLOCK_CHARS',4):
                    r,c=self.scan(name,staged=staged,known_name='scratch/known.json')
                self.assertEqual(c,1,r);self.assertNotIn(marker,json.dumps(r))
                if name=='lines':self.assertEqual((r['findings'][0]['line'],r['findings'][0]['column']),(2,1))

    def test_no_synthetic_final_newline_in_staged_known_match(self):
        (self.root/'scratch/known.json').write_text(json.dumps({'values':[{'kind':'contact','value':self.marker+'\n'}]}))
        (self.root/'no-lf').write_text(self.marker);self.git('add','no-lf')
        for staged in (False,True):
            r,c=self.scan('no-lf',staged=staged,known_name='scratch/known.json');self.assertEqual(c,0,r)

    def test_truncation_still_validates_late_encoding_and_binary(self):
        for suffix in (b'\xff',b'\x00'):
            (self.root/'bad-tail').write_bytes((b'uid: private_fixture\n'*200)+b'safe\n'*100+suffix)
            for staged in (False,True):
                self.git('add','bad-tail')
                with patch.object(privacy,'SCAN_BLOCK_CHARS',64),patch.object(privacy,'MAX_FINDINGS',2):
                    r,c=self.scan('bad-tail',staged=staged)
                self.assertEqual(c,2);self.assertEqual(r['status'],'unavailable')

    def test_total_stream_budget_refuses_and_git_process_is_reaped(self):
        (self.root/'budget').write_text('safe\n'*1000);self.git('add','budget')
        spawned=[];popen=privacy.subprocess.Popen
        def track(*args,**kwargs):
            proc=popen(*args,**kwargs);spawned.append(proc);return proc
        for staged in (False,True):
            with patch.object(privacy,'MAX_STREAM_BYTES',1024),patch.object(privacy.subprocess,'Popen',track):
                r,c=self.scan('budget',staged=staged)
            self.assertEqual(c,2);self.assertEqual(r['targets'][0]['reason'],'input_too_large')
            self.assertTrue(all(p.poll() is not None for p in spawned))

    def test_staged_index_and_known_input_drift_refuse(self):
        p=self.root/'drift';p.write_text('safe\n');self.git('add','drift')
        original=privacy.collect;count=[0]
        def changed(*args):
            count[0]+=1
            if count[0]==2:
                p.write_text(self.marker+'\n');self.git('add','drift')
            return original(*args)
        with patch.object(privacy,'collect',changed):r,c=self.scan('drift',staged=True)
        self.assertEqual(c,2);self.assertEqual(r['reason'],'input_changed')
        count=[0]
        def known_changed(*args):
            count[0]+=1
            if count[0]==2:(self.root/'scratch/known.json').write_text('{"values":[]}')
            return original(*args)
        with patch.object(privacy,'collect',known_changed):
            with self.assertRaisesRegex(privacy.ScanError,'known_values_changed'):
                self.scan('drift',known_name='scratch/known.json')

    def test_column_positions_and_noninitial_bom_are_not_rebased(self):
        p=self.root/'unicode';p.write_text('safe\n\ufeff😀 '+self.marker+'\n');self.git('add','unicode')
        for staged in (False,True):
            with patch.object(privacy,'SCAN_BLOCK_CHARS',8):r,c=self.scan('unicode',staged=staged,known_name='scratch/known.json')
            self.assertEqual(c,1);self.assertEqual((r['findings'][0]['line'],r['findings'][0]['column']),(2,4))

    def test_dense_long_line_keeps_only_bounded_findings(self):
        (self.root/'dense').write_text(('uid: fixture_private, '*100000)+'\n')
        r,c=self.scan('dense');self.assertEqual(c,1)
        self.assertEqual(len(r['findings']),privacy.MAX_FINDINGS);self.assertTrue(r['targets'][0]['positions_truncated'])


    def test_read_error_after_partial_stream_is_unavailable_not_clean(self):
        (self.root/'read-error').write_text('safe\n')
        original=privacy.stream_lines
        def unreadable(stream,state,key,**kwargs):
            yield 'safe\n'
            raise OSError('SYNTHETIC_PRIVATE_ERROR_MUST_NOT_ECHO')
        with patch.object(privacy,'stream_lines',unreadable):r,c=self.scan('read-error')
        self.assertEqual(c,2);self.assertEqual(r['targets'][0]['reason'],'file_unavailable')
        self.assertNotIn('SYNTHETIC_PRIVATE_ERROR',json.dumps(r))


    def test_new_empty_file_and_mode_only_change_are_not_false_unavailable(self):
        p=self.root/'empty';p.write_bytes(b'');self.git('add','empty')
        r,c=self.scan('empty',staged=True);self.assertEqual(c,0,r)
        self.git('commit','-qm','Synthetic empty file')
        self.git('update-index','--chmod=+x','empty')
        r,c=self.scan('empty',staged=True);self.assertEqual(c,0,r)

    def test_missing_diff_for_changed_blob_is_not_clean(self):
        p=self.root/'missing-diff';p.write_text('safe\n');self.git('add','missing-diff');self.git('commit','-qm','Synthetic baseline')
        p.write_text(self.marker+'\n');self.git('add','missing-diff')
        original=privacy.git_lines
        def omit(root,state,key,*args,**kwargs):
            if key=='diff':
                state[key]={'sha256':hashlib.sha256(b'').hexdigest(),'bytes':0}
                return
            yield from original(root,state,key,*args,**kwargs)
        with patch.object(privacy,'git_lines',omit):r,c=self.scan('missing-diff',staged=True)
        self.assertEqual(c,2);self.assertEqual(r['targets'][0]['reason'],'staged_diff_unavailable')

    def test_known_values_never_stitch_across_unchanged_staged_lines(self):
        marker='ALPHA\nOMEGA'
        (self.root/'scratch/known.json').write_text(json.dumps({'values':[{'kind':'contact','value':marker}]}))
        p=self.root/'hunks';p.write_text('old1\nunchanged\nold2\n');self.git('add','hunks');self.git('commit','-qm','Synthetic disjoint hunks')
        p.write_text('ALPHA\nunchanged\nOMEGA\n');self.git('add','hunks')
        with patch.object(privacy,'SCAN_BLOCK_CHARS',4):r,c=self.scan('hunks',staged=True,known_name='scratch/known.json')
        self.assertEqual(c,0,r)
