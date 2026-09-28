# Assessment: `develop FEAT-001 --parallel` (FeatraceDev 0.5.26, project-local Skill)

## Result in one line
Scope prerequisites were current and the plan was eligible. Two isolated workers each returned `ready`. The helper produced an external integration candidate with status `candidate_checks_passed`. This is a **candidate only**: nothing was adopted into the primary project, no task was marked done, and no final Verify was run. Nothing was delivered.

## Loaded Skill and routing
- Loaded `/private/tmp/featrace-claude-0526-w1ged5mr/READY3/.claude/skills/dev/SKILL.md` by reading the file directly. The same-named personal/global `dev` Skill (0.5.25) was not invoked. Nothing under `~/.claude/skills/dev` or in settings was read for execution or modified.
- Version evidence: `core/references/parallel-build.md` has the header "Opt-in two-task parallel Build pilot (0.5.26)". SKILL.md itself has no version field.
- This run does not show native `/dev` discovery of 0.5.26.
- Route taken, per the SKILL.md action table and its "Boundaries" paragraph for `develop --parallel`: orchestration → Scope (workflow, impact, task-semantic, historical-regression) → project profile → `parallel-build.md` → bundled `specialists/featrace-build/SKILL.md`.

## References actually used, and why
| Reference | Why |
|---|---|
| `SKILL.md` | Entry point and routing table. |
| `core/references/orchestration.md` | Required first for any feature mutation. Defines the Scope→Build handoff, and states that the parallel pilot requires current task/history review records. |
| `core/references/workflow.md` | Develop invariants. Parallel mode does not skip Scope. If review records are missing and writes are disallowed, the run is blocked. |
| `core/references/impact-review.md` | Pre-edit boundary (impact.json, allowed paths, preserved behavior). |
| `core/references/task-semantic-review.md` | Checks whether the task-meaning review is current. |
| `core/references/historical-regression.md` | Checks the historical-fix candidate review. |
| `core/references/parallel-build.md` | Eligibility rules, then prepare/preflight/dispatch/integrate. |
| `profiles/generic/PROFILE.md` | Profile for a pure-Python, non-Android project. Commands must come from evidence or explicit user choice; here they came from the supplied plan. |
| `specialists/featrace-build/SKILL.md` | Given to each worker. The router read it to write the dispatch prompts. |

Not loaded:
- `module-context.md`: no module catalog, and the feature does not opt into module context. `feature-status` reports `MODULES: unclassified`.
- `project-baseline.md`: no scan was requested.
- The Requirement, Repair, Verify and Deliver references: those stages were not entered.

## Existing review freshness and develop result
All of these were read-only checks. None of the `sync`/`review` subcommands were run.
- `validate-feature.py <PROJECT> FEAT-001 --stage develop` → `FEATURE_VALID`, exit 0, no warnings.
- `feature-status.py` reports:
  - R-1 is confirmed, with 0 blocked or inferred requirements.
  - `TASK_SEMANTICS: current`.
  - `HISTORICAL_REGRESSION: candidates=0, pending=0`.
  - No unresolved fixes or clarifications, and the feature is not archived.
- `task_review.py show`: the current digest equals the reviewed digest (`8e46deb2…451b`). The review covers T-UP and T-LOW against R-1 and `sources/prd-original.txt:1`.
- `regression_review.py show`: schema v2 with scope paths `lower.py` and `upper.py`, zero candidates, review digest `d38b327c…73eb`. A zero-candidate sync is a valid record, and I did not invent a retest.
- `impact.json`:
  - base is `0999e6e`;
  - allowed and inspected paths are exactly `upper.py` and `lower.py`;
  - all six mechanisms are reviewed with evidence;
  - B-PRESERVE requires each task to leave the other entry point unchanged.
  - `impact.py` reported `changed_paths: []`, so the business tree was clean.
- `prd-intake.json` has a develop-stage review and a complete inventory. The single source item S-1 maps to R-1.
- **Scope exit: `ready`.**
  - Selected tasks: T-UP and T-LOW, both `planned`, both linked to R-1.
  - No decisions are pending and no product facts were missing.
  - Independence evidence holds: `upper.py:1-2` and `lower.py:1-2` are separate pure `convert` functions with no imports, and each test imports only its own module.

## Plan
- Used `/private/tmp/featrace-claude-0526-w1ged5mr/READY3/plan.json` unchanged. Its sha1 was `58a027fa…855e` before and after the run.
- The task checks and integration check are real unittest argv arrays using `/Library/Developer/CommandLineTools/usr/bin/python3` (3.9).

## Build: prepare, preflight, workers
- `prepare` → `PARALLEL_BUILD_PREPARED`, run_digest `600e4f9b…b213`.
- `preflight` → `PARALLEL_BUILD_INPUTS_CURRENT`.
- The helper created two detached worktrees at `0999e6e` under `attempt/workers/`.
- I dispatched two native background Agents (general-purpose) at the same time. Each got only:
  - its task ID, worktree, RUN directory and frozen-input path;
  - the Skill root and the Build specialist path;
  - the side-effect restrictions.
- I gave no implementation hint. The file-ownership split is an instruction plus the helper's post-run hash and ownership checks, not a permission-enforced sandbox.

| Task | Return | Changed | Check | Patch sha256 |
|---|---|---|---|---|
| T-UP | `ready` | `upper.py` (`return value.upper()`) | `test_upper.py` passed (Ran 1, OK) | `20cc9013…7fd8` |
| T-LOW | `ready` | `lower.py` (`return value.lower()`) | `test_lower.py` passed (Ran 1, OK) | `5d29991a…7708` |

- I checked the files on disk rather than relying on the workers' messages:
  - `returns/<task>/patch.diff` hashes match `result.json`;
  - each worktree's `git diff` matches its patch;
  - each worktree changed only its own file.
- The two check logs have identical hashes because both tests print the same unittest output text.
- Neither return touched `.agent-workflow`. The worker state reports it as `missing`, because it is gitignored and not present in the worktrees.
- I saw no semantic conflict: the patches are disjoint single-line changes to independent functions, and the interface `convert(str)->str` is unchanged.

## Integration (external candidate only)
- `integrate` → `candidate_checks_passed`, base `0999e6e36fa8…`, candidate tree `d52165715259258da3837731a70eac3849b7da96`.
- Integration check: full `unittest discover -s tests` → Ran 2 tests, OK (log sha256 `a6707d4e…c3da`).
- The candidate is in `attempt/integration`, with `upper.py` and `lower.py` changed in the index and not committed.
- The supplied integration check only covers the two acceptance criteria. It does not separately assert the preserved behavior (no input mutation, no side effects). That behavior rests on the diff inspection above.

## Primary unchanged: evidence
- HEAD is `0999e6e36fa8ad2a4ee91fbf70f7275a6c4a6bfd` before and after. The branch is still `main` and `git status --porcelain -uall` is empty.
- The `git ls-files -s` digest is `7d03dae2…33ddc` before and after, so the index is unchanged.
- A sha1 manifest of every non-`.git` file in the project, including `.agent-workflow`, was identical before the run, after the review checks and after integration (`PRIMARY_UNCHANGED`).
- The only primary Git mutation was worktree registration for `attempt/workers/T-UP`, `attempt/workers/T-LOW` and `attempt/integration`, which was authorized. No commits, pushes, cleanup, retries, network/MCP calls, or settings/plugin/personal-install changes were made.

## Timing (observed, not a claimed speed gain)
- prepare + preflight: about 0.8s (09:46:27Z).
- Workers ran concurrently, taking about 33.2s (T-UP) and 33.9s (T-LOW) per host-reported duration.
- Token use: about 32.5k (T-UP) and 33.6k (T-LOW) subagent tokens.
- integrate: about 0.7s (09:47:30Z).
- There was no serial baseline for the same stage, so no speedup can be claimed. For a two-line change, overhead dominates.

## Limitations
- The candidate is not delivered. To adopt it, a separate authorized ordinary Build step would need to:
  1. recheck primary freshness;
  2. apply the candidate to the primary checkout;
  3. serially update task status, traceability and verification records;
  4. run ordinary Verify/check/audit against the real primary snapshot.
- The helper's hash checks and the worker boundaries detect drift after the fact; they are not a security sandbox. Git worktrees share repository metadata.
- Nothing here proves that the workers actually loaded or understood the specialist. Their returns and the post-run checks are the only evidence.
- The existing reviews were fixture-authored (`synthetic-fixture-reviewer`, `fixture-author`). I checked that they are current and structurally valid, not that their judgement is independently correct.
- Kept for inspection: the attempt directory, both worktrees and the integration worktree. No cleanup was performed.
