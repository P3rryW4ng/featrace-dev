import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/dev/core/scripts/project.py'
spec = importlib.util.spec_from_file_location('scan_project', SCRIPT)
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class ScanContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base = self.root / '.agent-workflow/project-baseline'; self.base.mkdir(parents=True)

    def run_action(self, action, expected):
        run = subprocess.run([sys.executable, str(SCRIPT), action, str(self.root)], capture_output=True, text=True)
        self.assertEqual(run.returncode, expected, run.stdout + run.stderr)
        return run

    def config(self, gates):
        (self.base / 'quality-gates.json').write_text(json.dumps({'gates': gates}))

    def gate(self):
        return {'name': 'sentinel', 'command': [sys.executable, '-c', "from pathlib import Path; Path('executed').write_text('yes')"]}

    def test_validate_does_not_execute(self):
        self.config([self.gate()]); self.run_action('validate-gates', 0)
        self.assertFalse((self.root / 'executed').exists())

    def test_invalid_later_gate_prevents_all_execution(self):
        self.config([self.gate(), {'name': 'bad', 'command': 'gradlew check'}])
        self.run_action('check', 2); self.assertFalse((self.root / 'executed').exists())

    def test_conditions_and_placeholders_rejected(self):
        for key, value in [('when', 'after source change'), ('enabled', False), ('command', ['gradlew', '--tests', '<pattern>'])]:
            with self.subTest(key=key):
                g=self.gate(); g[key]=value; self.config([g]); self.run_action('validate-gates', 2)

    def test_empty_selection_never_passes_check(self):
        self.config([]); self.run_action('validate-gates', 0); self.run_action('check', 2)

    def test_candidates_not_executed(self):
        (self.base / 'quality-candidates.json').write_text(json.dumps({'candidates': [self.gate()]}))
        self.config([]); self.run_action('check', 2); self.assertFalse((self.root / 'executed').exists())

    def test_selected_only_runs(self):
        self.config([self.gate()]); self.run_action('check', 0)
        self.assertTrue((self.root / 'executed').exists())

    def test_bad_cwd_duplicate_name_and_timeout(self):
        for gates in ([dict(self.gate(), cwd='..')], [self.gate(), self.gate()], [dict(self.gate(), timeout_seconds=float('nan'))], [None]):
            self.config(gates); self.run_action('validate-gates', 2)

    def test_registered_evidence_and_rules_invalidate(self):
        (self.root / 'rules.md').write_text('original')
        (self.base / 'evidence-files.json').write_text('{"files":["rules.md"]}')
        self.run_action('scan', 0); self.run_action('verify', 0)
        (self.root / 'rules.md').write_text('changed without commit')
        self.run_action('verify', 3)
        self.run_action('scan', 0); (self.root / 'rules.md').unlink(); self.run_action('verify', 3)
        self.run_action('scan', 0); (self.root / 'CLAUDE.md').write_text('new rules'); self.run_action('verify', 3)

    def test_evidence_outside_root_rejected(self):
        (self.base / 'evidence-files.json').write_text('{"files":["../outside"]}')
        self.run_action('scan', 2)

    def test_rescan_preserves_reviewed_coverage(self):
        self.run_action('scan', 0)
        (self.base / 'coverage.md').write_text('app: reviewed UI only')
        self.run_action('scan', 0)
        self.assertEqual((self.base / 'coverage.md').read_text(), 'app: reviewed UI only')

if __name__ == '__main__': unittest.main()
