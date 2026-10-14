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
