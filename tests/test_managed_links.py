"""Observable identity/runner/continuity boundaries using synthetic Git projects."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

CORE = Path(__file__).resolve().parents[1] / 'skills/dev/core/scripts'
sys.path.insert(0, str(CORE))
import check_identity as ci
import managed_links as ml
from evidence_carry import project_files
import regression_continuity as continuity


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), '-c', 'user.name=Fixture',
                                   '-c', 'user.email=fixture@example.invalid', *args], stderr=subprocess.PIPE)


def commit(root):
    git(root, 'add', '-A'); git(root, 'commit', '-qm', 'synthetic input')


def fixture_links(root, count=1):
    for i in range(count):
        name = 'fixture-%02d' % i
        target = root / '.agents/skills' / name
        target.mkdir(parents=True)
        for n in range(4 if count == 14 and i < 4 else 3):
            (target / ('input-%d.md' % n)).write_text('Synthetic managed input %d/%d\n' % (i, n))
        alias = root / '.claude/skills' / name
        alias.parent.mkdir(parents=True, exist_ok=True)
        alias.symlink_to('../../.agents/skills/' + name, target_is_directory=True)
    commit(root)


class ManagedLinksTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        git(self.root, 'init'); (self.root / 'README.md').write_text('Synthetic ordinary source')
        commit(self.root)

    @property
    def alias(self): return self.root / '.claude/skills/fixture-00'

    @property
    def member(self): return self.root / '.agents/skills/fixture-00/input-0.md'

    def check(self): return ci.capture(self.root)

    def test_fourteen_links_and_forty_six_files_are_bound_not_excluded(self):
        fixture_links(self.root, 14)
        identity = self.check()
        self.assertEqual(identity['state'], 'identified', identity)
        self.assertEqual(identity['schema_version'], 2)
        self.assertTrue(ci.valid(identity))
        links = [v for v in identity['files'].values() if v['state'] == 'managed_directory_link']
        self.assertEqual(len(links), 14)
        self.assertEqual(sum(len(v['members']) for v in links), 46)
        self.assertEqual(ci.compare(identity, self.check())['state'], 'same')
        continuity.check_worktree(self.root, project_files(self.root))

    def test_ordinary_projects_keep_schema_one_and_old_reader_compatibility(self):
        identity = self.check(); self.assertEqual(identity['schema_version'], 1)
        old = self.old_reader()
        self.assertTrue(old.valid(identity)); self.assertEqual(old.collect(self.root, (), ()), ci.collect(self.root, (), ()))

    def old_reader(self):
        source = git(Path(__file__).resolve().parents[1], 'show',
                     'ed33c6d311ecb65f635b7f0f3c10170827a4f13c:skills/dev/core/scripts/check_identity.py')
        module = types.ModuleType('released_check_identity')
        exec(compile(source, '<released-0.18-reader>', 'exec'), module.__dict__)
        return module

    def test_old_reader_rejects_new_identity_and_live_links(self):
        fixture_links(self.root)
        old = self.old_reader(); current = self.check()
        self.assertFalse(old.valid(current))
        self.assertEqual(old.compare(current, current)['state'], 'unknown')
        self.assertEqual(old.capture(self.root)['state'], 'unknown')
        source=git(Path(__file__).resolve().parents[1], 'show',
                   'ed33c6d311ecb65f635b7f0f3c10170827a4f13c:skills/dev/core/scripts/regression_continuity.py')
        node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='check_worktree')
        namespace={'Path':Path,'git':git,'path_name':lambda name:name}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<released-device-reader>','exec'),namespace)
        with self.assertRaisesRegex(ValueError,'symlink input'):
            namespace['check_worktree'](self.root,project_files(self.root))

    def test_hidden_target_changes_and_permissions_are_detected(self):
        fixture_links(self.root)
        original = self.member.read_bytes(); rel = str(self.member.relative_to(self.root))
        for flag in ('assume-unchanged', 'skip-worktree'):
            with self.subTest(flag=flag):
                before = self.check()
                git(self.root, 'update-index', '--' + flag, rel)
                self.member.write_text('Changed despite ' + flag)
                self.assertEqual(git(self.root, 'diff', '--name-only'), b'')
                self.assertEqual(ci.compare(before, self.check())['state'], 'changed')
                with self.assertRaisesRegex(ValueError, 'actual input differs'):
                    continuity.check_worktree(self.root, project_files(self.root))
                self.member.write_bytes(original)
                git(self.root, 'update-index', '--no-' + flag, rel)
        before = self.check(); self.member.chmod(0o755)
        self.assertEqual(ci.compare(before, self.check())['state'], 'changed')

    def test_link_retarget_and_membership_changes_are_detected(self):
        fixture_links(self.root); before = self.check()
        (self.member.parent / 'new.md').write_text('New tracked member'); commit(self.root)
        after = self.check(); self.assertEqual(ci.compare(before, after)['state'], 'changed')
        self.assertIn('new.md', ' '.join(after['files'][str(self.alias.relative_to(self.root))]['members']))
        other = self.root / 'other-target'; other.mkdir(); (other / 'README').write_text('Other managed input')
        self.alias.unlink(); self.alias.symlink_to('../../other-target'); commit(self.root)
        self.assertEqual(ci.compare(after, self.check())['state'], 'changed')

    def test_uncommitted_or_replaced_links_are_not_certified(self):
        fixture_links(self.root)
        for replacement in ('../../.agents/skills/not-present', None):
            self.alias.unlink()
            if replacement is None: self.alias.write_text('ordinary replacement')
            else: self.alias.symlink_to(replacement)
            self.assertEqual(self.check()['state'], 'unknown')
        self.alias.unlink(); self.alias.symlink_to('../../.agents/skills/fixture-00')
        git(self.root, 'add', str(self.alias.relative_to(self.root)))
        extra = self.root / 'uncommitted-link'; extra.symlink_to('.agents/skills/fixture-00')
        git(self.root, 'add', 'uncommitted-link')
        self.assertEqual(self.check()['state'], 'unknown')

    def test_absolute_external_missing_root_control_and_file_targets_refused(self):
        fixture_links(self.root)
        targets = [str(self.member.parent), '../../../outside', '../../missing', '../..',
                   '../../.git', '../../.agent-workflow', '../../README.md',
                   '../../.agents/skills/fixture-00/../fixture-00']
        for target in targets:
            with self.subTest(target=target):
                self.alias.unlink(); self.alias.symlink_to(target); commit(self.root)
                self.assertEqual(self.check()['state'], 'unknown')
                with self.assertRaises((ValueError, OSError)):
                    continuity.check_worktree(self.root, project_files(self.root))

    def test_nested_links_and_cycles_are_never_followed(self):
        fixture_links(self.root)
        nested = self.member.parent / 'nested'; nested.symlink_to('..'); commit(self.root)
        self.assertEqual(self.check()['state'], 'unknown')
        nested.unlink(); commit(self.root)
        self.alias.unlink(); self.alias.symlink_to('fixture-00'); commit(self.root)
        self.assertEqual(self.check()['state'], 'unknown')

    def test_unmanaged_ignored_missing_and_submodule_members_refused(self):
        fixture_links(self.root)
        extra = self.member.parent / 'extra'; extra.write_text('not tracked')
        self.assertEqual(self.check()['state'], 'unknown'); extra.unlink()
        (self.root / '.gitignore').write_text('*.private\n'); commit(self.root)
        extra = self.member.parent / 'input.private'; extra.write_text('ignored')
        self.assertEqual(self.check()['state'], 'unknown'); extra.unlink()
        self.member.unlink(); self.assertEqual(self.check()['state'], 'unknown')
        git(self.root, 'checkout', '--', str(self.member.relative_to(self.root)))
        git(self.root, 'update-index', '--add', '--cacheinfo', '160000',
            git(self.root, 'rev-parse', 'HEAD').decode().strip(), '.agents/skills/fixture-00/submodule')
        git(self.root, 'commit', '-qm', 'unsupported synthetic submodule')
        self.assertEqual(self.check()['state'], 'unknown')

    def test_declared_inputs_and_workflow_paths_do_not_gain_link_permission(self):
        fixture_links(self.root)
        required = str(self.alias.relative_to(self.root)) + '/input-0.md'
        self.assertEqual(ci.capture(self.root, [required])['state'], 'unknown')
        (self.root / '.agent-workflow').mkdir(); (self.root / '.agent-workflow/evidence').symlink_to(self.member.parent)
        self.assertEqual(ci.capture(self.root, ['.agent-workflow/evidence/input-0.md'])['state'], 'unknown')

    def test_target_edit_during_descriptor_read_is_unknown(self):
        fixture_links(self.root)
        original = ml.os.read
        changed = []
        inode = self.member.stat().st_ino
        def race(fd, length):
            result = original(fd, length)
            if result and not changed and os.fstat(fd).st_ino == inode:
                changed.append(True); self.member.write_text('Changed during descriptor read')
            return result
        with patch.object(ml.os, 'read', side_effect=race):
            self.assertEqual(self.check()['state'], 'unknown')

    def test_link_swap_during_read_never_produces_identified_input(self):
        fixture_links(self.root)
        original = ml.members; changed = []
        def race(*args):
            result = original(*args)
            if not changed:
                changed.append(True); self.alias.unlink(); self.alias.symlink_to('/does-not-exist')
            return result
        with patch.object(ml, 'members', side_effect=race):
            self.assertEqual(self.check()['state'], 'unknown')

    def test_target_swap_before_open_never_reads_replacement(self):
        fixture_links(self.root)
        original = ml.os.open; changed = []
        def race(name, flags, *args, **kwargs):
            if name == 'fixture-00' and not changed:
                changed.append(True)
                self.member.parent.rename(self.member.parent.with_name('original'))
                self.member.parent.symlink_to(self.root.parent)
            return original(name, flags, *args, **kwargs)
        with patch.object(ml.os, 'open', side_effect=race), patch.object(ml, 'read_member') as read:
            self.assertEqual(self.check()['state'], 'unknown')
            read.assert_not_called()

    def test_malformed_or_downgraded_link_records_are_unknown(self):
        fixture_links(self.root); identity = self.check(); alias = str(self.alias.relative_to(self.root))
        variants=[]
        for field, value in [('members', []), ('target_path', '../outside'), ('sha256', '0'*64), ('target', '/outside')]:
            broken = copy.deepcopy(identity); broken['files'][alias][field]=value; variants.append(broken)
        broken=copy.deepcopy(identity);broken['schema_version']=1;variants.append(broken)
        broken=copy.deepcopy(identity);broken['files'][str(self.member.relative_to(self.root))]='malformed';variants.append(broken)
        for value in variants:
            self.assertEqual(ci.compare(value, value)['state'], 'unknown')

    def test_sha256_git_objects_and_same_target_aliases(self):
        git(self.root, 'init', '--object-format=sha256', 'sha256-fixture')
        root = self.root / 'sha256-fixture'; (root/'README').write_text('SHA256 Git fixture'); commit(root)
        fixture_links(root)
        (root/'second').symlink_to('.agents/skills/fixture-00');commit(root)
        identity = ci.capture(root)
        self.assertEqual(identity['state'], 'identified', identity); self.assertTrue(ci.valid(identity))
        continuity.check_worktree(root, project_files(root))


class ManagedLinkIntegrationTests(unittest.TestCase):
    def test_legacy_runner_keeps_schema_two_and_stales_on_target_changes(self):
        import test_delivery_audit
        h=test_delivery_audit.DeliveryAuditTests();h.setUp();self.addCleanup(h.doCleanups)
        fixture_links(h.root)
        h.script('project.py','check',h.root)
        report=json.loads((h.base/'quality-report.json').read_text())
        self.assertEqual(report['project_snapshot']['check_inputs']['schema_version'],2)
        h.script('audit-delivery.py',h.root,'FEAT-001')
        (h.root/'.agents/skills/fixture-00/input-0.md').write_text('Changed actual tool input')
        h.script('audit-delivery.py',h.root,'FEAT-001',expected=1)

    def test_feature_attempt_adoption_and_latest_failure_keep_their_contract(self):
        import test_check_runs
        h=test_check_runs.CheckRunTests();h.setUp();self.addCleanup(h.doCleanups)
        fixture_links(h.root)
        # Model pre-existing tool links, not links introduced by this feature.
        h.helper.doc['base_revision']=git(h.root,'rev-parse','HEAD').decode().strip();h.helper.save()
        ident=h.map_claim(); report=h.execute();h.adopt(ident)
        self.assertEqual(report['project_snapshot']['check_inputs']['schema_version'],2)
        self.assertEqual(h.effective(h.plan()['items'][0]),'passed')
        cfg=json.loads((h.helper.base/'quality-gates.json').read_text())
        cfg['gates'][0]['command']=[sys.executable,'-c','raise SystemExit(7)']
        (h.helper.base/'quality-gates.json').write_text(json.dumps(cfg))
        self.assertEqual(test_check_runs.runs.run(h.root,'FEAT-001'),2)
        self.assertEqual(test_check_runs.runs.view(h.root,'FEAT-001')['state'],'unavailable')

    def test_device_review_apply_references_original_and_detects_target_edit(self):
        import test_regression_continuity
        h=test_regression_continuity.DeviceContinuityTests();h.setUp();self.addCleanup(h.doCleanups)
        fixture_links(h.root)
        h.apply()
        doc=h.doc();self.assertEqual(doc['fixes'][0]['regression_execution_history'][0],h.origin)
        self.assertTrue(test_regression_continuity.current_evidence(h.root,h.folder,doc['fixes'][0],'UT-1'))
        h.old.helper.script('project.py','check',h.root)
        h.old.helper.script('audit-delivery.py',h.root,'FEAT-001')
        git(h.root,'update-index','--assume-unchanged','.agents/skills/fixture-00/input-0.md')
        (h.root/'.agents/skills/fixture-00/input-0.md').write_text('Hidden actual target change')
        with self.assertRaisesRegex(ValueError, 'actual input differs'):
            test_regression_continuity.current_evidence(h.root,h.folder,doc['fixes'][0],'UT-1')

    def test_manual_scope_reader_reuses_same_identity_boundary(self):
        import test_manual_scope
        h=test_manual_scope.ManualScopeTests();h.setUp();self.addCleanup(h.doCleanups)
        fixture_links(h.root)
        h.h.doc['base_revision']=git(h.root,'rev-parse','HEAD').decode().strip();h.h.save()
        snap=h.capture();h.apply(snap)
        self.assertTrue(all(h.states()[i]=='retained' for i in h.ids))
        (h.root/'.agents/skills/fixture-00/extra').write_text('Unmanaged target member')
        self.assertEqual(test_manual_scope.m.view(h.root,h.folder)['state'],'unavailable')

    def test_links_new_to_feature_still_need_original_impact_handling(self):
        import test_check_runs
        h=test_check_runs.CheckRunTests();h.setUp();self.addCleanup(h.doCleanups)
        fixture_links(h.root)
        ident=h.map_claim();h.execute()
        with self.assertRaisesRegex(ValueError,'symlink/outside path needs manual handling'):
            h.adopt(ident)

    def test_unknown_link_stops_before_any_gate_command(self):
        import test_delivery_audit
        h=test_delivery_audit.DeliveryAuditTests();h.setUp();self.addCleanup(h.doCleanups)
        fixture_links(h.root)
        alias=h.root/'.claude/skills/fixture-00';alias.unlink();alias.symlink_to('/outside');commit(h.root)
        h.gates([{'name':'sentinel','command':[sys.executable,'-c',"from pathlib import Path; Path('executed').touch()"], 'test_ids':['UT-1']}])
        h.script('project.py','check',h.root,expected=2)
        self.assertFalse((h.root/'executed').exists())
        self.assertFalse((h.base/'quality-report.json').exists())
