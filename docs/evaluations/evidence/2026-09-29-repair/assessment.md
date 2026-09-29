# FEAT-001 Repair → Retest → Deliver assessment (2026-09-29)

## Skill identity
- Invoked via native Skill tool: `featrace-repair:dev`, args `next --feature FEAT-001 …`.
- Loaded base directory: `<ISOLATION>/repair-continuation/plugin/skills/dev`; plugin manifest `{"name": "featrace-repair", "version": "0.5.30"}`; verification-workflow.md header `0.5.30`. Not the personal 0.5.29 install.
- Project: `<ISOLATION>/project`, feature FEAT-001 "Independent catalog and event importers".

## Actual route
`next` → **Repair** (`fix-workflow.md`) → **Verify** (`verification-workflow.md`, impact/historical-regression gates) → **Deliver** judgment. Existing single-Agent route; no coordinator, independent reviewer, workers, Agents, MCP, network or builds. One repair-and-check round was enough (limit was two).

Steps actually executed:
1. Starting identity captured: HEAD `69a66ba…d288`, nothing staged, uncommitted adopted `upper.py` sha256 `7a1cea57…a6e7`, `lower.py` `e4e9aa7f…120f` (the same identity as the failed rows in verification.json).
2. Re-ran the recorded counterexamples on that code. All reproduced: JSONL payload `NaN`/`Infinity`/`-Infinity` accepted; Arabic-Indic-digit timestamp accepted and normalized; malformed CSV price set `InvalidOperation` in the caller's decimal context.
3. `record-fix.py` → FIX-001, FIX-002, FIX-003 (feature was already `provisional`).
4. Investigated (original PRD, requirements/AC, tasks, impact, code, tests), classified, repaired, added regression tests.
5. Updated impact.json (scope + stale mechanism evidence), fixes.json, tasks.json (progress/evidence only), rendered views, ran `validate-feature --stage develop` and `regression_review.py sync`.
6. `verify-inputs.py`, `verification.py sync`, `verification.py run` (parser-all), bounded Agent technical re-inspection, `verification.py record` for the 4 manual rows.
7. Fixes marked verified. Regression review re-synced, and the 3 surfaced candidates were given a `retest` disposition with results. Then `validate-feature --stage check`, `audit-delivery.py`, `feature-status.py`, and feature status set to `complete`.

## Classifications
All three are **implementation_defect** (code differed from already-confirmed source rules). No requirement, AC, PRD or product decision changed, and no clarify/revise was needed.

| Fix | Rule (original source) | Root cause | Repair |
|---|---|---|---|
| FIX-001 (T-LOW) | "Invalid JSON -> invalid_json" | `json.loads` default accepts non-JSON constants NaN/Infinity/-Infinity | `json.loads(raw, parse_constant=_reject_constant)` → ValueError → existing invalid_json path. The id is not reserved |
| FIX-002 (T-LOW) | "timestamp an ISO8601 aware time" | `_TIMESTAMP` `\d` matched any Unicode digit | compile `_TIMESTAMP` with `re.ASCII` |
| FIX-003 (T-UP) | "without external effects" / AC "no external effects" | `Decimal(value)` signalled into the caller's thread-local decimal context | price parse/validate/format inside `decimal.localcontext(Context())` |

Public interfaces `convert(text)->dict` and every accepted/rejected semantic outside these defects are unchanged.

## Tests and executed coverage
- New regression tests, appended to the existing `tests/test_contract.py`. Diff is 15 insertions, 0 deletions, and no existing assertion changed:
  - `test_json_non_standard_constants_are_invalid_json_and_do_not_reserve`: NaN, Infinity, -Infinity and nested NaN → exact invalid_json errors on lines 1–4. A later valid line with the same id is accepted.
  - `test_json_timestamp_requires_ascii_digits`: Arabic-Indic year, full-width offset digits, Bengali hour digit → exact invalid_timestamp.
  - `test_csv_leaves_caller_decimal_context_untouched`: sets caller traps off and prec=1 → exact output for bad/NaN/sNaN/-1/0.001/12.34. Caller context identity, flags (none set), traps and prec are unchanged.
- The new tests do guard the defects. The same tests run against the pre-repair code, reconstructed in a disposable `/tmp` scratch copy outside the project, gave FAILED (failures=5). On the repaired code they pass.
- Gate `parser-all` (`python3 -m unittest discover -s tests`), run through `verification.py run`: returncode 0, **Ran 28 tests OK** (25 pre-existing + 3 new).
- verification.json digest `d1de4584…108a`: all 6 rows `passed`.
  - Automatic: R-1:1 and gate:parser-all.
  - Manual (Agent technical inspection, recorded with method, identity and limits, not user/device evidence): R-1:2, R-1:3, impact B-1, impact B-PRESERVE.
- Agent inspection on repaired code: the recorded counterexamples no longer reproduce. With caller traps on and prec=1, CSV output is unchanged and caller flags stay empty. Imports are limited to csv/io/decimal and json/re/datetime, with no cross-import and no file/env/network/process calls.
- `validate-feature --stage check`: FEATURE_VALID.
- `audit-delivery.py`: DELIVERY_EVIDENCE_CURRENT.
- `feature-status`: tasks 2/2, fixes unresolved 0/3 (verified 3), historical regression retest=3 pending=0, task semantics current, verification passed=6.

## Record changes, and why
- impact.json: added `tests/test_contract.py` to `allowed_paths`/`inspected_paths`. This is the authorized regression edit; check otherwise reports unreviewed scope expansion. Also refreshed stale mechanism evidence (entry_points/callers/shared_state/lifecycle still described two-line stubs). Behaviors are unchanged, so verification row IDs are unchanged.
- regression-review.json: sync first gave 0 candidates. After FIX-001..003 were verified, it surfaced them as candidates. Each got `retest` with reason "the current change is the repair itself, touching its matched paths", planned check parser-all + the named test, and a passed result bound to the current review digest.
- tasks.json: `test_evidence` appended only. Titles, descriptions, status and requirement links are unchanged, so no task semantic re-review was needed (task semantics reported current).
- traceability.json: content unchanged. It was re-serialized (pretty-printed) by the edit script with identical data; its schema has no fix field and links (R-1 → T-UP/T-LOW, TEST-UP/TEST-LOW, upper.py/lower.py) remain accurate.
- requirements.json: only `feature.status` `provisional` → `complete`. Statement, AC, requirement status and sources are unchanged.

## History preservation
- Original source `sources/prd-original.txt` is unchanged (sha256 `2d00bc96…e2e3`, readable and indexed per verify-inputs).
- verification.json histories are kept. R-1:2 reads passed, passed, **failed**, passed. R-1:3, B-1 and B-PRESERVE each read **failed**, passed. No rows retired, and no digests replaced.
- Fix records keep their original report text, expected/actual/reproduction and `previous_feature_status`. There were no prior fixes to preserve; decisions.json is untouched (empty).
- HEAD `69a66badf72164c34bf2a9e49e5cf050cb11d288` and the index (empty staged diff) are unchanged. All fixes are left unstaged. No commit/push/archive, no config/install writes, no Skill-source edits. The external attempt directory was not read or modified.

## Current code identity (delivered working tree)
HEAD `69a66badf72164c34bf2a9e49e5cf050cb11d288` + uncommitted:
- `upper.py` `04cc7c9bf3aa40b1847f32517eb8fc44f1de28b8cfe9a5479e135c8a1fdde7c2`
- `lower.py` `168cad22cff88e0476cabdce7e99deb809e8338bab1824a9741288d85a2faa26`
- `tests/test_contract.py` `3dbad9b96c0d21fb59396cf06b76686bd6a4fe3ed375e55b9f558cded9c62755`
- Unchanged: `tests/test_upper.py` `768d2442…419e`, `tests/test_lower.py` `5e1123a2…3e64`, `tests/test_integration.py` `a1a02cb7…c9c6`.

## Delivery judgment
**Complete** (feature.status = complete) for the uncommitted working tree above. The confirmed requirement, all tasks, all three fixes (verified with regression tests that fail on the pre-repair code), current historical-regression retests, the approved parser-all gate and every verification row are current and passed. The selected gate and the source not-applicable status (figma/api) are reused as approved. No waiver was used, and no user or device evidence was claimed.

## Limitations
- Manual rows rest on Agent technical inspection plus representative inputs. They cover a single interpreter/host (CommandLineTools Python 3.9.6), not an exhaustive proof, fuzzing or a security sandbox.
- Not probed, deliberately outside the bounded repair scope; no source rule was decided and these are not recorded failures:
  - CSV fields larger than `csv.field_size_limit()` (by stdlib behaviour this likely raises `_csv.Error`).
  - JSON numbers that overflow float (e.g. `1e400` decodes to `inf`).
  - ISO 8601 variants beyond the source examples: basic `+HHMM` offsets and fractional seconds are accepted, and fractions are truncated (source: "fixtures have no fractions").

  If the owner cares about any of these, they belong in a new fix/clarify, not this delivery.
- Delivery identity is an uncommitted working tree. A commit will change the revision string, and the verification rows are bound to HEAD + file hashes.
- The decimal flag interpretation (caller-visible context write = external effect) follows the prior recorded basis. The repair removes the effect without changing any output, so no product choice was needed.
