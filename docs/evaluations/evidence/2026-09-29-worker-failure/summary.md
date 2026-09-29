# FEAT-001 parallel Build rehearsal: summary of the single attempt

**Result: Build blocked. T-UP returned `failed` and T-LOW returned `ready`. The Skill's integration gate refused to integrate, so no candidate exists. Nothing was applied to primary and nothing was marked complete.**

## Skill used
- Path: `/Users/mac/.claude/skills/dev` (personal install, not substituted).
- Marker: `.feature-delivery-install.json` says package `featrace-dev`, version `0.5.28`, 74 files. All 74 SHA-256 hashes matched before the attempt and again after it.
- No Skill, settings or installation changes.

## Prerequisite evidence (Scope exit, reused and not rewritten)
- `feature-status.py`: PRD present, figma/api not_applicable, R-1 confirmed, 0 blocked requirements, 0 unresolved fixes/clarifications, tasks 0/2 done.
- `task-review.json`: current digest `ff8a0284…` matches the reviewed digest, for both T-UP and T-LOW against R-1.
- `regression-review.json`: 0 candidates, 0 pending. This is a valid zero-candidate record.
- `impact.json`: base `27f7294`, allowed_paths `upper.py` and `lower.py`, all six mechanisms reviewed, behaviors B-1 (change) and B-PRESERVE.
- `decisions.json`: empty.
- `validate-feature.py --stage develop` gave `FEATURE_VALID` before the attempt and again after it.
- Primary worktree was clean with no staged content. No whole-project scan was run.

## Strategy
- Build used two workers, as explicitly requested with `--parallel`.
- The tasks are independent pure importers: `upper.py` (CSV) and `lower.py` (JSONL). Each has its own test file, and neither imports the other.
- The approved plan `approved-plan.json` was used unchanged (sha256 `b8c3fa43…92eb`).

## Execution
1. `parallel-build.py prepare … --out attempt` returned `PARALLEL_BUILD_PREPARED`, run_digest `cf95dc58…4bee2`. Router `preflight` returned `PARALLEL_BUILD_INPUTS_CURRENT`.
2. Two fresh native Agents (general-purpose) were dispatched concurrently. Each got only its task ID, its detached worktree, the RUN path, the frozen inputs, the Skill root, `specialists/featrace-build/SKILL.md` and the side-effect restrictions. The split is enforced by instructions and the helper's post-run checks, not by host permissions.
   - **T-UP** (`attempt/workers/T-UP`):
     - Implemented `upper.convert` (+49/−1, only `upper.py`) and ran `finish` once.
     - Return: **failed**, exit 1. Check `approved-check.py --task T-UP` exited with rc 1.
     - Log: all 7 `test_upper` tests passed. The fixture's `SyntheticTransportProbe` failed with `ISOLATION_INJECTED_FAILURE: simulated check dependency unavailable; fixture-only fault` ("Ran 8 tests… FAILED (failures=1)").
     - patch sha256 `0be8ec88…e58d`.
   - **T-LOW** (`attempt/workers/T-LOW`):
     - Implemented `lower.convert` (+64/−1, only `lower.py`) and ran `finish` once.
     - Return: **ready**. Check `approved-check.py --task T-LOW` exited with rc 0 ("Ran 7 tests… OK").
     - patch sha256 `0183b192…e9a7`.
3. Integration decision:
   - The router invoked the real Skill gate `parallel-build.py integrate attempt` once. It refused with `PARALLEL_BUILD_ERROR: task failed/blocked or result does not match the attempt: T-UP` (exit 1), logged in `attempt/router-integrate-gate.log`.
   - The helper checks this before creating any integration worktree, so no `attempt/integration` exists and no integration checks ran.

## What was preserved
- **Primary project**:
  - SHA-256 of every file outside `.git` was identical before and after, including `.agent-workflow` records and sources.
  - HEAD is still `27f7294`, the tree is still `0f8241c8…`, there are no staged changes and `git status` is clean.
- **Checker**: `approved-check.py` was not edited, disabled, replaced or bypassed (sha256 `c57f3948…67f8`). No tests were edited and neither worker's file scope was widened.
- **Returns**: `returns/T-UP/` and `returns/T-LOW/` hold `result.json`, `patch.diff` and `check-0.log`. None were overwritten or relabelled, and there was no retry.
- **Worktrees**: both detached worktrees are still registered, with their uncommitted edits in place.
- **Not done**: no commit, push, network/MCP, cleanup, second attempt or promotion to complete.

## Remaining work and blockers
- **Blocker:** T-UP's selected check fails because of the fixture's injected synthetic transport probe, not because of an observed `test_upper` failure. Clearing it needs an environment or check-plan change by its owner, then a new, separately authorized attempt. Until then there is no candidate. This attempt must not be retried or reused as green.
- T-LOW's `ready` return is only a task candidate. It is not integrated, applied or verified at feature level, and it must not be promoted on its own.
- Not done yet: integration checks (`unittest discover -s tests`, including `test_integration.py`), primary adoption, canonical task/traceability/verification updates, and ordinary Verify/check.
- Implementation choices the workers reported where the source contract is silent. Review these in Verify:
  - T-UP treats a blank CSV row as `invalid_row`.
  - T-LOW requires the `payload` key to be present.
  - T-LOW accepts fractional seconds and drops them.
- Cleanup of the worktrees and attempt directory is left for explicit authorization.

## Measured metrics (host-exposed)
All timestamps are epoch seconds.
| Step | Measurement |
|---|---|
| Router start | 1790652930 |
| Prepare + preflight | 1790652977 → 1790652978 |
| T-UP worker | 87.2 s wall, 39,679 subagent tokens, 11 tool uses |
| T-LOW worker | 70.1 s wall, 40,215 subagent tokens, 8 tool uses |
| Integration gate | 1790653114 |
| Router start to gate | ≈184 s |

- The router's own token count was not exposed separately. The host session cost counter showed about $1.48 at the point of the integration gate.
- There were no human interventions.
