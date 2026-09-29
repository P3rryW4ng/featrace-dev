# FEAT-001 candidate adoption assessment

- Skill: featrace-adoption:dev 0.5.30 (`<RUN>/plugin/skills/dev`), invoked as `next --feature FEAT-001`
- Project: `<RUN>/project` (HEAD `c6de3ba`, main, clean)
- Attempt: `<RUN>/attempt` (run digest `8d1117d9…`)
- Route: Build → primary adoption of the existing integration candidate (`parallel-build.md` § "Integrate and hand back")

## Decision: NOT ADOPTED. Stopped at the adoption preflight guard.

## Guard results (from actual commands run in this session)

| Guard | Command / evidence | Result |
|---|---|---|
| Return gate (both returns `ready`) | `attempt/returns/T-UP/result.json`, `T-LOW/result.json` | Pass: both `ready`, run_digest matches, changed paths are `upper.py` / `lower.py`, each inside its allowed_paths |
| Patch/log integrity | `shasum -a 256` of both patch.diff files and check-0.log | Pass: they match `patch_sha256` / `log_sha256` in the returns and integration-report |
| Candidate tree (step 1) | Private-index `write-tree` in `attempt/integration` | Pass: `d528278c…`, which matches `candidate_tree`. The diff vs base is only `lower.py` and `upper.py`. The candidate was not staged, reset or edited |
| **Adoption preflight (step 2, blocking)** | `python3 core/scripts/parallel-build.py preflight <attempt>` | **FAIL: exit 1. `PARALLEL_BUILD_ERROR: review inputs stale; preserve result and redispatch with current inputs`** |
| Develop validator (current Scope) | `python3 core/scripts/validate-feature.py --stage develop project FEAT-001` | **FAIL: exit 1. `ERROR: PRD review missing or stale: reread sources and reconcile before recording review`** |

### Cause of the staleness (read-only diagnosis)

I recomputed the input collection with `verify-handoff.collect` and compared it with `run.json` → `snapshot.inputs`. HEAD, the tracked/changed paths, the index/worktree hashes and `skill_sha256` all match. The only difference is in `files`:

- `.agent-workflow/features/FEAT-001/sources/prd-original.txt` has a new sha256 compared with the snapshot's `2d00bc96…` (mtime 15:25:09, after run.json at 15:25:07).
- The current file has this appended line: **"New isolation requirement added after candidate checks."**

The original source evidence changed after prepare and after the candidate checks. The approved PRD review, the requirements, the task review and the candidate were all based on the earlier source. Under the Skill this needs a renewed PRD review and reconciliation of requirement meaning (Requirement stage) before any Build. The new line has not been reviewed, so it is unknown whether the candidate satisfies it.

Also observed: `attempt/inputs/` is empty. There is no frozen copy of the canonical inputs, only hashes, so the previous source text cannot be recovered from the attempt. Both returns' `summary` field says they "reuse previously validated synthetic patches". That is recorded here as is; I have not independently confirmed that the workers ran the tasks.

## Actions taken

- Read-only only: read the Skill references, ran `feature-status.py`, `validate-feature.py --stage develop` and `parallel-build.py preflight`, computed hashes, and inspected the candidate tree using a temporary private index that I then deleted.
- **No** primary code applied, **no** record updates (tasks.json/traceability unchanged; both tasks still `planned`), **no** prepare/finish/integrate, dispatch, retry, snapshot refresh, source edit, test run, commit or installation write.
- The primary `upper.py` / `lower.py` are still the `NotImplementedError` stubs. Existing tests and the source are preserved. `git status` is clean.
- The attempt was preserved in full: run.json, snapshot.json, returns/, integration-report.json, check-0.log, and the worktrees `attempt/integration`, `attempt/workers/T-UP` and `attempt/workers/T-LOW`, which are still registered.

## Blockers and next eligible step

1. **Requirement:** the source changed after review. Someone with product authority needs to reread the updated `prd-original.txt`, decide what the "isolation requirement" means, and renew the PRD review (revise/clarify flow). Then reconcile requirements, the task semantic review and impact.
2. **Build:** this attempt cannot become current. The Skill forbids refreshing the snapshot or repairing records to make it green. After step 1, a **new** attempt (new prepare → dispatch → finish → integrate) or serial Build must be based on the current inputs. The existing candidate can serve only as reference material to be re-checked against the renewed requirement, not as adoptable code.
3. Cleanup of this attempt's worktrees is a separate, explicit decision. Keep them until the evidence is no longer needed.
