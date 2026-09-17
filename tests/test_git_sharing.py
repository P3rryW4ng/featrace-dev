from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/dev/core/scripts'

class GitSharingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'repo'; self.root.mkdir()
        self.git('init', '-q')

    def git(self, *args, root=None):
        return subprocess.run(['git','-C',str(root or self.root),*args], capture_output=True, text=True, check=True).stdout

    def setup_ignore(self):
        return subprocess.run([sys.executable,str(SCRIPTS/'setup-workflow-git.py'),str(self.root)], capture_output=True,text=True)

    def ignored(self, path):
        return subprocess.run(['git','-C',str(self.root),'check-ignore','-q',path]).returncode == 0

    def test_scope_and_idempotence(self):
        work=self.root/'.agent-workflow';work.mkdir();p=work/'.gitignore';p.write_bytes(b'# existing\r\n/custom-private')
        self.assertEqual(self.setup_ignore().returncode,0);old=p.read_bytes()
        self.assertTrue(old.startswith(b'# existing\r\n/custom-private\n'))
        self.assertEqual(self.setup_ignore().returncode,0);self.assertEqual(old,p.read_bytes())
        for rel in ('project-baseline/fingerprint.json','project-baseline/quality-gates.json','project-baseline/quality-report.json','baseline-draft/a','baseline-backups/a',' .baseline.lock'.strip(),'.baseline-previous/a','.baseline-stage-123/a','features/F/sources/prd.md'):
            self.assertTrue(self.ignored('.agent-workflow/'+rel),rel)
        for rel in ('.gitignore','config.yaml','project-baseline/coverage.md','project-baseline/quality-candidates.json','features/F/spec/requirements.json','features/F/tasks.json'):
            self.assertFalse(self.ignored('.agent-workflow/'+rel),rel)
        with p.open('a') as f:f.write('!/features/F/sources/prd.md\n')
        self.assertFalse(self.ignored('.agent-workflow/features/F/sources/prd.md'))

    def test_reports_tracked_files_without_untracking(self):
        p=self.root/'.agent-workflow/project-baseline/fingerprint.json';p.parent.mkdir(parents=True);p.write_text('{}')
        self.git('add','.')
        run=self.setup_ignore();self.assertEqual(run.returncode,0);self.assertIn('already tracked',run.stdout)
        self.assertIn('fingerprint.json',self.git('ls-files'));self.assertEqual(p.read_text(),'{}')

    def test_parent_ignore_report_and_custom_block_conflict(self):
        (self.root/'.gitignore').write_text('.agent-workflow/\n')
        self.assertIn('parent/existing',self.setup_ignore().stdout)
        p=self.root/'.agent-workflow/.gitignore';p.write_text(p.read_text().replace('/baseline-draft/','/custom/'))
        old=p.read_bytes();self.assertEqual(self.setup_ignore().returncode,2);self.assertEqual(p.read_bytes(),old)

    def test_clone_reuses_notes_and_rebuilds_local_fingerprint(self):
        self.assertEqual(self.setup_ignore().returncode,0)
        def action(root, name, expected=0):
            run=subprocess.run([sys.executable,str(SCRIPTS/'project.py'),name,str(root)],capture_output=True,text=True)
            self.assertEqual(run.returncode,expected,run.stdout+run.stderr)
        action(self.root,'scan')
        notes=self.root/'.agent-workflow/project-baseline/architecture.md';notes.write_text('Reviewed architecture retained')
        self.git('add','.')
        self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture')
        clone=Path(self.tmp.name)/'clone';self.git('clone','-q',str(self.root),str(clone))
        base=clone/'.agent-workflow/project-baseline'
        self.assertFalse((base/'fingerprint.json').exists());action(clone,'verify',2)
        action(clone,'scan-prepare');action(clone,'scan-publish');action(clone,'verify')
        self.assertEqual((base/'architecture.md').read_text(),'Reviewed architecture retained')
        self.assertEqual(self.git('status','--porcelain',root=clone),'')

if __name__=='__main__':unittest.main()
