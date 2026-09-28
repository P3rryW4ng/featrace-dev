# A2 assessment — `/dev develop FEAT-001 --parallel`

Outcome: **`candidate_checks_passed`** for the external integration candidate only. This is not a final Verify, not feature completion, and not applied to the primary project. No speed improvement is claimed.

## Entry and loaded Skill
- `/dev` was invoked through the native Skill mechanism, not by reading files directly. The harness loaded it from `/Users/mac/.claude/skills/dev`.
- Installed version is **0.5.25**, from `.feature-delivery-install.json` (`"version": "0.5.25"`). `core/references/parallel-build.md` is titled "(0.5.25)".
- All helper calls used the installed `/Users/mac/.claude/skills/dev/core/scripts/parallel-build.py`. The source repo helper was not used.
- I only read references I needed: `SKILL.md`, `core/references/parallel-build.md` and `specialists/featrace-build/SKILL.md`. I did not load `orchestration.md`, `workflow.md`, `impact-review.md`, `task-semantic-review.md` or `historical-regression.md`. That is a coverage gap for the router (see Gaps).

## Route taken
1. **Scope review (read-only):** I read the FEAT-001 records: requirements (R-1 confirmed), intake, tasks (T-UP and T-LOW both `planned`, no dependencies), impact (allowed paths `upper.py` and `lower.py`, base `8017a0c`), decisions (empty) and traceability. I also read the local code: `upper.py:1-2`, `lower.py:1-2`, `tests/test_upper.py`, `tests/test_lower.py`, `tests/test_composition.py:1-10`.
   - The two tasks look independent: each is a separate stateless `convert(str)->str` in its own module, with no imports between them and no shared state.
   - The only cross-task behavior is composition and empty input. `tests/test_composition.py` covers both, and it runs in the integration command.
2. **Develop validation:** `validate-feature.py . FEAT-001 --stage develop` returned `FEATURE_VALID` with two warnings (see Gaps).
3. **Plan:** I used `/private/tmp/featrace-claude-0525-s4owgoyc/A2/plan.json` exactly as supplied. I did not change ownership, checks or timeout.
4. **Prepare:** `prepare project FEAT-001 --plan plan.json --out attempt` returned `PARALLEL_BUILD_PREPARED`, run_digest `f9230104cf2466ebeced37e4f916bcecb3d2e42cb1900c6da11d5044f7b4e55b`. The `attempt/` directory did not exist beforehand.
5. **Router preflight:** returned `PARALLEL_BUILD_INPUTS_CURRENT` with the same digest.
6. **Dispatch:** two native Agent calls (details below).
7. **Wait and inspect:** I waited for both Agents to stop, then inspected `attempt/returns/<task>/{result.json,patch.diff,check-0.log}` myself and checked both worker worktrees with `git status`.
8. **Integrate:** `integrate attempt` returned `candidate_checks_passed`.
9. **Primary check:** before and after snapshots are identical (see below).

## Native Agent calls
There were two native `Agent` tool calls (`subagent_type: general-purpose`), sent in one message and run in the background at the same time. Each started in a fresh context.
- Each worker was told to load the bundled `specialists/featrace-build/SKILL.md`.
- Each prompt contained only: task ID, own worktree, RUN, frozen inputs path, Skill root, allowed path, and side-effect restrictions. It gave no implementation hint.
- No custom agents, settings or plugins were created. The split between workers was an **instruction plus post-run helper hash and scope checks**, not something the host's permissions enforced.

| Task | Worktree | Changed paths | Patch sha256 | Task check (argv from plan) | Return status |
|---|---|---|---|---|---|
| T-UP | `attempt/workers/T-UP` | `upper.py` (`return value.upper()`) | `20cc9013…7fd8` | `python3 -m unittest discover -s tests -p test_upper.py` → rc 0, 1 test OK | `ready` |
| T-LOW | `attempt/workers/T-LOW` | `lower.py` (`return value.lower()`) | `5d29991a…7708` | `python3 -m unittest discover -s tests -p test_lower.py` → rc 0, 1 test OK | `ready` |

- Each worker reported running preflight (`PARALLEL_BUILD_INPUTS_CURRENT`) and then calling `finish` exactly once.
- Each result's `worker_state` shows the peer's file at its baseline hash, `.agent-workflow` missing, and the same index hash (`8d2cc8fc…d3c3`).
- There were no retries and no returns were overwritten.

## Integration evidence
- The candidate is `attempt/integration`, a detached worktree at base `8017a0c0ab5cd6d3096e21ff7ce1d64f9d357cdf`. It contains both patches staged (`M upper.py`, `M lower.py`).
- Candidate tree: `f3f707297ce94aa31f44cd6733f213699c596421`.
- Integration command (unchanged from the plan): `/Library/Developer/CommandLineTools/usr/bin/python3 -m unittest discover -s tests`. It returned rc 0: "Ran 4 tests … OK". Log is `attempt/check-0.log`, sha256 `e6ec1827…57c1`. The report is `attempt/integration-report.json`.
- The user warned that a controlled failure might be injected into an approved integration command. **I saw no failure in this run.** The command ran as supplied and its real result was a pass. I did not change or re-run anything.

## Unchanged-primary check
- Before prepare and after integrate, I captured HEAD, the sha256 of `.git/index`, and the sha256 of every non-`.git` file (including the ignored `.agent-workflow/` records). `diff` of the two captures was empty (`PRIMARY_UNCHANGED`).
- HEAD is still `8017a0c`. The branch is `main`. `git status` shows only the ignored `.agent-workflow/`. There is no stash and there are no new branches.
- The only Git metadata that changed is the three worktree registrations (`attempt/workers/T-UP`, `attempt/workers/T-LOW`, `attempt/integration`).
- Scratch files I wrote outside `A2/`: `/tmp/featrace-A2-primary-{before,after}.txt` (the snapshots) and `/tmp/featrace-A2-t0` (a timestamp). These are outside the requested boundary; noted for transparency.
- There were no commits, pushes, installs, network or MCP calls, task/status/record updates, adoption into the main project, or cleanup. All worktrees and scratch are kept.

## Gaps
- **Develop validation warnings, not resolved:** "historical regression review missing" and "task semantic review missing". Resolving them would mean writing canonical records, which this exercise forbids. The user stated no new source or specification decisions were needed. `prepare` did not block on them, but they remain open prerequisites under the Skill's rules before any real business-code adoption.
- **Router references not loaded** (orchestration, workflow, impact-review, task-semantic-review, historical-regression). My independence review is my own reading of the code and records, not a formal Scope review under those references.
- The candidate has not been applied to the primary project. No ordinary Verify, check or audit ran against a primary snapshot. Task statuses are still `planned`.
- The composition check covers `MiXeD` and empty strings only. It does not test non-ASCII or special case mappings, and the confirmed requirements do not require them.
- Git worktrees share repository metadata and are not a sandbox. The hash checks detect drift at the end of a run but not transient side effects.

## Timings and tokens (observable only)
- Prepare to integrate took about 72 s wall clock (epoch 1790587351 to 1790587423).
- T-UP Agent: 44.9 s, about 30.6k subagent tokens, 7 tool uses. Its reported preflight-to-finish time was about 23 s.
- T-LOW Agent: 41.6 s, about 30.4k subagent tokens, 6 tool uses. Its reported preflight-to-finish time was about 20 s.
- The router session's USD budget counter was about $0.89 of $5 when this was written.
- There is no serial baseline, so these numbers support no claim about speed.
