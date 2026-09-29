# Delivery report — FEAT-001 Independent catalog and event importers

Status: reviewed local delivery report (written 2026-09-29 as a Deliver-record continuation; no tests/builds were re-run while writing it; read-only currency checks are listed below).
Feature status in `spec/requirements.json`: `complete` (existing value, not changed by this report).

## Accepted revision and code identity

- Base / HEAD commit: `69a66badf72164c34bf2a9e49e5cf050cb11d288` (`test: complete synthetic parser contract assertions`).
- The delivered code is **not committed**. It is the uncommitted working tree on that HEAD, with nothing staged:
  - `upper.py` sha256 `04cc7c9bf3aa40b1847f32517eb8fc44f1de28b8cfe9a5479e135c8a1fdde7c2`
  - `lower.py` sha256 `168cad22cff88e0476cabdce7e99deb809e8338bab1824a9741288d85a2faa26`
  - `tests/test_contract.py` sha256 `3dbad9b96c0d21fb59396cf06b76686bd6a4fe3ed375e55b9f558cded9c62755`
- When this report was written, these hashes matched the identity recorded in `verification.json`, `fixes.json` and `regression-review.json`. The working tree showed only these 3 modified files (135 insertions, 2 deletions vs HEAD). The full `git diff` output hashed to sha256 `a85b1fa7c734dcb89f92a8dbcac08e890aa6d890b1ac3a81f1b4af16b7da5446`.
- Verification evidence digest: `d1de458427f53b5c25fff4a4377d11b762dcf2a0970ae5691abd03031a20108a`.
- The commit hash alone does not identify the accepted code. Acceptance applies only to HEAD plus the file hashes above.

## Sources and requirements

- Source: `sources/prd-original.txt` (sha256 `2d00bc96…ae2e3`), the approved CSV (T-UP) and JSONL (T-LOW) contract. Figma and API are `not_applicable` (local functions only).
- PRD intake inventory is complete. Source item S-1 maps to R-1, reviewed at stage `develop` by `fixture-author` on 2026-09-29T03:09:48Z.
- R-1 "Local importers" is `confirmed` and has three acceptance criteria: CSV rules, JSONL rules, and order/no external effects/no shared mutable state.
- Decisions: none recorded (`decisions.json` is empty). No clarifications are pending.
- Tasks: T-UP (CSV importer, `upper.py`) and T-LOW (JSONL importer, `lower.py`) are both `done`. The task semantic review is current (digest `ff8a0284…49af`, 2 prior reviews).
- Traceability: R-1 → T-UP, T-LOW → TEST-UP, TEST-LOW → `upper.py`, `lower.py`.
- Note: `tasks.json.test_evidence` preserves the adoption-time "Ran 25 tests" and worktree diff `e7fd580a…5330`, and appends the Repair notes and named regressions with a reference to the fresh run in `verification.json`. Those 25-test results are history; the current 28-test result and accepted identity are listed below and above respectively.

## Failure history (preserved)

1. **Adoption runs, 2026-09-29T07:27:09Z / 07:33:34Z / 07:37:29Z.** Automatic `parser-all` passed with 25 tests (digests `7cd1cc4e…` and `4b89d049…`).
2. **Agent technical review, 2026-09-29T07:37:49Z–07:37:50Z, digest `4b89d049…`.** This review recorded **failed** manual rows for requirement R-1:2 (JSONL), R-1:3 (no external effects), impact B-1 and impact B-PRESERVE. The automatic tests were still passing at that point, but did not catch these defects. The counterexamples became:
   - **FIX-001**: JSONL accepted the non-JSON tokens `NaN`/`Infinity`/`-Infinity` as payload. Expected result: `invalid_json`.
   - **FIX-002**: JSONL timestamps accepted non-ASCII Unicode digits (Arabic-Indic), because `\d` was used without `re.ASCII`.
   - **FIX-003**: `upper.convert` set the caller's thread-local decimal `InvalidOperation` flag when a price was malformed. This is an external effect.
3. **Repair.** All three are `implementation_defect`:
   - `lower.py` now uses `json.loads(..., parse_constant=_reject_constant)` and compiles `_TIMESTAMP` with `re.ASCII`.
   - `upper._parse_price` now runs inside `decimal.localcontext(Context())`.
   - Three regression tests were added to `tests/test_contract.py`. Existing assertions were not changed.
   - The fix records say the new tests failed against the pre-repair code, reconstructed in a disposable scratch copy outside the project (5 subtest/test failures), and pass on the repaired code.
4. **Re-verification, 2026-09-29T07:47:32Z (automatic) and 07:48:09Z (manual), digest `d1de4584…`.** All 6 verification rows are passed. FIX-001, FIX-002 and FIX-003 are `verified`, with 0 unresolved.

## Verification evidence (as recorded; not re-run for this report)

| Row | Method | Result | Recorded at (UTC) |
|---|---|---|---|
| gate:parser-all | automatic: `python3 -m unittest discover -s tests` | passed, returncode 0, "Ran 28 tests … OK" | 2026-09-29T07:47:32Z (quality-report executed 07:47:32.212Z) |
| requirement R-1:1 (CSV rules) | automatic (same parser-all run) | passed | 2026-09-29T07:47:32Z |
| requirement R-1:2 (JSONL rules) | manual = Agent technical inspection + bounded in-process repro + inspected parser-all assertions | passed | 2026-09-29T07:48:09Z |
| requirement R-1:3 (order / no effects / no shared state) | manual = Agent technical inspection + bounded repro | passed | 2026-09-29T07:48:09Z |
| impact B-1 (changed behavior) | manual = Agent technical inspection | passed | 2026-09-29T07:48:09Z |
| impact B-PRESERVE (pure independent interfaces) | manual = Agent technical inspection | passed | 2026-09-29T07:48:09Z |

- **Automated evidence** is limited to the unittest run above: 28 tests, including the 3 FIX regression tests.
- **"Manual" rows** are Agent technical evidence: code reading plus in-process reproduction by the Agent, on Python 3.9.6 with `PYTHONDONTWRITEBYTECODE=1`, on this single host. They are **not** user acceptance, and no user or device observation took place. This feature has no UI, device or installation component.
- **Historical regression:** 3 candidates (FIX-001..003), all with action `retest` and result passed via the same parser-all run. None are pending. Review digest `96e50ed2…2a86`.
- **Impact:** base `69a66ba`. Allowed and inspected paths are `upper.py`, `lower.py` and `tests/test_contract.py`. Entry points, callers, shared state, navigation (not applicable) and lifecycle were all reviewed.
- **Waivers:** none.

## Read-only checks performed while writing this report (2026-09-29)

- `feature-status.py`: confirmed 1 requirement, 2/2 tasks done, 0/3 fixes unresolved, 0 pending historical regression candidates, task semantics current, 6 verification rows passed.
- `validate-feature.py --stage check`: `FEATURE_VALID`. This is a structural check only.
- `audit-delivery.py`: `DELIVERY_EVIDENCE_CURRENT`. Its scope is manifests, tracked content and registered evidence. It does not cover task meaning, test assertions or uncommitted code, which is why the file hashes above were checked separately.
- `git rev-parse HEAD`, `git diff --cached`, `git status`, and sha256 of the three changed files: all matched the recorded identity.
- No tests, builds or verification recording were run for this report.

## Known limits and residual risk

- Tests and repros ran on a single interpreter and host (CommandLineTools Python 3.9.6), using representative inputs only. There was no fuzzing and no extreme input sizes.
- These cases were not probed, and the source contract does not decide them:
  - CSV fields larger than `csv.field_size_limit()`.
  - JSON numbers that overflow float (for example, `1e400` decodes to `inf`).
  - ISO 8601 variants beyond the source examples. The basic `+HHMM` offset and fractional seconds are accepted, and fractions are truncated.
- The delivered code exists only as uncommitted working-tree changes. It is not protected until someone commits it, and any edit to those files makes this acceptance stale.
- `.agent-workflow/` is git-ignored, so this report and the feature records are local only.
- Module label: unclassified.
- No archive, commit, push or cleanup was performed.

## Conclusion

The recorded evidence supports delivery of R-1 for HEAD `69a66ba` plus the uncommitted working tree with the hashes above. That evidence consists of automated tests plus Agent technical inspection; it does not include user or device acceptance. The earlier failed verification for FIX-001, FIX-002 and FIX-003 is preserved above and was resolved by re-verification at digest `d1de4584…`.

Maintainer review note: clarified the distinction between preserved adoption evidence and appended Repair evidence, and between test execution and read-only currency checks. No outcome, code identity or recorded result changed.
