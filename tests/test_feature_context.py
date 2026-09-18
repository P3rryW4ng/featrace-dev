import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "skills/dev/core/scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("feature_context", SCRIPTS / "feature-context.py")
ctx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctx)


class FeatureContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name).resolve()
        self.record("A")
        self.record("B")

    def record(self, fid):
        path = self.root / ".agent-workflow/features" / fid / "spec/requirements.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"feature": {"id": fid, "title": "Title " + fid, "status": "drafted"}}))
        return path

    def test_inventory_and_no_default_even_single_feature(self):
        self.assertEqual([r["id"] for r in ctx.inventory(self.root)], ["A", "B"])
        with self.assertRaises(ValueError):
            ctx.resolve(self.root)
        (self.root / ".agent-workflow/features/B/spec/requirements.json").unlink()
        with self.assertRaises(ValueError):
            ctx.resolve(self.root)

    def test_sessions_and_explicit_override_are_read_only(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(ctx.resolve(self.root, current="A", current_root=self.root)["id"], "A")
        self.assertEqual(ctx.resolve(self.root, current="B", current_root=self.root)["id"], "B")
        self.assertEqual(ctx.resolve(self.root, explicit="B", current="A", current_root=self.root)["id"], "B")
        self.assertEqual(ctx.resolve(self.root, current="A", current_root=self.root)["id"], "A")
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_project_scope_and_invalid_explicit_do_not_fall_back(self):
        with self.assertRaises(ValueError):
            ctx.resolve(self.root, current="A", current_root=self.root / "other")
        with self.assertRaises(OSError):
            ctx.resolve(self.root, explicit="MISSING", current="A", current_root=self.root)
        with self.assertRaises(ValueError):
            ctx.resolve(self.root, explicit="../A")

    def test_deleted_or_corrupt_selection_and_inventory(self):
        path = self.root / ".agent-workflow/features/A/spec/requirements.json"
        path.write_text("{")
        with self.assertRaises(ValueError):
            ctx.resolve(self.root, current="A", current_root=self.root)
        self.assertIn("error", ctx.inventory(self.root)[0])
        path.unlink()
        with self.assertRaises(OSError):
            ctx.resolve(self.root, current="A", current_root=self.root)

    def test_record_identity_and_shape(self):
        path = self.root / ".agent-workflow/features/A/spec/requirements.json"
        for doc in ([], {"feature": {"id": "B", "title": "B", "status": "drafted"}},
                    {"feature": {"id": "A", "title": [], "status": "drafted"}}):
            path.write_text(json.dumps(doc))
            with self.assertRaises(ValueError):
                ctx.describe(self.root, "A")

    def test_outside_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            path = pathlib.Path(outside) / "requirements.json"
            path.write_text('{}')
            target = self.root / ".agent-workflow/features/A/spec/requirements.json"
            target.unlink()
            target.symlink_to(path)
            with self.assertRaises(ValueError):
                ctx.describe(self.root, "A")

    def test_cli_use_and_failure(self):
        command = [sys.executable, str(SCRIPTS / "feature-context.py"), "use", str(self.root)]
        good = subprocess.run(command + ["--feature", "B"], capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertEqual(json.loads(good.stdout)["id"], "B")
        bad = subprocess.run(command + ["--feature", "NONE"], capture_output=True, text=True)
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("FEATURE_CONTEXT_ERROR", bad.stderr)

    def test_creation_refuses_existing_and_missing_source_without_overwrite(self):
        source = self.root / "prd.md"
        source.write_text("# Synthetic PRD")
        existing = self.root / ".agent-workflow/features/A/spec/requirements.json"
        before = existing.read_bytes()
        for fid, src in (("A", source), ("NEW", self.root / "missing.md")):
            result = subprocess.run([sys.executable, str(SCRIPTS / "init-feature.py"), fid,
                                     str(src), str(self.root)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
        self.assertEqual(existing.read_bytes(), before)
        self.assertFalse((self.root / ".agent-workflow/features/NEW").exists())
        self.assertEqual(ctx.resolve(self.root, current="A", current_root=self.root)["id"], "A")
