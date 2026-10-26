from pathlib import Path
from datetime import datetime,timezone,timedelta
import sys,tempfile,unittest
import test_task_workflow as fixture
w=fixture.w


class TaskInputAssetTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.TaskWorkflowTests(methodName='runTest');self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.ext=Path(self.temp.name).resolve()
        self.csv=self.ext/'reference.csv';self.csv.write_text('code,label\nGB,British\n')
        self.script=self.ext/'verify.py';self.script.write_text('from pathlib import Path\nimport sys\nassert "British" in Path(sys.argv[1]).read_text()\n')

    def imported(self):
        f=self.f
        a=w.attach(f.root,f.ident,str(self.script),'input')
        b=w.attach(f.root,f.ident,str(self.csv),'input')
        c=f.plan['checks'][0];c['argv']=[sys.executable,str(f.root/a['path']),str(f.root/b['path'])]
        c['input_assets']=[a['attachment'],b['attachment']]
        f.plan['criteria'][0]['source_assets']=[b['attachment']]
        f.refresh();return a,b

    def test_external_snapshots_are_actual_command_and_source_inputs(self):
        f=self.f;a,b=self.imported();self.assertEqual(f.execute()['status'],'passed');f.support()
        self.assertTrue(w.view(f.root,f.ident)['eligible'])
        self.assertEqual(f.doc()['attachments'][b['attachment']]['origin'],str(self.csv))

    def test_original_change_does_not_relabel_fixed_snapshot_as_current(self):
        f=self.f;a,b=self.imported();first=f.execute();self.csv.write_text('Changed external version');self.script.unlink()
        self.assertTrue(f.execute()['reused'])
        self.assertIn(first['execution'],f.doc()['facts'])
        self.assertIn('British',(f.root/b['path']).read_text())

    def test_new_selected_data_snapshot_invalidates_only_its_check(self):
        f=self.f;a,b=self.imported();first=f.execute();self.csv.write_text('Changed external version')
        new=w.attach(f.root,f.ident,str(self.csv),'input')
        c=f.plan['checks'][0];c['argv'][-1]=str(f.root/new['path']);c['input_assets']=[a['attachment'],new['attachment']]
        f.plan['criteria'][0]['source_assets']=[new['attachment']];f.refresh()
        result=f.execute();self.assertFalse(result['reused']);self.assertEqual(result['status'],'failed')
        self.assertIn(first['execution'],f.doc()['facts'])

    def test_task_owned_scratch_helper_can_be_captured_not_used_raw(self):
        f=self.f;p=f.root/'.featrace/scratch'/f.ident/'helper.py';p.parent.mkdir(parents=True);p.write_text('print("synthetic check")')
        f.plan['checks'][0]['argv']=[sys.executable,str(p)]
        with self.assertRaisesRegex(ValueError,'UNDECLARED_CONTROL_COMMAND_INPUT'):f.refresh()
        a=w.attach(f.root,f.ident,str(p),'input')
        f.plan['checks'][0]['argv']=[sys.executable,str(f.root/a['path'])]
        f.plan['checks'][0]['input_assets']=[a['attachment']];f.refresh()
        self.assertEqual(f.execute()['status'],'passed')

    def test_other_tasks_scratch_cannot_be_imported_as_owned_input(self):
        f=self.f;p=f.root/'.featrace/scratch/OTHER/data.csv';p.parent.mkdir(parents=True);p.write_text('other task')
        with self.assertRaisesRegex(ValueError,'ASSET_CONTROL_SOURCE'):w.attach(f.root,f.ident,str(p),'input')

    def test_task_record_cannot_become_its_own_input_under_any_spelling(self):
        f=self.f;p=w.task_path(f.root,f.ident)
        with self.assertRaisesRegex(ValueError,'ASSET_CONTROL_SOURCE'):w.attach(f.root,f.ident,str(p),'input')
        for name in (p.relative_to(f.root).as_posix(),str(p)):
            with self.assertRaisesRegex(ValueError,'GENERATED_SCOPE_INPUT'):
                w.task_inputs.signature(f.root,[],[],[{'kind':'file','path':str(f.root/name) if not Path(name).is_absolute() else name}],[])

    def test_evidence_role_cannot_be_adopted_as_execution_input(self):
        f=self.f;a=w.attach(f.root,f.ident,str(self.csv))
        f.plan['checks'][0]['input_assets']=[a['attachment']]
        with self.assertRaisesRegex(ValueError,'INPUT_ASSET_REQUIRED'):f.refresh()

    def test_snapshot_tampering_is_refused_not_silently_refingerprinted(self):
        f=self.f;a,b=self.imported();f.execute();(f.root/b['path']).write_text('tampered snapshot')
        with self.assertRaisesRegex(ValueError,'INPUT_ASSET_CHANGED'):f.execute()
        self.assertFalse(w.view(f.root,f.ident)['eligible'])

    def test_product_source_reselection_does_not_rerun_unrelated_execution(self):
        f=self.f;a=w.attach(f.root,f.ident,str(self.csv),'input')
        f.plan['criteria'][0]['source_assets']=[a['attachment']];f.refresh();f.execute();f.support()
        self.csv.write_text('Changed product source');b=w.attach(f.root,f.ident,str(self.csv),'input')
        f.plan['criteria'][0]['source_assets']=[b['attachment']];f.refresh()
        self.assertTrue(f.execute()['reused']);self.assertFalse(w.view(f.root,f.ident)['eligible'])

    def test_undeclared_external_script_is_not_certifiable_by_argv_alone(self):
        f=self.f;f.plan['checks'][0]['argv']=[sys.executable,str(self.script),str(self.csv)]
        with self.assertRaisesRegex(ValueError,'COMMAND_SCRIPT_INPUT_REQUIRED'):f.refresh()
        f.plan['checks'][0]['external_inputs']=[{'kind':'file','path':str(self.script)},{'kind':'file','path':str(self.csv)}];f.refresh()
        self.assertEqual(f.execute()['status'],'passed')

    def test_interpreter_flags_do_not_hide_undeclared_script(self):
        f=self.f;f.plan['checks'][0]['argv']=[sys.executable,'-u','-X','dev',str(self.script),str(self.csv)]
        with self.assertRaisesRegex(ValueError,'COMMAND_SCRIPT_INPUT_REQUIRED'):f.refresh()
        f.plan['checks'][0]['external_inputs']=[{'kind':'file','path':str(self.script)},{'kind':'file','path':str(self.csv)}];f.refresh()
        self.assertEqual(f.execute()['status'],'passed');self.script.write_text('raise RuntimeError("changed helper")')
        self.assertEqual(f.execute()['status'],'failed')

    def test_python_optimization_flag_does_not_consume_script_path(self):
        f=self.f;f.plan['checks'][0]['argv']=[sys.executable,'-O',str(self.script),str(self.csv)]
        with self.assertRaisesRegex(ValueError,'COMMAND_SCRIPT_INPUT_REQUIRED'):f.refresh()
        self.assertEqual(w.task_assets.script_argument(['bash','-e',str(self.script)]),str(self.script))

    def test_policy_control_file_is_not_a_product_source(self):
        f=self.f;f.plan['criteria'][0]['sources']=[w.task_policy.NAME]
        with self.assertRaisesRegex(ValueError,'GENERATED_SCOPE_INPUT'):f.refresh()

    def test_absolute_external_control_alias_is_rejected(self):
        f=self.f;f.plan['checks'][0]['external_inputs']=[{'kind':'file','path':str(w.task_path(f.root,f.ident))}]
        f.refresh()
        with self.assertRaisesRegex(ValueError,'GENERATED_SCOPE_INPUT'):f.execute()

    def test_prune_does_not_delete_selected_input_snapshots(self):
        f=self.f;a,b=self.imported();f.execute();f.support();w.prune(f.root,f.ident,True)
        self.assertTrue((f.root/a['path']).is_file());self.assertTrue(w.view(f.root,f.ident)['eligible'])

    def test_cleanup_deletes_only_owned_copies_not_external_originals(self):
        f=self.f;a,b=self.imported();f.execute();f.support();w.close(f.root,f.ident,[])
        d=f.doc();d['receipt']['completed_at']=(datetime.now(timezone.utc)-timedelta(days=9)).isoformat();w.save(f.root,d)
        w.cleanup(f.root,f.ident,True)
        self.assertTrue(self.csv.exists());self.assertTrue(self.script.exists())
        self.assertFalse((f.root/a['path']).exists())

    def test_unused_input_slots_are_reclaimed_but_negative_sources_survive(self):
        f=self.f;a,b=self.imported();self.csv.write_text('changed data')
        bad=w.attach(f.root,f.ident,str(self.csv),'input')
        f.plan['checks'][0]['argv'][-1]=str(f.root/bad['path']);f.plan['checks'][0]['input_assets']=[a['attachment'],bad['attachment']];f.refresh();f.execute()
        f.plan['checks'][0]['argv'][-1]=str(f.root/b['path']);f.plan['checks'][0]['input_assets']=[a['attachment'],b['attachment']];f.refresh();f.execute()
        unused=w.attach(f.root,f.ident,str(self.csv),'input');w.prune(f.root,f.ident,True)
        self.assertNotIn(unused['attachment'],f.doc()['attachments'])
        self.assertFalse((f.root/unused['path']).exists())
        self.assertTrue((f.root/bad['path']).exists());self.assertTrue((f.root/a['path']).exists())

    def test_changed_unused_copy_is_not_deleted_by_prune(self):
        f=self.f;a=w.attach(f.root,f.ident,str(self.csv),'input');(f.root/a['path']).write_text('unknown changed bytes')
        before=w.task_path(f.root,f.ident).read_bytes()
        with self.assertRaisesRegex(ValueError,'PRUNE_CHANGED_ASSET'):w.prune(f.root,f.ident,True)
        self.assertEqual(w.task_path(f.root,f.ident).read_bytes(),before);self.assertTrue((f.root/a['path']).exists())

    def test_attachment_budget_and_symlink_refusals_remain(self):
        f=self.f;p=self.ext/'alias';p.symlink_to(self.csv)
        with self.assertRaisesRegex(ValueError,'SYMLINK_INPUT'):w.attach(f.root,f.ident,str(p),'input')
        self.csv.write_bytes(b'x'*(w.MAX_LOG+1))
        with self.assertRaisesRegex(ValueError,'ATTACHMENT_SIZE_LIMIT'):w.attach(f.root,f.ident,str(self.csv),'input')
