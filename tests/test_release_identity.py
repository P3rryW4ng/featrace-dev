import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO=Path(__file__).resolve().parents[1]
class ReleaseIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)/'source'
        shutil.copytree(REPO/'skills',self.root/'skills',ignore=shutil.ignore_patterns('__pycache__'))
        (self.root/'scripts').mkdir();shutil.copyfile(REPO/'scripts/install.py',self.root/'scripts/install.py');(self.root/'VERSION').write_text('9.0.0\n')
        spec=importlib.util.spec_from_file_location('isolated_installer',self.root/'scripts/install.py');self.installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.installer)
        self.git('init','-q');self.git('config','user.name','Synthetic');self.git('config','user.email','synthetic@example.invalid')
    def git(self,*args):
        r=subprocess.run(['git','-C',str(self.root),*args],capture_output=True);self.assertEqual(r.returncode,0,r.stderr);return r.stdout.decode().strip()
    def formal(self):
        desc={'channel':'release','version':'9.0.0','files':self.installer.hashes(self.root/'skills/dev'),'installer_sha256':hashlib.sha256((self.root/'scripts/install.py').read_bytes()).hexdigest()}
        (self.root/'release.json').write_text(json.dumps(desc));self.git('add','.');self.git('commit','-qm','synthetic release');self.git('branch','release/9.0.0')
    def test_candidate_cannot_masquerade_as_formal_version(self):
        with self.assertRaisesRegex(ValueError,'DESCRIPTOR_REQUIRED'):self.installer.source_identity()
        dev=self.installer.source_identity(True);self.assertNotEqual(dev['version'],'9.0.0');self.assertEqual(dev['channel'],'development')
    def test_formal_identity_binds_committed_content(self):
        self.formal();identity=self.installer.source_identity();self.assertEqual(identity['source_commit'],self.git('rev-parse','HEAD'));self.assertEqual(identity['channel'],'release')
        p=self.root/'skills/dev/SKILL.md';p.write_text(p.read_text()+'\nmodified')
        with self.assertRaisesRegex(ValueError,'CONTENT_MISMATCH'):self.installer.source_identity()
    def test_descriptor_without_matching_release_ref_refuses(self):
        self.formal();self.git('branch','-D','release/9.0.0')
        with self.assertRaisesRegex(ValueError,'REF_MISMATCH'):self.installer.source_identity()
    def test_uncommitted_matching_descriptor_refuses(self):
        self.formal();p=self.root/'release.json';p.write_text(p.read_text()+'\n')
        with self.assertRaisesRegex(ValueError,'WORKTREE_CHANGED'):self.installer.source_identity()
    def test_installed_marker_preserves_channel_and_commit(self):
        self.formal();home=Path(self.temp.name)/'home'
        r=subprocess.run([sys.executable,str(self.root/'scripts/install.py'),'--home',str(home),'--agent','claude'],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr);marker=json.loads((home/'.claude/skills/dev/.feature-delivery-install.json').read_text())
        self.assertEqual(marker['source']['channel'],'release');self.assertEqual(marker['source']['source_commit'],self.git('rev-parse','HEAD'))
