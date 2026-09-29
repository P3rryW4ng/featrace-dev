# FEAT-001 candidate adoption assessment

Skill: native `featrace-adoption:dev` (plugin.json version 0.5.30, root `<RUN>/plugin/skills/dev`), invoked with `next --feature FEAT-001`.
Route: Build (adopt the validated parallel candidate) → Verify → Deliver (report only).

## Delivery status: NOT COMPLETE (blocked on 3 manual verification rows)

Code is adopted and every automated gate passes on the actual primary worktree. However, `validate-feature.py --stage check` and `audit-delivery.py` both exit 1 because three verification rows have no evidence. I did not invent a pass or a waiver for them.

## Worktree identity

- Primary: `<RUN>/project`, branch `main`, HEAD `69a66badf72164c34bf2a9e49e5cf050cb11d288` (unchanged).
- Adopted changes are **uncommitted and unstaged**: ` M upper.py`, ` M lower.py`. Full worktree diff sha256 `e7fd580a5ed7f58052a379e65b2190d5a52a43a10758aad6f90d9d87c6e85330`.
- Per-file primary diffs are byte-identical to the approved return patches: upper.py `0be8ec88…ae58d` (T-UP), lower.py `0183b192…e9a7` (T-LOW). File contents equal the candidate.
- Index: `.git/index` sha256 `263bc7d5…79b1`, the same before and after. Nothing is staged.
- Tests (`tests/test_{contract,integration,lower,upper}.py`) and `sources/prd-original.txt` are byte-identical to the frozen hashes.
- `.agent-workflow/` is git-ignored, so record updates appear only on disk.

## Candidate eligibility (inspected read-only before adoption)

- Attempt `<RUN>/attempt`, run digest `521b9cf4…3ca56`, base `69a66ba`.
- Both returns have `status: ready`. Each changed only its assigned path (T-UP→upper.py, T-LOW→lower.py). The patch and check-log sha256 values match `result.json` (task logs: 7 tests OK each).
- Integration report: `candidate_checks_passed`, candidate tree `d528278c…a0226d405db0da74`. I recomputed this with a private index and it matches. The candidate diff vs HEAD is exactly the two return patches. The integration log sha matches `eea909e8…`: 25 tests OK.
- Semantics: the two pure functions have no cross imports and no shared/global mutable state, which is consistent with impact.json B-1/B-PRESERVE and the plan's independence rationale.
- Blocking guard: `parallel-build.py preflight <RUN>` was run as a separate call. It exited 0 with `PARALLEL_BUILD_INPUTS_CURRENT`, and adoption went ahead only after that.

## Actions taken

1. Ran `git apply --check` and then `git apply` (no `--index`) for both return patches into the primary worktree.
2. Ran the actual primary suite: `python3 -m unittest discover -s tests -v` gave **25 tests OK, exit 0**.
3. Serial record updates:
   - `tasks.json`: T-UP and T-LOW set to `done`, with `test_evidence` giving patch hashes, HEAD plus uncommitted-diff identity and the actual primary run result.
   - `traceability.json`: unchanged. It already links R-1 → T-UP/T-LOW → upper.py/lower.py → TEST-UP/TEST-LOW.
   - Ran `render-workspace.py`, which regenerated the views.
4. Verify:
   - `verify-inputs.py`: the only changed paths are the adopted ones.
   - `validate-feature.py --stage develop`: `FEATURE_VALID`.
   - `verification.py sync`, then row mapping (see below), then `verification.py run`: gate `parser-all` **passed** on revision 69a66ba plus the uncommitted diff. Checklist digest `7cd1cc4e…a6a0`. Exit 2 because rows remain unfinished.
   - `validate-feature.py --stage check`: exit 1.
   - `audit-delivery.py`: exit 1.
   - `feature-status`: tasks 2/2 done, verification passed=3, not_run=3.
5. Reused the existing reviews without changing them: task-review (current digest `ff8a0284…`), regression-review (0 candidates) and impact.json. Task progress does not change the task-review digest.

## Assertion coverage mapping (verification.json)

| Row | Mode | Result | Basis |
|---|---|---|---|
| requirement:R-1:1 CSV rules | automatic → parser-all | passed | Each listed CSV rule has an exact-equality assertion. |
| requirement:R-1:2 JSONL rules | automatic → parser-all | passed | Each listed JSONL rule has an exact-equality assertion. |
| gate:parser-all | automatic | passed | Actual run on the primary worktree. |
| requirement:R-1:3 order / no external effects / no shared mutable state | manual | not_run | Order and state are asserted. "No external effects" is only asserted on representative paths, by patching open/io.open/socket/Popen. The gate's known_gap says so. Partial, so left manual. |
| impact:B-1 full source contract | manual | not_run | Includes the source's "without external effects / no global state / no CSV dependency" clauses, which have the same partial assertion coverage. |
| impact:B-PRESERVE pure interfaces, no external effects | manual | not_run | Same external-effects gap. |

My source inspection found that upper.py imports only csv, io and decimal, and lower.py imports only json, re and datetime. Neither has global mutable state or I/O calls. This is Agent inspection, not an assertion or a user observation, so I did not record it as a manual pass. The CSV row also has an untested interpretation: scientific-notation prices (for example `1e2`) are accepted as a finite Decimal. The source does not forbid them, so this is not recorded as a gap in the row.

## Remaining gaps and blockers

- Three manual rows (R-1:3, B-1, B-PRESERVE) need either an actual reviewer observation recorded through `verification.py record` for this uncommitted build, or an authorized waiver with reason, risk and follow-up. Another option is an authorized refinement of the acceptance criteria and impact behaviors into independently assertable parts, which needs its own review. None of these was authorized here, so none was done.
- The `check` validator additionally reports that B-1 and B-PRESERVE "need actual regression evidence or explicit waiver". The same rows resolve this.
- There is no UI or manual-device evidence, and none applies to this headless fixture.
- The adopted code is uncommitted, so the tested revision is HEAD plus the working diff. A future commit would need the checks to be re-established for that commit.

## Not done (by instruction)

No new tests or implementation. No additional prepare/finish/integrate, Agents, retries or scan. No settings or installation writes. No commit, push, archive or cleanup. The attempt, candidate, returns and frozen inputs are unchanged (hashes and candidate tree re-verified), and all four worktrees are still registered. I did not read `before.json` or the preparation transcripts.

Recommended next action: a human reviewer confirms or rejects the external-effects/pure-interface rows (R-1:3, B-1, B-PRESERVE) and records the result with `verification.py record` against digest `7cd1cc4e…` and HEAD `69a66ba` plus the uncommitted diff. Then rerun check and audit.
