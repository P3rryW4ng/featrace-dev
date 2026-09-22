import copy
import json
import unittest
import test_impact
from module_context import plan, review, catalog, validate_modules, render_graph
from feature_scope import set_scope, not_applicable, validate_scope, suggest


class ModuleTests(unittest.TestCase):
    write = test_impact.ImpactTests.write
    run_script = test_impact.ImpactTests.run_script
    git = test_impact.ImpactTests.git
    save = test_impact.ImpactTests.save

    def setUp(self):
        test_impact.ImpactTests.setUp(self)
        self.root = self.root.resolve(); self.folder = self.folder.resolve()
        self.modules = self.root / '.agent-workflow/modules'; self.modules.mkdir()
        (self.root / 'build.cfg').write_text('root configuration')
        for name in ('wallet', 'identity', 'app', 'chat'):
            (self.root / name).mkdir()
            (self.root / name / 'code.txt').write_text(name)
        self.git('add', 'build.cfg', 'wallet', 'identity', 'app', 'chat')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'modules')
        self.index = {'schema_version': 1, 'shared_stack': 'Fixture language; see build.cfg', 'global_files': ['build.cfg'], 'modules': [
            {'id': name, 'summary': name + ' behavior', 'roots': [name], 'evidence_files': [], 'depends_on': deps}
            for name, deps in [('wallet', ['identity']), ('identity', []), ('app', ['wallet']), ('chat', [])]]}
        self.save_index()

    def save_index(self):
        (self.modules / 'index.json').write_text(json.dumps(self.index))

    def body(self, name):
        return {'module_id': name, 'gaps': [], 'feature_ids': ['FEAT-001'], **{
            key: [{'detail': key + ' observed in fixture', 'evidence_files': [name + '/code.txt']}]
            for key in ('technology', 'behaviors', 'entry_points', 'state_lifecycle', 'tests')}}

    def accept(self, name):
        row = next(r for r in plan(self.root, [name]) if r['module'] == name)
        review(self.root, name, self.body(name), row['digest'])

    def accept_scope(self):
        for name in ('wallet', 'identity', 'app'):
            self.accept(name)

    def test_plan_scopes_dependencies_and_callers_without_unrelated_module(self):
        rows = plan(self.root, ['wallet'])
        self.assertEqual({r['module'] for r in rows}, {'wallet', 'identity', 'app'})
        self.assertTrue(all(r['status'] == 'unreviewed' for r in rows))
        self.assertFalse(any('chat/code.txt' in r['scope_files'] for r in rows))

    def test_review_generates_dossiers_and_global_overview(self):
        self.accept_scope()
        self.assertTrue(all(r['status'] == 'current' for r in plan(self.root, ['wallet'])))
        self.assertIn('technology observed', (self.modules / 'wallet.md').read_text())
        self.assertIn('shared_stack', (self.modules / 'index.json').read_text())
        self.assertIn('chat behavior', (self.modules / 'index.md').read_text())

    def test_new_deleted_and_modified_files_stale_only_relevant_module(self):
        self.accept_scope()
        (self.root / 'wallet/new.txt').write_text('new path')
        rows = {r['module']: r for r in plan(self.root, ['wallet'])}
        self.assertEqual(rows['wallet']['status'], 'stale')
        self.assertIn('wallet/new.txt', rows['wallet']['changed_paths'])
        self.assertEqual(rows['identity']['status'], 'current')
        (self.root / 'wallet/code.txt').unlink()
        rows = {r['module']: r for r in plan(self.root, ['wallet'])}
        self.assertIn('wallet/code.txt', rows['wallet']['changed_paths'])

    def test_unrelated_commit_does_not_stale_modules(self):
        self.accept_scope()
        (self.root / 'chat/code.txt').write_text('unrelated chat change')
        self.git('add', 'chat')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'chat update')
        self.assertTrue(all(r['status'] == 'current' for r in plan(self.root, ['wallet'])))

    def test_global_configuration_change_stales_all_selected(self):
        self.accept_scope()
        (self.root / 'build.cfg').write_text('new build settings')
        self.assertTrue(all(r['status'] == 'stale' for r in plan(self.root, ['wallet'])))

    def test_stale_review_token_and_outside_evidence_rejected(self):
        row = next(r for r in plan(self.root, ['wallet']) if r['module'] == 'wallet')
        (self.root / 'wallet/code.txt').write_text('changed')
        with self.assertRaises(ValueError):
            review(self.root, 'wallet', self.body('wallet'), row['digest'])
        row = next(r for r in plan(self.root, ['wallet']) if r['module'] == 'wallet')
        body = self.body('wallet'); body['technology'][0]['evidence_files'] = ['chat/code.txt']
        with self.assertRaises(ValueError):
            review(self.root, 'wallet', body, row['digest'])

    def test_doc_tamper_and_known_gaps_are_not_current(self):
        self.accept('wallet')
        path = self.modules / 'wallet.json'; doc = json.loads(path.read_text())
        doc['body']['behaviors'][0]['detail'] = 'unreviewed interpretation'
        path.write_text(json.dumps(doc))
        self.assertEqual(next(r for r in plan(self.root, ['wallet']) if r['module']=='wallet')['status'], 'stale')
        token = next(r for r in plan(self.root, ['wallet']) if r['module']=='wallet')['digest']
        body = self.body('wallet'); body['gaps'] = ['Unknown navigation behavior']
        review(self.root, 'wallet', body, token)
        self.assertEqual(next(r for r in plan(self.root, ['wallet']) if r['module']=='wallet')['status'], 'gaps')

    def test_feature_gate_opt_in_and_cli_selection(self):
        self.req['feature'].update(module_context_required=True, modules=['wallet'])
        self.write('spec/requirements.json', self.req)
        self.assertTrue(validate_modules(self.root, self.folder, self.req, 'check'))
        self.assertTrue(validate_modules(self.root, self.folder, self.req, 'develop'))
        self.accept_scope()
        self.assertFalse(validate_modules(self.root, self.folder, self.req, 'develop'))
        self.assertFalse(validate_modules(self.root, self.folder, self.req, 'check'))
        self.run_script('module_context.py', 'plan', self.root, '--feature', 'FEAT-001')

    def test_new_workflow_requires_module_choice_or_reason_when_catalog_exists(self):
        self.req['feature']['workflow_version'] = 2
        self.assertTrue(any('module catalog exists' in e for e in validate_modules(self.root, self.folder, self.req, 'develop')))
        self.req['feature']['module_context_required'] = False
        self.assertTrue(any('module_context_note' in e for e in validate_modules(self.root, self.folder, self.req, 'develop')))
        self.req['feature']['module_context_note'] = 'Change only updates repository documentation; no registered runtime module applies'
        self.assertFalse(validate_modules(self.root, self.folder, self.req, 'develop'))
        self.req['feature']['workflow_version'] = '2'
        self.assertTrue(any('workflow_version' in e for e in validate_modules(self.root, self.folder, self.req, 'develop')))

    def test_bad_catalog_paths_and_dependency_rejected(self):
        original = copy.deepcopy(self.index)
        for key, value in [('roots', ['../outside']), ('depends_on', ['unknown'])]:
            self.index = copy.deepcopy(original); self.index['modules'][0][key] = value; self.save_index()
            with self.assertRaises(ValueError): catalog(self.root)
        self.index = original; self.save_index()
        (self.root / 'wallet/code.txt').unlink()
        (self.root / 'wallet/code.txt').symlink_to('/etc/hosts')
        with self.assertRaises(ValueError): plan(self.root, ['wallet'])

    def test_dependency_cycles_terminate(self):
        self.index['modules'][1]['depends_on'] = ['wallet']; self.save_index()
        self.assertEqual(len(plan(self.root, ['wallet'])), 3)

    def test_confirmed_capability_records_distinct_module_roles_and_graph(self):
        scope = {'capability': {'id': 'red-envelope', 'name': '红包'}, 'assignments': [
            {'module_id': 'wallet', 'role': 'owner', 'responsibility': 'Own amount and state rules',
             'evidence_refs': ['wallet/code.txt']},
            {'module_id': 'chat', 'role': 'host', 'responsibility': 'Display the envelope in conversations',
             'evidence_refs': ['chat/code.txt']},
        ], 'note': 'Confirmed from product scope and current code'}
        self.req['feature']['workflow_version'] = 3
        self.write('spec/requirements.json', self.req)
        set_scope(self.root, 'FEAT-001', scope)
        req = json.loads((self.folder / 'spec/requirements.json').read_text())
        self.assertEqual(req['feature']['modules'], ['wallet', 'chat'])
        self.assertEqual(req['feature']['module_scope']['assignments'][0]['role'], 'owner')
        self.assertFalse(validate_scope(self.root, req['feature'], 'develop'))
        for name in ('wallet', 'identity', 'app', 'chat'):
            self.accept(name)
        self.run_script('validate-feature.py', '--stage', 'develop', self.root, 'FEAT-001')
        graph = render_graph(self.root)
        self.assertIn('capability:red-envelope', {node['id'] for node in graph['nodes']})
        self.assertEqual({edge['relation'] for edge in graph['edges'] if edge['from'] == 'capability:red-envelope'}, {'owner', 'host'})
        self.assertIn('business capability', (self.modules / 'graph.md').read_text())
        self.assertIn('red-envelope', (self.modules / 'graph.json').read_text())

    def test_workflow_v3_pending_unknown_and_not_applicable_scope(self):
        feature = {'id': 'FEAT-001', 'workflow_version': 3,
                   'module_scope': {'status': 'pending', 'capability': None, 'assignments': [], 'note': ''}}
        self.assertFalse(validate_scope(self.root, feature, 'draft'))
        self.assertTrue(any('need confirmation' in value for value in validate_scope(self.root, feature, 'develop')))
        self.req['feature'].update(feature)
        self.write('spec/requirements.json', self.req)
        not_applicable(self.root, 'FEAT-001', 'Documentation-only change with no runtime module')
        req = json.loads((self.folder / 'spec/requirements.json').read_text())
        self.assertFalse(validate_scope(self.root, req['feature'], 'develop'))
        bad = {'capability': {'id': 'red-envelope', 'name': '红包'}, 'assignments': [
            {'module_id': 'unknown', 'role': 'owner', 'responsibility': 'Unknown', 'evidence_refs': ['source']}]}
        with self.assertRaises(ValueError):
            set_scope(self.root, 'FEAT-001', bad)

    def test_scope_suggestion_uses_registered_code_paths_without_claiming_semantics(self):
        trace = json.loads((self.folder / 'traceability.json').read_text())
        trace['links'][0]['code'] = ['wallet/code.txt']
        self.write('traceability.json', trace)
        result = suggest(self.root, 'FEAT-001')
        wallet = next(row for row in result['candidates'] if row['module_id'] == 'wallet')
        chat = next(row for row in result['candidates'] if row['module_id'] == 'chat')
        self.assertEqual(wallet['matched_code_paths'], ['wallet/code.txt'])
        self.assertEqual(chat['matched_code_paths'], [])
        self.assertIn('candidates only', result['note'])
