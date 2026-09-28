# FEAT-001 `develop --parallel` — attempt assessment

**Outcome: `candidate_checks_passed`, for the external integration candidate only.** This is not a final Verify, it is not feature completion, and it does not mean anything was applied to the primary project.

## Route and Skill
- `/dev` could not be called through the host Skill tool: it returned "Unknown skill: dev". Instead, the installed Skill at `/Users/mac/.claude/skills/dev` was loaded by reading its files directly: `SKILL.md`, then `core/references/parallel-build.md` (the Develop route with explicit `--parallel`), then `specialists/featrace-build/SKILL.md`.
- Version in `.feature-delivery-install.json`: **featrace-dev 0.5.25**. After the run, all files listed in the manifest were rehashed and still match (`SKILL_MATCHES_MANIFEST`).
- All helper calls used the installed `core/scripts/parallel-build.py`. The source-repo helper was not used.
- Plan: `/private/tmp/featrace-claude-0525-s4owgoyc/A/plan.json`, used exactly as supplied and not modified.

## Independence review (router)
- `upper.py:1-2` and `lower.py:1-2` each define a separate pure `convert(value)`. Neither imports the other, and there is no shared state.
- Only `tests/test_composition.py:1-10` uses both functions, and it runs as part of the integration command.
- The plan's allowed paths (`upper.py` for T-UP, `lower.py` for T-LOW) match `impact.json` `allowed_paths`. Both tasks are `planned`, and neither depends on the other.

## Helper statuses
| Step | Status |
|---|---|
| `prepare` | `PARALLEL_BUILD_PREPARED`, run_digest `9679016e…a7deef` |
| `preflight` (router) | `PARALLEL_BUILD_INPUTS_CURRENT` |
| `finish` T-UP | `ready`; its check `test_upper.py` passed (rc 0) |
| `finish` T-LOW | `ready`; its check `test_lower.py` passed (rc 0) |
| `integrate` | `candidate_checks_passed`; integration check `unittest discover -s tests` passed (rc 0, 4 tests) |

## Native Agent calls
- There were 2 background calls to the host Agent tool, both sent in one message using the built-in `general-purpose` type. No custom agents, settings or plugins were used.
- Each worker was given only:
  - its task ID
  - its worktree
  - the RUN directory
  - the frozen inputs path
  - the Skill root and the path to the Build specialist
  - the side-effect restrictions
- Neither worker was told how to implement its task.
- Permissions did **not** enforce the split between workers. It relied on the instructions plus the helper's ownership and hash checks after the run.
- Each worker ran its own preflight, then called `finish` once.

## Changed paths and patches
- T-UP: `returns/T-UP/patch.diff` (sha256 `20cc9013…af7fd8`, matches result.json). The only change is in `upper.py`: `return value` became `return value.upper()`.
- T-LOW: `returns/T-LOW/patch.diff` (sha256 `5d29991a…3d7708`, matches result.json). The only change is in `lower.py`: `return value` became `return value.lower()`.
- The router read both patches and both check logs before integrating. The changes don't overlap, and neither changes the other function. No semantic conflict was visible.

## Integration evidence
- Candidate worktree: `attempt/integration`, detached at base `8017a0c0ab5cd6d3096e21ff7ce1d64f9d357cdf`, candidate tree `f3f707297ce94aa31f44cd6733f213699c596421`.
- In the candidate, `git status` shows `M lower.py` and `M upper.py` staged, and nothing else.
- `attempt/check-0.log` (sha256 `e6ec1827…94c57c1`) reads: "Ran 4 tests … OK". The four tests are upper, lower, composition and empty-string.
- The brief said a controlled failure might be injected into the approved integration command. No failure appeared in this run: the command actually passed.

## Primary unchanged check
- Before the attempt and again after integration, the router recorded: HEAD, `git write-tree`, `git status --porcelain --ignored`, sha256 of every non-`.git` file (including `.agent-workflow` records), and the sha256 of `.git/index`.
- The two snapshots are identical (`PRIMARY_UNCHANGED`). HEAD is still `8017a0c` on `main`, with no new branches or stashes.
- The only Git metadata added is three worktree registrations (`workers/T-UP`, `workers/T-LOW`, `integration`). They were kept; no cleanup was done.

## Gaps and limits
- `prepare`'s develop validation reported `FEATURE_VALID` with two warnings: **historical regression review missing** and **task semantic review missing**. Both warnings say these should be synced before business-code edits. The helper still accepted the attempt, and I did not sync or disposition either review, because the instructions ruled out any record or status changes. The T-LOW worker also saw these warnings and correctly left them to the router. They remain open. They have to be dealt with before any ordinary Build applies code to the primary project, and before Verify.
- The requirements record's feature status is still `provisional`.
- Not done, as instructed:
  - applying the code to the primary project
  - updating tasks, traceability or verification records
  - ordinary or independent Verify, `check`, or audit
  - cleanup
- The worktrees are not security sandboxes. Hash checks detect differences in the final state; they don't catch temporary or external side effects.

## Timings and tokens (as reported by the host)
- `prepare` + `preflight`: about 0 s by wall clock (whole-second resolution). `integrate`: about 0 s.
- T-UP worker: 36.5 s, 20,868 subagent tokens, 5 tool uses.
- T-LOW worker: 38.8 s, 20,783 subagent tokens, 5 tool uses.
- The router's own token use is not visible per step. The session cost reported was about $0.78 at the time of writing.
- This does not show that running in parallel made anything faster; no serial run was measured for comparison.
