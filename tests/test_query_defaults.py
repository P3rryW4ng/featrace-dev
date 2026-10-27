"""CLI page units: character detail versus row-based queries."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
import test_task_workflow as fixture
w=fixture.w

class QueryDefaultTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.TaskWorkflowTests(methodName='runTest');self.f.setUp();self.addCleanup(self.f.doCleanups)

    def cli(self,*args):
        return subprocess.run([sys.executable,str(Path(w.__file__)),*args],capture_output=True,text=True)

    def test_default_detail_recovers_ordinary_request_without_twenty_character_pages(self):
        f=self.f;doc=f.doc();doc['request']='Keep original business behavior; change only the selected display label. '*8;w.save(f.root,doc)
        before=w.task_path(f.root,f.ident).read_bytes()
        result=self.cli('detail',str(f.root),f.ident,'--section','request');self.assertEqual(result.returncode,0,result.stdout)
        out=json.loads(result.stdout);self.assertTrue(out['complete']);self.assertEqual(json.loads(out['text']),doc['request']);self.assertIsNone(out['next_offset'])
        explicit=self.cli('detail',str(f.root),f.ident,'--section','request','--limit','20');self.assertEqual(explicit.returncode,0,explicit.stdout)
        small=json.loads(explicit.stdout);self.assertEqual(len(small['text']),20);self.assertEqual(small['next_offset'],20);self.assertFalse(small['complete'])
        self.assertEqual(before,w.task_path(f.root,f.ident).read_bytes());self.assertFalse((f.root/'run-count').exists())

    def test_row_queries_keep_twenty_item_default(self):
        f=self.f
        for i in range(24):w.begin(f.root,'PAGE-'+str(i),'Synthetic draft for row pagination')
        result=self.cli('list',str(f.root));self.assertEqual(result.returncode,0,result.stdout)
        out=json.loads(result.stdout);self.assertEqual(len(out['items']),20);self.assertEqual(out['next_offset'],20)
        self.assertFalse((f.root/'run-count').exists())

    def test_invalid_explicit_detail_limit_still_refuses_without_writes(self):
        f=self.f;before=w.task_path(f.root,f.ident).read_bytes();result=self.cli('detail',str(f.root),f.ident,'--section','request','--limit','0')
        self.assertEqual(result.returncode,2);self.assertEqual(json.loads(result.stdout)['reason'],'PAGE_INVALID');self.assertEqual(before,w.task_path(f.root,f.ident).read_bytes())
