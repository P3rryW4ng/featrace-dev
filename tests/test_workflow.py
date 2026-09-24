import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from intake_helpers import attach_intake

REPO = Path(__file__).resolve().parents[1]
CORE = REPO / 'skills/dev/core/scripts'

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'project with spaces'
        self.root.mkdir()
        self.prd = Path(self.temp.name) / '需求.txt'
        self.prd.write_text('Convert a local string to uppercase. No network or UI.\n')

    def run_script(self, script, *args, expected=0):
        run = subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True, text=True)
        self.assertEqual(run.returncode, expected, run.stdout + run.stderr)
        return run

    def init(self):
        self.run_script(CORE / 'init-feature.py', 'FEAT-001', self.prd, self.root)
        self.folder = self.root / '.agent-workflow/features/FEAT-001'
        return self.folder

    def record(self, name, data):
        (self.folder / name).write_text(json.dumps(data))

    def valid(self):
        self.init()
        self.req = {'feature': {'id': 'FEAT-001', 'status': 'provisional', 'source_status': {'prd': 'present', 'api': 'not_applicable', 'figma': 'not_applicable'}, 'source_notes': {'api': 'local computation', 'figma': 'no UI'}}, 'requirements': [{'id': 'R-1', 'title': 'Uppercase', 'statement': 'Return uppercase text', 'status': 'confirmed', 'sources': [{'type': 'prd', 'ref': 'sources/prd-original.txt'}], 'acceptance_criteria': ['abc becomes ABC'], 'tasks': ['T-1'], 'tests': ['UT-1'], 'assumptions': []}]}
        self.record('spec/requirements.json', self.req)
        self.record('tasks.json', {'feature_id': 'FEAT-001', 'tasks': [{'id': 'T-1', 'title': 'Implement', 'status': 'done', 'requirement_ids': ['R-1'], 'test_evidence': ['UT-1: abc -> ABC passed (synthetic)']}]})
        self.record('traceability.json', {'feature_id': 'FEAT-001', 'links': [{'requirement_id': 'R-1', 'task_id': 'T-1', 'tests': ['UT-1'], 'code': ['convert.py']}]})

        attach_intake(self.folder, self.req)

    def validate(self, stage='develop', expected=0):
        return self.run_script(CORE / 'validate-feature.py', '--stage', stage, self.root, 'FEAT-001', expected=expected)

    def test_init_preserves_bytes_and_extension_and_refuses_overwrite(self):
        self.init()
        self.assertEqual((self.folder / 'sources/prd-original.txt').read_bytes(), self.prd.read_bytes())
        requirements = json.loads((self.folder / 'spec/requirements.json').read_text())
        self.assertTrue(requirements['feature']['history_regression_required'])
        self.assertTrue(requirements['feature']['task_review_required'])
        self.assertEqual(requirements['feature']['workflow_version'], 3)
        self.assertEqual(requirements['feature']['module_scope']['status'], 'pending')
        before = (self.folder / 'spec/requirements.json').read_bytes()
        self.run_script(CORE / 'init-feature.py', 'FEAT-001', self.prd, self.root, expected=1)
        self.assertEqual((self.folder / 'spec/requirements.json').read_bytes(), before)

    def test_path_traversal_rejected(self):
        self.run_script(CORE / 'init-feature.py', '../escape', self.prd, self.root, expected=1)
        self.assertFalse((self.root / '.agent-workflow').exists())

    def test_empty_draft_not_developable(self):
        self.init(); self.validate('draft'); self.validate(expected=1)

    def test_optional_sources_can_validate_and_render(self):
        self.valid(); self.validate(); self.validate('check')
        self.run_script(CORE / 'render-workspace.py', self.root, 'FEAT-001')
        self.assertIn('Uppercase', (self.folder / 'spec/spec.md').read_text())
        self.assertIn('R-1 → T-1 → UT-1', (self.folder / 'traceability.md').read_text())

    def test_render_traceability_displays_current_task_list(self):
        self.valid()
        self.record('traceability.json', {'feature_id': 'FEAT-001', 'links': [
            {'requirement_id': 'R-1', 'tasks': ['T-1', 'T-2'], 'tests': ['UT-1']},
        ]})
        self.run_script(CORE / 'render-workspace.py', self.root, 'FEAT-001')
        self.assertIn('R-1 → T-1, T-2 → UT-1', (self.folder / 'traceability.md').read_text())

    def test_not_applicable_requires_reason(self):
        self.valid(); self.req['feature']['source_notes'] = {}
        self.record('spec/requirements.json', self.req); self.validate(expected=1)

    def test_blocked_requirement_and_pending_decision(self):
        self.valid(); self.req['requirements'][0]['status'] = 'blocked'
        self.record('spec/requirements.json', self.req); self.validate(expected=1)
        self.req['requirements'][0]['status'] = 'confirmed'
        self.record('spec/requirements.json', self.req)
        self.record('decisions.json', {'feature_id': 'FEAT-001', 'decisions': [{'id': 'D-1', 'status': 'pending'}]})
        self.validate(expected=1)

    def test_migration_refuses_partial_existing_json(self):
        self.init()
        (self.folder / 'spec/requirements.json').unlink()
        legacy = self.folder / 'spec/requirements.yaml'; legacy.write_text('requirements: []\n')
        before = (self.folder / 'tasks.json').read_bytes()
        self.run_script(CORE / 'migrate-workspace.py', self.root, 'FEAT-001', expected=1)
        self.assertEqual(before, (self.folder / 'tasks.json').read_bytes())
        self.assertFalse((self.folder / 'spec/requirements.json').exists())

    def test_migration_preserves_legacy_and_blocks_develop(self):
        self.folder = self.root / '.agent-workflow/features/FEAT-001'
        (self.folder / 'spec').mkdir(parents=True)
        legacy = self.folder / 'spec/requirements.yaml'; legacy.write_text('requirements: []\n')
        self.run_script(CORE / 'migrate-workspace.py', self.root, 'FEAT-001')
        self.assertEqual(legacy.read_text(), 'requirements: []\n'); self.validate(expected=1)

    def test_profile_detection_and_fingerprint_add_delete(self):
        project = CORE / 'project.py'
        (self.root / 'build.gradle').write_text("plugins { id 'java' }")
        self.run_script(project, 'scan', self.root)
        base = self.root / '.agent-workflow/project-baseline'
        self.assertEqual(json.loads((base / 'fingerprint.json').read_text())['profile'], 'generic')
        (base / 'architecture.md').write_text('Reviewed architecture')
        (self.root / 'package.json').write_text('{}')
        self.run_script(project, 'verify', self.root, expected=3)
        self.run_script(project, 'scan', self.root)
        (self.root / 'package.json').unlink()
        self.run_script(project, 'verify', self.root, expected=3)
        (self.root / 'build.gradle').write_text("plugins { id 'com.android.application' }")
        self.run_script(project, 'scan', self.root)
        self.assertEqual(json.loads((base / 'fingerprint.json').read_text())['profile'], 'android')
        self.assertEqual((base / 'architecture.md').read_text(), 'Reviewed architecture')
        self.run_script(project, 'verify', self.root)

    def test_scan_renders_declared_module_graph(self):
        (self.root / 'build.cfg').write_text('fixture build')
        (self.root / 'wallet').mkdir()
        modules = self.root / '.agent-workflow/modules'
        modules.mkdir(parents=True)
        (modules / 'index.json').write_text(json.dumps({'schema_version': 1, 'shared_stack': 'Fixture stack',
            'global_files': ['build.cfg'], 'modules': [
                {'id': 'wallet', 'summary': 'Wallet behavior', 'roots': ['wallet'],
                 'evidence_files': [], 'depends_on': []}]}))
        output = self.run_script(CORE / 'project.py', 'scan', self.root)
        self.assertIn('MODULE_GRAPH_RENDERED: nodes=1 edges=0', output.stdout)
        self.assertTrue((modules / 'graph.json').is_file())
        self.assertIn('```mermaid', (modules / 'graph.md').read_text())

    def test_android_scan_renders_unconfirmed_gradle_candidates_without_catalog(self):
        (self.root / 'settings.gradle.kts').write_text('include(":app", ":wallet")\n')
        (self.root / 'app').mkdir(); (self.root / 'wallet').mkdir()
        (self.root / 'app' / 'build.gradle.kts').write_text('plugins { id("com.android.application") }\ndependencies { implementation(project(":wallet")) }\n')
        (self.root / 'wallet' / 'build.gradle.kts').write_text('plugins { id("com.android.library") }\n')
        output = self.run_script(CORE / 'project.py', 'scan', self.root)
        self.assertIn('MODULE_CANDIDATES_RENDERED: modules=2 edges=1 gaps=0', output.stdout)
        candidates = json.loads((self.root / '.agent-workflow/modules/candidates.json').read_text())
        self.assertEqual(candidates['status'], 'candidate_only')
        self.assertFalse((self.root / '.agent-workflow/modules/index.json').exists())

    def test_quality_reports_real_exit_and_unavailable(self):
        project = CORE / 'project.py'
        self.run_script(project, 'scan', self.root)
        self.run_script(project, 'check', self.root, expected=2)
        base = self.root / '.agent-workflow/project-baseline'
        for code in (0, 1):
            (base / 'quality-gates.json').write_text(json.dumps({'gates': [{'name': 'synthetic', 'command': [sys.executable, '-c', 'raise SystemExit(%d)' % code]}]}))
            self.run_script(project, 'check', self.root, expected=code)
            self.assertEqual(json.loads((base / 'quality-report.json').read_text())['results'][0]['returncode'], code)

    def test_installer_copy_idempotence_conflict_and_uninstall(self):
        home = Path(self.temp.name) / 'isolated-home'
        installer = REPO / 'scripts/install.py'
        self.run_script(installer, '--home', home)
        self.run_script(installer, '--home', home)
        for directory in ('.claude', '.agents'):
            self.assertTrue((home / directory / 'skills/dev/core/scripts/project.py').is_file())
        self.assertFalse((home / '.claude/CLAUDE.md').exists())
        skill = home / '.claude/skills/dev/SKILL.md'
        old = skill.read_text(); skill.write_text(old + '\nlocal edit')
        self.run_script(installer, '--home', home, '--update', expected=1)
        self.assertIn('local edit', skill.read_text())
        skill.write_text(old)
        self.run_script(installer, '--home', home, '--uninstall')
        self.assertFalse(skill.exists())
        self.assertEqual(len(list((home / '.feature-delivery/backups').iterdir())), 2)

    def test_installer_unowned_preflight_no_partial_install(self):
        home = Path(self.temp.name) / 'isolated-home'
        target = home / '.agents/skills/dev'; target.mkdir(parents=True)
        (target / 'SKILL.md').write_text('someone else')
        self.run_script(REPO / 'scripts/install.py', '--home', home, expected=1)
        self.assertFalse((home / '.claude/skills/dev').exists())

    def test_installer_update_keeps_old_copy(self):
        clone = Path(self.temp.name) / 'clone'
        shutil.copytree(REPO, clone, ignore=shutil.ignore_patterns('__pycache__'))
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

if __name__ == '__main__':
    unittest.main()
