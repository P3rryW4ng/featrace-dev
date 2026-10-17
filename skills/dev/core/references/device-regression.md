# Executed device regression and routine gate enrollment (0.12.1)

Use when a verified fix has a declared regression test that actually ran on a selected device but cannot safely run as a routine project gate. Keep its `regression_test_ids`: device requirements are not a reason to erase FIX → TEST linkage or waive this delivery's observed regression. Existing passed gate coverage remains valid and preferred for routinely executable tests.

## Evidence and scope

First inspect the archived runner output, exact assertions/cases, device/environment, installed app/test package identity and original tested source tree. Compilation, an exit-zero command with skipped target cases, a fabricated case list or a package built but not installed cannot establish execution. Preserve output and identity artifacts under the feature's `evidence/`; redact secrets with an explicit note. A truncated hash is not full byte equality. Record limits precisely; runtime method tests do not automatically cover JS/container dispatch.

Keep test IDs declared by the affected requirements or a justified existing `regression_scope_notes` link. Update the fix's current routine-enrollment explanation before capture and preserve earlier waiver wording as history. A routine limitation explains why this test is not a daily gate; it is not a behavior waiver and grants no installation, uninstall, language-change or device authorization.

Create an execution JSON from actual output (place disposable input/snapshot/review in authorized ignored scratch):

```json
{
  "kind": "device", "status": "passed", "returncode": 0,
  "tested_revision": "<full available tested commit>", "executed_at": "<actual timestamp>",
  "command": ["adb", "-s", "<selected device>", "shell", "am", "instrument", "<actual arguments>"],
  "executed_cases": ["<exact asserted regression case>"], "failed_cases": [], "skipped_cases": [],
  "test_files": ["<tracked actual test source>"],
  "evidence_refs": ["evidence/device-regression/run.txt"],
  "package_identity_refs": ["evidence/device-regression/package-identity.txt"],
  "environment": "<device/API/setup actually used>",
  "coverage": "<assertions, branches and explicit uncovered boundaries>"
}
```

This conservative path requires the non-workflow project tree to equal the tested commit, including tracked test sources. A changed tree needs affected-regression investigation/testing; this helper does not implement test-result continuity across code changes. Old worktree-built packages need archived substantiation of their relationship to the named commit, not a new execution timestamp or a recording commit substituted for the tested revision.

## Capture, inspect, apply

```text
python3 core/scripts/regression_execution.py capture <PROJECT> <ID> --fix <FIX-ID> --test <TEST-ID> --execution <execution.json>
```

Save stdout as a snapshot. Inspect the frozen execution, artifacts, original package/tree identity and exact assertion coverage. A qualified reviewer returns:

```json
{
  "input_digest": "<snapshot input_digest>", "status": "supported",
  "reviewer": "<actual reviewer>",
  "assertion_evidence": "<archived output/assertions support this fix; no skipped required case>",
  "original_identity_evidence": "<actual build/install provenance and limits>",
  "routine_check_reason": "<why selected-device execution remains separate from routine gate>"
}
```

This review is an inspected attestation, not a cryptographic identity certificate or machine parser of every test framework. Never generate supported prose merely to make audit pass. Unsupported/partial execution needs the missing targeted check or a genuine authorized behavior waiver. A fresh reviewer is appropriate if provenance or coverage is disputed; this helper does not require an extra Agent for every ordinary already-clear device run.

```text
python3 core/scripts/regression_execution.py apply <PROJECT> <ID> --snapshot <snapshot.json> --review <review.json>
```

Application rechecks the complete frozen inputs before saving, appends `regression_execution_history` to that fix and preserves the TEST IDs. Audit can accept this current device receipt for a FIX test that is not selected by a passed ordinary gate. Other quality reports, baseline bindings, acceptance coverage and normal completion checks remain mandatory. The helper runs no test and sets no feature status. Later code, relevant authority, fix contract or referenced artifact changes invalidate the receipt; unrelated index text is not included unless it is itself a referenced execution artifact. Existing records with no device receipts remain compatible.

If required original execution/build/install material exists only in authorized ignored scratch, and adding it would stale current unrelated carry rows, use the explicit archive-addition path in `evidence-annotations.md`: freeze before archive/index edits and obtain one bounded fresh-context review. Do not erase TEST linkage, treat raw logs as annotations or repeat all unrelated carry reviews. Register the device receipt only after durable provenance and accurate full/prefix comparison wording are reconciled.

## Reviewed applicability after unrelated changes (0.16.0)

If the original run is complete and trustworthy but the current tree differs, do not re-sign the execution. The optional internal helper `regression_continuity.py` can freeze one feature's explicit FIX/TEST requests for a new-context read-only applicability review. This is not another device run or an automatic waiver. Prefer an authorized targeted rerun when recovering or reviewing evidence would cost more. Related behavior changes, unknown provenance or environment, missing cases and partial support still require the missing evidence.

A request array contains `fix_id`, `test_id`, `source_index` (the latest **original** execution for that TEST), and nonempty investigated `dependencies` paths. Test sources and registered FIX code paths are also checked. No directory/extension whitelist establishes independence; inspect every changed path, direct/transitive calls, resources, global initialization, build/test assembly and original environment. A shared file's unrelated addition may be supported only with specific unchanged-path evidence. Changed original test assertions cannot be carried by this mechanism. Original device-only failures with unexplained mechanisms may remain unknown.

```text
python3 core/scripts/regression_continuity.py capture <PROJECT> <ID> --requests <ignored-request.json>
```

Save stdout in the authorized ignored scratch location. Read the snapshot's original receipt locators in `fixes.json`, original archived artifacts/package identity, current fix/requirement/task/decision records, actual dependency contents, and the **complete** Git diff for each original `tested_revision` versus `target_revision` (use `--no-ext-diff --no-textconv`). The snapshot stores hashes/locators rather than copying original private evidence. Do not send raw device/account identifiers in review prose. Hashes do not prove package provenance, dependency completeness, reviewer independence or execution truth.

The qualified fresh-context reviewer supplies the matching `input_digest`, `context: "fresh"`, real `reviewer`, and exactly one finding per snapshot target ID. Each finding has `verdict` (`supported`, `affected`, `unknown`, `partial`), nonempty `assertion_evidence`, `original_identity_evidence`, `dependency_evidence`, `authority_evidence`, `environment_evidence`, `counterexample_check`, and `limits`. Its `changes` array must assess **every** snapshot changed path exactly once with `path`, `effect` (`unaffected`, `affected`, `unknown`) and concrete `evidence`; supported cannot contain affected/unknown paths. `apply_targets` explicitly lists only fully supported FIX/TEST IDs; a partially supported batch is not all green. Reviewer/context strings are attestations, not machine proof of independence. Do not write supported fixture prose as a substitute for an actual reviewer.

```text
python3 core/scripts/regression_continuity.py apply <PROJECT> <ID> --snapshot <frozen.json> --review <review.json>
```

Application freezes/rechecks the full current business tree, investigates related contracts, binds current decisions/source authority/regression review and exact origin artifacts, and atomically appends one shared event with version-2 typed references in `regression_execution_history`. Schema-1 execution history, tested revision/time/command/package provenance and FIX→TEST IDs stay unchanged. The new event proves reviewed applicability to a code target, not installation or runtime success of a new device package. The ordinary quality report, actual current checks and final independent claim review remain required. Pure workflow commits can preserve the same reviewed business target; subsequent code or bound evidence/contract changes expire applicability. A later new execution may supersede this review without deleting it. A subsequent applicability review must return to the latest original run, never use a derived continuity as its source or skip a newer withdrawal/failure.

Readers that only support version-1 execution receipts must reject new entries for acceptance/delivery; do not backport them by editing version/hash fields. New readers accept old records without automatic migration. Render/status/stage views and final review must expose original execution versus current review and stale inputs. This mechanism does not change global manual-evidence digests or allow automatic gate reuse. Temporary request/snapshot/review inputs are not an evidence archive; original execution/package evidence must already be durable.
