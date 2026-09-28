# Assessment: `develop FEAT-001 --parallel` (tasks T-UP, T-LOW)

**Result: Scope blocked. Stopped before prepare/dispatch. No attempt, no worktrees, no workers, no integration candidate.**

## 1. Loaded Skill version and routing

- Loaded Skill: `/private/tmp/featrace-claude-0526-w1ged5mr/BLOCKED2/.claude/skills/dev/SKILL.md`. Its `.feature-delivery-install.json` reports `featrace-dev` version **0.5.26**, and `parallel-build.md` has the heading "(0.5.26)". I read this file directly. I did not invoke the personal/global `dev` Skill (0.5.25) or the Skill tool. This run does not test native `/dev` discovery.
- Routing in SKILL.md: `develop [ID]` routes Scope → Build. Explicit `--parallel` uses `parallel-build.md` only "after the same Scope prerequisites". The cross-stage boundary says: "a supplied plan or green legacy validator does not replace current Scope reviews. Missing reviews with writes disallowed mean stop before prepare/dispatch."

## 2. References used and why

| Reference | Why it was loaded |
|---|---|
| `core/references/orchestration.md` | Required first for any feature mutation. It defines the Scope/Build contract and says the parallel pilot needs current task/history review records, and that read-only missing reviews block. |
| `core/references/workflow.md` | Required with orchestration for the develop route. Its "Optional isolated parallel Build" section says the pilot needs both review records even for legacy features. If writing them is out of scope, stop with Scope blocked. |
| `core/references/impact-review.md` | A named Scope prerequisite for develop. I used it to judge `impact.json`. |
| `core/references/task-semantic-review.md` | A named Scope prerequisite. It says `task-review.json` is the canonical record and `task-review.md` is only a generated view. |
| `core/references/historical-regression.md` | A named Scope prerequisite. It says `regression-review.json` is canonical and the rendered `.md` is only a view. Sync (`regression_review.py sync`) writes that record. |
| `core/references/parallel-build.md` | The route for explicit `--parallel`. It holds the eligibility rule that decided this run. |

Not loaded, deliberately: `module-context.md` (no module catalog; its rules did not come into play) and `project-baseline.md` (no scan was allowed or needed). The project profile was not loaded either, because the run stopped before any command choice or Build work. Requirement, Repair, Verify and Deliver references were not relevant.

## 3. Existing review freshness and develop result

Feature records in `project/.agent-workflow/features/FEAT-001/`:

- `spec/requirements.json`: R-1 is `confirmed`. PRD present; API/Figma `not_applicable` with reasons.
- `tasks.json`: T-UP and T-LOW, both `planned`, both linked to R-1.
- `impact.json`: present. Base `0999e6e3…`, allowed paths `upper.py` and `lower.py`, all six mechanisms `reviewed`. The evidence text is generic ("Synthetic independent files reviewed"), and B-1 has no preserve behavior. That is acceptable for a synthetic fixture, but noted.
- **`task-review.json`: missing.** Only `task-review.md` exists. It claims reviewed digest `8e46deb2…` equals the current digest, but the Markdown is a generated view and not the authority. Freshness cannot be established without the canonical JSON.
- **`regression-review.json`: missing.** Only `regression-review.md` exists (it says zero candidates, digest `d38b327c…`). This is also a view only, with no canonical record behind it.

Develop validator (read-only, `PYTHONDONTWRITEBYTECODE=1`):

```
$ python3 core/scripts/validate-feature.py --stage develop <project> FEAT-001
WARNING: historical regression review missing; sync it before new business-code edits
WARNING: task semantic review missing; sync and review tasks before business-code edits
FEATURE_VALID        (exit 0)
```

`feature-status.py` reported: 1 confirmed requirement, 0 blocked, tasks done 0/2, no unresolved fixes or clarifications, modules `unclassified`.

**Develop result for the parallel pilot: blocked.** The green validator result only reflects legacy compatibility warnings. `parallel-build.md` says that for this opt-in mode both `task-review.json` and `regression-review.json` "must exist and pass the existing develop validator, even for legacy features where missing records would ordinarily warn", and that a missing record stops prepare. The helper enforces the same rule itself (`core/scripts/parallel-build.py:107-111` raises "parallel Scope review missing … no workers created").

**Concrete Scope blocker:** `FEAT-001/task-review.json` and `FEAT-001/regression-review.json` do not exist. The ordinary fix is `task_review.py sync` plus `task_review.py review` (with exact `--task/--requirement/--evidence`), and `regression_review.py sync` plus a disposition if any candidates appear. Every one of those steps writes a canonical record, and this turn forbids all canonical record writes and creating or refreshing reviews. So the prerequisite cannot be met here.

What I did not do, as instructed: I did not treat the warnings as a waiver, did not fall back to serial Build, did not ask workers to create the records, and did not hand-write the JSON from the Markdown views.

**Next eligible action (needs new authorization):** a run that allows the Scope review writes performs the task-review and regression-review sync/review flows. Then re-run `validate-feature.py --stage develop` and start a new parallel attempt.

## 4. Tasks, workers and integration

- The supplied `plan.json` was read and left unchanged. It declares the two tasks with disjoint `allowed_paths` (`upper.py` and `lower.py`), no dependencies, real unittest checks, and an integration check. Its declared independence looks plausible from the code: two separate `convert` stubs that each return the input unchanged, and separate tests. But plan eligibility was never reached, because Scope failed first.
- `parallel-build.py prepare` and `preflight` were **not** run. `/private/tmp/featrace-claude-0526-w1ged5mr/BLOCKED2/attempt` was **not** created.
- No Build specialist Agents were dispatched. There are no worker returns, patches, check logs or integration candidate. No implementation was attempted or suggested.

## 5. Evidence the primary project is unchanged

- `git rev-parse HEAD` = `0999e6e36fa8ad2a4ee91fbf70f7275a6c4a6bfd` before and after.
- `git status --porcelain --ignored` shows only `!! .agent-workflow/` (ignored) before and after. There are no tracked or untracked business changes.
- `git worktree list` shows only the primary worktree. No worktree metadata was created.
- SHA-256 of all tracked files plus every FEAT-001 record was taken before any helper ran and again at the end: identical (`diff` empty).
- The only helpers I ran were `validate-feature.py` and `feature-status.py`, with bytecode writing disabled. A grep of both scripts found no file-write calls.
- No commits, pushes, network/MCP calls, settings/plugin changes or personal-install changes. The one file written is this assessment. (A temporary hash list, `/tmp/blocked2-before.sha`, was written outside the project for the comparison.)

## 6. Limitations

- Nothing was delivered and there is no candidate. So there is no candidate result, delivery result, worker timing or speed measurement, and no claim of any parallel speed-up. Observed time was spent only on reading references and running read-only checks.
- The hash and structure checks show the files didn't change. They cannot prove that the Markdown review views were once backed by real reviews, or that the reviews would still be semantically current.
- The "unchanged" evidence covers tracked files, FEAT-001 records, HEAD, index/status and the worktree list. It does not cover every ignored file in the environment.
- Boundaries were kept by following instructions and by self-checks. No sandbox enforced them.
- This check exercised the project-local 0.5.26 Skill by reading it explicitly. It does not show that native `/dev` discovery selects 0.5.26; that belongs to the later personal-install check.
