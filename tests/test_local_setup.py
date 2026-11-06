import json
import fcntl
import signal
import sys
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
import test_task_workflow as fixture
w=fixture.w

class LocalSetupTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.TaskWorkflowTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.root=self.f.root
        self.config=w.task_policy.load(self.root)

    def prepare(self,root=None):
        return w.task_policy.prepare(root or self.root,self.config,w.git)

    def test_only_local_exclude_changes_and_policy_is_ignored(self):
        before=(self.root/'.gitignore').read_bytes()
        self.prepare()
        self.assertEqual(before,(self.root/'.gitignore').read_bytes())
        self.assertIn('/.featrace-policy.json',(self.root/'.git/info/exclude').read_text())
        self.assertNotIn(b'.featrace',self.f.git('status','--porcelain'))

    def test_linked_worktree_uses_git_common_metadata(self):
        other=self.root.parent/(self.root.name+'-linked')
        self.f.git('worktree','add','-q','--detach',str(other),'HEAD')
        self.addCleanup(lambda:self.f.git('worktree','remove','--force',str(other)))
        self.prepare(other)
        self.assertFalse((other/'.gitignore').read_text().find('Featrace')>=0)
        self.assertTrue((other/'.featrace-policy.json').exists())

    def test_tracked_policy_refuses_without_shared_mutation(self):
        self.f.git('add','-f','.featrace-policy.json')
        with self.assertRaisesRegex(ValueError,'TRACKED'):self.prepare()

    def test_negation_refuses_and_restores_local_exclude(self):
        (self.root/'.gitignore').write_text('!.featrace-policy.json\n')
        exclude=self.root/'.git/info/exclude';before=exclude.read_bytes()
        with self.assertRaisesRegex(ValueError,'IGNORE_CONFLICT'):self.prepare()
        self.assertEqual(exclude.read_bytes(),before)

    def test_lock_and_symlink_refuse(self):
        lock=self.root/'.git/info/featrace-setup.lock';lock.write_text('other writer')
        with lock.open('a+b') as stream:
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError,'SETUP_BUSY'):self.prepare()
        exclude=self.root/'.git/info/exclude';exclude.unlink();exclude.symlink_to(self.root/'rules.md')
        with self.assertRaisesRegex(ValueError,'LINK_REFUSED'):self.prepare()

    def test_failed_policy_write_restores_exclusion(self):
        exclude=self.root/'.git/info/exclude';exclude.write_text('# preserve\n');before=exclude.read_bytes()
        write=w.task_policy.write
        def fail_dest(p,data):
            if p.name=='.featrace-policy.json':raise OSError('synthetic')
            return write(p,data)
        with patch.object(w.task_policy,'write',side_effect=fail_dest):
            with self.assertRaises(OSError):self.prepare()
        self.assertEqual(exclude.read_bytes(),before)

    def test_sigkill_during_policy_setup_does_not_leave_busy_lock(self):
        core=str(Path(w.__file__).parent)
        script="import sys,os,signal,json;sys.path.insert(0,sys.argv[1]);import task_workflow as w;from pathlib import Path;r=Path(sys.argv[2]);config=w.task_policy.load(r);old=w.task_policy.write;w.task_policy.write=lambda p,data: os.kill(os.getpid(),signal.SIGKILL) if p.name==w.task_policy.NAME else old(p,data);w.task_policy.prepare(r,config,w.git)"
        run=subprocess.run([sys.executable,'-c',script,core,str(self.root)],capture_output=True)
        self.assertEqual(run.returncode,-signal.SIGKILL)
        self.prepare()
        self.assertEqual(w.task_policy.load(self.root),self.config)
