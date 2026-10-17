import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_regression_execution as original
import regression_continuity as continuity
from regression_execution import current_evidence, validate_receipt
from fixes import read_fixes, render_fixes
from impact import digest


class DeviceContinuityTests(unittest.TestCase):
    def setUp(self):
        self.old = original.RegressionExecutionTests()
        self.old.setUp(); self.addCleanup(self.old.doCleanups)
        self.root, self.folder = self.old.root, self.old.folder
        self.old.record()
        self.origin = copy.deepcopy(self.doc()['fixes'][0]['regression_execution_history'][0])
        self.requests = [dict(fix_id='FIX-001', test_id='UT-1', source_index=0,
                              dependencies=['README.md', 'device_test.py'])]
        self.commit('other.py', '# unrelated fixture feature\n')

    def doc(self):
        return json.loads((self.folder / 'fixes.json').read_text())

    def put(self, d):
        (self.folder / 'fixes.json').write_text(json.dumps(d))

    def commit(self, path, value):
        (self.root / path).write_text(value)
        self.git('add', path); self.git('commit', '-m', 'fixture delta')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), '-c', 'user.name=Fixture',
                                        '-c', 'user.email=fixture@example.invalid', *args], stderr=subprocess.DEVNULL).decode().strip()

    def capture(self, requests=None):
        return continuity.capture(self.root, self.folder, self.requests if requests is None else requests)

    def review(self, frozen, verdict='supported'):
        return dict(input_digest=frozen['input_digest'], context='fresh', reviewer='synthetic protocol fixture; not native semantic review',
                    apply_targets=[t['id'] for t in frozen['inputs']['targets']] if verdict == 'supported' else [],
                    findings=[dict(id=t['id'], verdict=verdict,
                                   **{k: 'Synthetic assertion/provenance investigation; see fixture sources' for k in continuity.REVIEW_FIELDS},
                                   changes=[dict(path=x['path'], effect='unaffected' if verdict == 'supported' else 'unknown',
                                                 evidence='Synthetic changed-path explanation, not proof of independence')
                                            for x in frozen['inputs']['changes']]) for t in frozen['inputs']['targets']])

    def apply(self, frozen=None, review=None):
        frozen = frozen or self.capture(); review = review or self.review(frozen)
        a, b = self.folder / 'snapshot.json', self.folder / 'review.json'
        a.write_text(json.dumps(frozen)); b.write_text(json.dumps(review))
        continuity.apply(self.root, self.folder, a, b)
        return frozen, review

    def test_review_retains_original_identity_and_audit_requires_current_gates(self):
        self.apply()
        doc = self.doc(); fix = doc['fixes'][0]
        self.assertEqual(fix['regression_execution_history'][0], self.origin)
        last = fix['regression_execution_history'][-1]
        self.assertEqual(last['schema_version'], 2)
        self.assertNotIn('execution', last['inputs'])
        self.assertTrue(current_evidence(self.root, self.folder, fix, 'UT-1'))
        self.old.helper.script('audit-delivery.py', self.root, 'FEAT-001', expected=1)
        self.old.helper.script('project.py', 'check', self.root)
        self.old.helper.script('audit-delivery.py', self.root, 'FEAT-001')
        summary = continuity.summaries(self.root, self.folder, doc)[0]
        self.assertFalse(summary['new_execution'])
        self.assertEqual(summary['execution_identity']['tested_revision'], self.origin['inputs']['execution']['tested_revision'])
        self.assertEqual(summary['execution_identity']['executed_at'], self.origin['inputs']['execution']['executed_at'])

    def test_changed_shared_file_needs_explicit_review_not_machine_whitelist(self):
        self.commit('README.md', 'fixture original path plus unrelated resource\n')
        frozen = self.capture()
        self.assertIn('README.md', [c['path'] for c in frozen['inputs']['changes']])
        for verdict in ['partial', 'unknown', 'affected']:
            review = self.review(frozen, verdict); review['apply_targets'] = ['FIX-001:UT-1']
            with self.assertRaises(ValueError): self.apply(frozen, review)
        self.apply(frozen)
        self.assertTrue(current_evidence(self.root, self.folder, self.doc()['fixes'][0], 'UT-1'))

    def test_every_changed_path_and_independence_evidence_required(self):
        frozen = self.capture()
        for mutate in [lambda r: r['findings'][0].update(changes=[]),
                       lambda r: r['findings'][0].update(dependency_evidence=''),
                       lambda r: r.update(context='same'),
                       lambda r: r['findings'][0]['changes'][0].update(effect='affected')]:
            review = self.review(frozen); mutate(review)
            with self.assertRaises(ValueError): self.apply(frozen, review)
        self.assertNotIn('regression_continuity_reviews', self.doc())

    def test_dependency_original_assertion_and_dirty_input_fail_closed(self):
        for deps in [[], ['missing.py'], ['../outside'], ['device_test.py', 'device_test.py']]:
            request = dict(self.requests[0], dependencies=deps)
            with self.assertRaises(ValueError): self.capture([request])
        (self.root / 'other.py').write_text('dirty')
        with self.assertRaises(ValueError): self.capture()
        self.git('checkout', '--', 'other.py')
        self.commit('device_test.py', '# changed original assertions\n')
        with self.assertRaisesRegex(ValueError, 'test source'): self.capture()

    def test_original_evidence_or_fix_expectation_changes_cannot_be_reused(self):
        original_doc = self.doc(); original_log = (self.folder / 'evidence/run.txt').read_text()
        (self.folder / 'evidence/run.txt').write_text('different outcome')
        with self.assertRaises(ValueError): self.capture()
        (self.folder / 'evidence/run.txt').write_text(original_log)
        for field, value in [('expected', 'new expectation'), ('status', 'resolved'), ('regression_test_ids', [])]:
            doc = copy.deepcopy(original_doc); doc['fixes'][0][field] = value; self.put(doc)
            with self.assertRaises(ValueError): self.capture()
        self.put(original_doc)

    def test_latest_execution_only_withdrawn_or_invalid_source_rejected(self):
        doc = self.doc(); fix = doc['fixes'][0]
        newer = copy.deepcopy(self.origin); newer['inputs']['execution']['executed_at'] = '2026-10-14T10:00:00Z'
        newer['input_digest'] = digest(newer['inputs']); newer['review']['input_digest'] = newer['input_digest']
        newer['receipt_digest'] = digest({k: v for k, v in newer.items() if k != 'receipt_digest'})
        fix['regression_execution_history'].append(newer); self.put(doc)
        with self.assertRaisesRegex(ValueError, 'latest original'): self.capture()
        newer['inputs']['execution']['skipped_cases'] = ['null_nickname']
        newer['input_digest'] = digest(newer['inputs']); newer['review']['input_digest'] = newer['input_digest']
        newer['receipt_digest'] = digest({k: v for k, v in newer.items() if k != 'receipt_digest'}); self.put(doc)
        with self.assertRaises(ValueError): self.capture([dict(self.requests[0], source_index=1)])

    def test_capture_and_apply_drift_never_partially_save(self):
        frozen = self.capture(); original_doc = self.doc()
        self.commit('other.py', '# later unrelated change\n')
        with self.assertRaises(ValueError): self.apply(frozen)
        self.assertEqual(original_doc, self.doc())
        frozen = self.capture(); original_capture = continuity.capture
        def moving(*a, **kw):
            result = original_capture(*a, **kw)
            (self.folder / 'evidence/run.txt').write_text('changed during apply')
            return result
        with patch.object(continuity, 'capture', side_effect=moving):
            with self.assertRaises(ValueError): self.apply(frozen)
        self.assertEqual(original_doc, self.doc())

    def test_events_references_and_original_tampering_are_not_ignored(self):
        self.apply(); original_doc = self.doc()
        for mutate in [lambda d: d.update(regression_continuity_reviews=[]),
                       lambda d: d['regression_continuity_reviews'][0]['review'].update(reviewer='tampered'),
                       lambda d: d['fixes'][0]['regression_execution_history'][-1]['inputs'].update(test_id='OTHER'),
                       lambda d: d['fixes'][0]['regression_execution_history'][0]['inputs']['execution'].update(executed_at='changed')]:
            doc = copy.deepcopy(original_doc); mutate(doc); self.put(doc)
            with self.assertRaises(ValueError): read_fixes(self.folder, 'FEAT-001')
        self.put(original_doc)

    def test_new_evidence_can_be_reviewed_from_original_without_derived_chain(self):
        self.apply(); doc = self.doc()
        with self.assertRaises(ValueError): self.capture([dict(self.requests[0], source_index=1)])
        self.commit('other.py', '# next unrelated feature\n')
        self.apply()
        doc = self.doc()
        self.assertEqual(len(doc['fixes'][0]['regression_execution_history']), 3)
        self.assertEqual(doc['fixes'][0]['regression_execution_history'][2]['inputs']['source_index'], 0)
        continuity.validate_document(doc)

    def test_currentness_changes_but_workflow_only_commit_preserves_target(self):
        self.apply(); fix = self.doc()['fixes'][0]
        self.git('add', '.agent-workflow'); self.git('commit', '-m', 'workflow only')
        self.assertTrue(current_evidence(self.root, self.folder, fix, 'UT-1'))
        self.commit('other.py', '# changed after review\n')
        with self.assertRaisesRegex(ValueError, 'target tree changed'):
            current_evidence(self.root, self.folder, fix, 'UT-1')
        self.assertEqual(continuity.summaries(self.root, self.folder, self.doc())[0]['status'], 'stale')

    def test_duplicate_and_multi_fix_partial_subset_are_explicit(self):
        doc = self.doc(); fix = copy.deepcopy(doc['fixes'][0]); fix['id'] = 'FIX-002'
        for entry in fix['regression_execution_history']:
            entry['inputs']['fix_id'] = 'FIX-002'; entry['inputs']['fix']['id'] = 'FIX-002'
            entry['input_digest'] = digest(entry['inputs']); entry['review']['input_digest'] = entry['input_digest']
            entry['receipt_digest'] = digest({k: v for k, v in entry.items() if k != 'receipt_digest'})
        doc['fixes'].append(fix); self.put(doc)
        requests = self.requests + [dict(self.requests[0], fix_id='FIX-002')]
        frozen = self.capture(requests); review = self.review(frozen)
        review['findings'][1]['verdict'] = 'partial'; review['apply_targets'] = ['FIX-001:UT-1']
        self.apply(frozen, review)
        self.assertEqual([len(f['regression_execution_history']) for f in self.doc()['fixes']], [2, 1])
        frozen2 = self.capture(requests)
        with self.assertRaisesRegex(ValueError, 'already applied'): self.apply(frozen2, review)

    def test_render_and_old_receipt_reader_refuse_silent_upgrade(self):
        self.apply(); render_fixes(self.folder, 'FEAT-001')
        self.assertIn('not executions', (self.folder / 'fixes.md').read_text())
        entry = self.doc()['fixes'][0]['regression_execution_history'][-1]
        from types import ModuleType
        # Load the actual released reader's validator only; it rejects version 2 before any imports/calls.
        code = subprocess.check_output(['git', 'show', 'c117f70:skills/dev/core/scripts/regression_execution.py'], cwd=Path(__file__).resolve().parents[1], text=True)
        import ast
        tree = ast.parse(code); node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'validate_receipt')
        module = ModuleType('old_validator'); module.digest = digest
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<released-validator>', 'exec'), module.__dict__)
        with self.assertRaisesRegex(ValueError, 'invalid regression execution receipt'): module.validate_receipt(entry)
    def test_assume_unchanged_and_symlinks_cannot_hide_inputs(self):
        self.git('update-index', '--assume-unchanged', 'README.md')
        original_data = (self.root / 'README.md').read_bytes()
        (self.root / 'README.md').write_text('hidden different bytes')
        with self.assertRaisesRegex(ValueError, 'actual input differs'):
            self.capture()
        (self.root / 'README.md').write_bytes(original_data)
        self.git('update-index', '--no-assume-unchanged', 'README.md')
        (self.root / 'alias').symlink_to('README.md')
        self.git('add', 'alias'); self.git('commit', '-m', 'symlink input')
        with self.assertRaisesRegex(ValueError, 'symlink input'):
            self.capture()

    def test_unrelated_decision_change_is_reviewed_but_not_ignored_after_apply(self):
        (self.folder / 'decisions.json').write_text(json.dumps({'decisions': [{'id': 'D-OTHER', 'status': 'approved', 'question': 'Independent feature'}]}))
        self.apply()
        doc = self.doc(); self.assertTrue(current_evidence(self.root, self.folder, doc['fixes'][0], 'UT-1'))
        (self.folder / 'decisions.json').write_text(json.dumps({'decisions': []}))
        self.assertFalse(current_evidence(self.root, self.folder, doc['fixes'][0], 'UT-1'))

    def test_historical_regression_discovery_keeps_test_links_and_original_revision(self):
        from regression_review import discover
        before = discover(self.root, 'FEAT-001')
        self.apply()
        after = discover(self.root, 'FEAT-001')
        self.assertEqual(before, after)
        self.assertEqual(self.doc()['fixes'][0]['regression_test_ids'], ['UT-1'])

    def test_current_failed_evidence_cannot_be_bypassed_by_original_green(self):
        (self.folder / 'verification.json').write_text(json.dumps({'items': [{'test_ids': ['UT-1'], 'history': [{'status': 'failed'}]}]}))
        with self.assertRaisesRegex(ValueError, 'current verification failure'):
            self.capture()
        (self.folder / 'verification.json').unlink()
        (self.folder / 'regression-review.json').write_text(json.dumps({'dispositions': [{'candidate_id': 'FEAT-001:FIX-001', 'result': {'status': 'failed'}}]}))
        with self.assertRaisesRegex(ValueError, 'current regression failure'):
            self.capture()

    def test_changed_fix_contract_stales_review_without_corrupting_history(self):
        self.apply(); original_doc = self.doc()
        changed = copy.deepcopy(original_doc)
        changed['fixes'][0]['regression_test_ids'] = []
        changed['fixes'][0]['regression_waiver'] = 'Fixture approved scope change; not an old pass'
        self.put(changed)
        continuity.validate_document(changed)
        self.assertEqual(continuity.summaries(self.root, self.folder, changed)[0]['status'], 'stale')
        self.put(original_doc)
        # New real executions must not silently preserve a corrupted event ledger.
        original_doc['regression_continuity_reviews'][0]['review']['reviewer'] = 'changed'
        self.put(original_doc)
        from regression_execution import capture
        with self.assertRaisesRegex(ValueError, 'event changed'):
            capture(self.root, self.folder, 'FIX-001', 'UT-1', self.old.execution)


class ContinuityReaderIntegrationTests(unittest.TestCase):
    def setUp(self):
        import test_verification
        self.helper = test_verification.VerificationTests(); self.helper.setUp(); self.addCleanup(self.helper.doCleanups)
        self.root, self.folder = self.helper.root.resolve(), self.helper.folder.resolve()
        # Complete fixture facts sufficient for the regular source inventory/view pipeline.
        head = self.helper.git('rev-parse', 'HEAD').strip()
        doc = {'feature_id': 'FEAT-001', 'fixes': [dict(id='FIX-001', status='verified',
               expected='Return uppercase text', regression_test_ids=['UT-1'], requirement_ids=['R-1'],
               code_paths=['convert.py'], evidence=['private-original-evidence-marker'])]}
        (self.folder / 'fixes.json').write_text(json.dumps(doc))
        (self.folder / 'evidence').mkdir(exist_ok=True)
        (self.folder / 'evidence/run.txt').write_text('Synthetic executed fixture assertion success')
        (self.folder / 'evidence/package.txt').write_text('Synthetic full image digest ' + 'a' * 64 + '; source ' + head)
        execution = dict(kind='device', status='passed', returncode=0, tested_revision=head,
                         executed_at='2026-10-13T10:00:00Z', command=['fixture-device-runner', 'uppercase'],
                         executed_cases=['uppercase'], failed_cases=[], skipped_cases=[], test_files=['convert.py'],
                         evidence_refs=['evidence/run.txt'], package_identity_refs=['evidence/package.txt'],
                         environment='synthetic device only', coverage='synthetic uppercase assertion')
        from regression_execution import capture, apply
        snap = capture(self.root, self.folder, 'FIX-001', 'UT-1', execution)
        a, b = self.folder / 'exec-snapshot.json', self.folder / 'exec-review.json'
        a.write_text(json.dumps(snap)); b.write_text(json.dumps(dict(input_digest=snap['input_digest'], status='supported', reviewer='fixture', assertion_evidence='fixture case', original_identity_evidence='fixture package', routine_check_reason='fixture device')))
        apply(self.root, self.folder, a, b)
        (self.root / 'unrelated.py').write_text('# unrelated fixture\n')
        self.helper.git('add', 'unrelated.py'); self.helper.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'unrelated')
        request = [dict(fix_id='FIX-001', test_id='UT-1', source_index=0, dependencies=['convert.py'])]
        snap = continuity.capture(self.root, self.folder, request)
        review = DeviceContinuityTests.review(self, snap)
        a.write_text(json.dumps(snap)); b.write_text(json.dumps(review)); continuity.apply(self.root, self.folder, a, b)

    def test_final_claim_review_and_stage_view_bind_continuity_and_detect_stale(self):
        from claim_review import identity, validate
        from stage_view import capture
        first = identity(self.root, self.folder)
        self.assertEqual(first['device_continuity'][0]['status'], 'current')
        view = capture(self.root, 'FEAT-001', 'verify')
        self.assertFalse(view['device_continuity'][0]['new_execution'])
        event = json.loads((self.folder / 'fixes.json').read_text())['regression_continuity_reviews'][0]
        self.assertNotIn('private-original-evidence-marker', json.dumps(event))
        review = dict(feature_id='FEAT-001', input_digest=first['input_digest'], reviewer='fixture',
                      findings=[dict(id=x['id'], verdict='supported', source_basis='fixture', required_scope='fixture',
                                     observed_scope='fixture', evidence_ref='fixture', counterexample_check='fixture') for x in first['claims']])
        (self.folder / 'claim-review.json').write_text(json.dumps(review))
        self.assertEqual(validate(self.root, self.folder), [])
        decisions = json.loads((self.folder / 'decisions.json').read_text()); decisions['decisions'].append({'id': 'D-NEW', 'status': 'pending'})
        (self.folder / 'decisions.json').write_text(json.dumps(decisions))
        second = identity(self.root, self.folder)
        self.assertEqual(second['device_continuity'][0]['status'], 'stale')
        self.assertNotEqual(first['input_digest'], second['input_digest'])
        self.assertTrue(validate(self.root, self.folder))
        view = capture(self.root, 'FEAT-001', 'verify')
        self.assertTrue(any('device_continuity_stale' in x for x in view['global_attention']))

    def test_status_and_render_expose_review_not_new_execution(self):
        output = self.helper.run_script('feature-status.py', self.root, 'FEAT-001')
        self.assertIn('no new execution', output)
        render_fixes(self.folder, 'FEAT-001')
        self.assertIn('Reviewed device continuities (not executions): 1', (self.folder / 'fixes.md').read_text())
        self.assertIn('original execution', (self.folder / 'fixes.md').read_text())
        (self.folder / 'decisions.json').write_text(json.dumps({'decisions': [{'id': 'D-NEW', 'status': 'pending'}]}))
        render_fixes(self.folder, 'FEAT-001')
        self.assertIn('FIX-001/UT-1: stale', (self.folder / 'fixes.md').read_text())


if __name__ == "__main__":
    unittest.main()
