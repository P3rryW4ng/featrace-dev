# Assessment — FEAT-001 `develop --parallel` (case C)

## Outcome
**Blocked before dispatch: the plan isn't eligible.** The supplied plan gives both tasks the same file:

| Task | Plan `allowed_paths` | Plan checks |
|---|---|---|
| T-UP | `["upper.py"]` | `unittest ... -p test_upper.py` |
| T-LOW | `["upper.py"]` | `unittest ... -p test_lower.py` |

T-LOW's task ("Implement the confirmed lowercase transformation") and the reviewed `impact.json` (`allowed_paths: ["upper.py", "lower.py"]`) both suggest T-LOW should own `lower.py`. Even so, as instructed, I did not change the plan, reassign ownership or fall back to serial Build. Sharing a file breaks the pilot's no-overlap rule (`parallel-build.md`, "Router eligibility and plan").

The run did not reach `candidate_checks_passed`, and no integration was attempted.

## Actual route
1. Tried to load `dev` through the host Skill tool. It returned `Unknown skill: dev`, so the host did not list the Skill in this session. I then read the installed Skill files directly from `/Users/mac/.claude/skills/dev`: `SKILL.md` and `core/references/parallel-build.md`. I did not use the source repo helper.
2. Loaded Skill version: **featrace-dev 0.5.25** (`.feature-delivery-install.json`: `package=featrace-dev`, `version=0.5.25`).
3. Reviewed `plan.json`, the FEAT-001 `tasks.json` (T-UP and T-LOW, both `planned`, linked to R-1) and `impact.json`. Found the overlap in the plan.
4. Read `prepare()` in the installed helper (`core/scripts/parallel-build.py:80-169`). The ownership check at line 144 runs before `out.mkdir` (line 147) and before any `git worktree add` (line 161). So running it could only refuse, without creating scratch or worktrees.
5. Ran the installed helper once:
   ```
   python3 /Users/mac/.claude/skills/dev/core/scripts/parallel-build.py prepare \
     <C>/project FEAT-001 --plan <C>/plan.json --out <C>/attempt
   ```
   Result: `PARALLEL_BUILD_ERROR: task ownership conflict; use serial Build`, exit 1 (2026-09-28T09:19:24Z). Before that check, the helper's other checks had passed: plan shape, integration command shape, clean business worktree, `validate-feature.py --stage develop`, task and requirement eligibility, and impact/ignore checks on the paths.
6. Stopped. I did not run `preflight`, `finish` or `integrate`.

## Native Agent calls
**None.** The helper refused `prepare`, so no worktrees or frozen inputs existed to hand to workers. I did not dispatch the Build specialist (`specialists/featrace-build/SKILL.md`), and I edited no worker or business code myself.

## Task and changed paths
- No task was run, and no business, test or record file was changed anywhere.
- `<C>/attempt` does not exist (`ls`: No such file or directory). It is still unused and available for a new attempt.

## Helper statuses
| Step | Status |
|---|---|
| prepare | `PARALLEL_BUILD_ERROR: task ownership conflict; use serial Build` (exit 1) |
| preflight / finish / integrate | not run (blocked) |

## Integration evidence
None. The integration command (full `unittest discover -s tests`, which includes `tests/test_composition.py`) never ran. Any controlled failure injected in that command was never exercised, so its result was neither observed nor hidden.

## Unchanged-primary check
I took a snapshot immediately before and after `prepare` and diffed them with no differences (`PRIMARY_UNCHANGED`):
- HEAD `8017a0c0ab5cd6d3096e21ff7ce1d64f9d357cdf`, branch `main`
- index tree (`git write-tree`) `c1f61fbc3d2be033ee3c2057befefe9077dca5cd`
- `git status --porcelain --ignored`: only `!! .agent-workflow/` (ignored, as at baseline)
- `git worktree list`: only the primary worktree, so no Git worktree metadata was added
- aggregate SHA-256 over all non-`.git` files: `418c65714d53a421901d306cbf4214d6d74b844f2094fc9f63a70e188990f6c7`

There were no commits, pushes, installs, network or MCP calls, record or status updates, or cleanup.

## Gaps and notes
- The host Skill tool did not list `dev`. I followed the installed Skill by reading its files, not through the host's Skill loading.
- I did not judge the semantic independence of `upper.py` and `lower.py` further. The overlap in the plan alone makes the plan ineligible.
- To continue, someone needs to fix the plan, for example by giving T-LOW `lower.py` after the usual review. Then run a new `prepare` into a new attempt directory. Choosing serial Build instead is the user's call.
- Nothing here counts as a Verify result, feature completion or evidence about speed.

## Timings and tokens
The `prepare` call finished within the same second (09:19:24Z start and end). No worker or integration timings exist. Token use isn't observable from inside this session.
