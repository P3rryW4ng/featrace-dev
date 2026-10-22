import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
REPO=Path(__file__).resolve().parents[1]
class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
    def run_script(self,script,*args,expected=0):
        run=subprocess.run([sys.executable,str(script),'--development',*map(str,args)],capture_output=True,text=True)
        self.assertEqual(run.returncode,expected,run.stdout+run.stderr);return run
    def test_installer_copy_idempotence_conflict_and_uninstall(self):
        home = Path(self.temp.name) / 'isolated-home'
        installer = REPO / 'scripts/install.py'
        self.run_script(installer, '--home', home)
        self.run_script(installer, '--home', home)
        for directory in ('.claude', '.agents'):
            self.assertTrue((home / directory / 'skills/dev/core/scripts/task_workflow.py').is_file())
        self.assertFalse((home / '.claude/CLAUDE.md').exists())
        skill = home / '.claude/skills/dev/SKILL.md'
        old = skill.read_text(); skill.write_text(old + '\nlocal edit')
        self.run_script(installer, '--home', home, '--update', expected=1)
        self.assertIn('local edit', skill.read_text())
        skill.write_text(old)
        self.run_script(installer, '--home', home, '--uninstall')
        self.assertFalse(skill.exists())
        self.assertEqual(len(list((home / '.feature-delivery/backups').iterdir())), 2)

    def test_installer_migrates_legacy_identity_with_backup_and_no_duplicate_skill(self):
        home = Path(self.temp.name) / 'isolated-home'
        installer = REPO / 'scripts/install.py'
        self.run_script(installer, '--home', home, '--agent', 'claude')
        target = home / '.claude/skills/dev'
        marker = target / '.feature-delivery-install.json'
        legacy = json.loads(marker.read_text())
        legacy['package'] = 'feature-delivery-skill'
        legacy['version'] = '0.5.21'
        marker.write_text(json.dumps(legacy))
        self.run_script(installer, '--home', home, '--agent', 'claude', expected=1)
        self.run_script(installer, '--home', home, '--agent', 'claude', '--update')
        self.assertEqual(json.loads(marker.read_text())['package'], 'featrace-dev')
        backups = list((home / '.feature-delivery/backups').iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual(json.loads((backups[0] / marker.name).read_text()), legacy)
        self.assertEqual([p.name for p in target.parent.iterdir()], ['dev'])
        self.run_script(installer, '--home', home, '--agent', 'claude', '--update')
        self.assertEqual(len(list((home / '.feature-delivery/backups').iterdir())), 1)

    def test_installer_rejects_modified_legacy_install(self):
        home = Path(self.temp.name) / 'isolated-home'
        installer = REPO / 'scripts/install.py'
        self.run_script(installer, '--home', home, '--agent', 'claude')
        target = home / '.claude/skills/dev'
        marker = target / '.feature-delivery-install.json'
        legacy = json.loads(marker.read_text()); legacy['package'] = 'feature-delivery-skill'
        marker.write_text(json.dumps(legacy))
        skill = target / 'SKILL.md'; skill.write_text(skill.read_text() + '\nLocal customization\n')
        self.run_script(installer, '--home', home, '--agent', 'claude', '--update', expected=1)
        self.assertIn('Local customization', skill.read_text())
        self.assertEqual(json.loads(marker.read_text()), legacy)
        self.assertFalse((home / '.feature-delivery/backups').exists())

    def test_installer_unowned_preflight_no_partial_install(self):
        home = Path(self.temp.name) / 'isolated-home'
        target = home / '.agents/skills/dev'; target.mkdir(parents=True)
        (target / 'SKILL.md').write_text('someone else')
        self.run_script(REPO / 'scripts/install.py', '--home', home, expected=1)
        self.assertFalse((home / '.claude/skills/dev').exists())

    def test_installer_update_keeps_old_copy(self):
        clone = Path(self.temp.name) / 'clone'
        shutil.copytree(REPO/'skills', clone/'skills', ignore=shutil.ignore_patterns('__pycache__'));shutil.copytree(REPO/'scripts',clone/'scripts');shutil.copyfile(REPO/'VERSION',clone/'VERSION')
        home = Path(self.temp.name) / 'isolated-home'
        installer = clone / 'scripts/install.py'
        self.run_script(installer, '--home', home, '--agent', 'claude')
        source = clone / 'skills/dev/SKILL.md'; source.write_text(source.read_text() + '\nUpdated fixture\n')
        self.run_script(installer, '--home', home, '--agent', 'claude', expected=1)
        self.run_script(installer, '--home', home, '--agent', 'claude', '--update')
        self.assertIn('Updated fixture', (home / '.claude/skills/dev/SKILL.md').read_text())
        backups = list((home / '.feature-delivery/backups').iterdir())
        self.assertEqual(len(backups), 1)
        self.assertNotIn('Updated fixture', (backups[0] / 'SKILL.md').read_text())
