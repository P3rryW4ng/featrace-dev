# Assessment: `develop FEAT-001 --parallel` (FeatraceDev 0.5.26, project-local Skill)

## Result

**Blocked before Scope exit. No attempt was prepared and no workers were dispatched.**
`/private/tmp/featrace-claude-0526-w1ged5mr/READY2/attempt` was not created, no worktree was registered, no Build Agent ran and nothing was integrated. There is no candidate and no delivery.

Concrete blocker: the required feature-selection check fails for FEAT-001.

```
$ python3 core/scripts/feature-context.py resolve project --feature FEAT-001
FEATURE_CONTEXT_ERROR: Feature title/status must be strings      (exit 1)
```

`spec/requirements.json` → `feature` has `id` and `status` but no `title`. SKILL.md says to "Confirm the project, feature ID and title before mutation". `feature-selection.md` says to "Display project, ID and title before work. On missing, malformed, mismatched or out-of-project records stop dependent actions." `develop` changes the feature, so it depends on selection and has to stop here.

Fixing this means writing a product fact (the feature title) into a canonical record. That is outside this turn: canonical writes are prohibited and I was told not to invent product facts. I did not ask a worker to fill it in, and I did not switch to serial Build.

What is needed to unblock: the user supplies the authoritative FEAT-001 title, and a separate authorized turn records it in `spec/requirements.json` and re-runs `feature-context.py resolve` and `validate-feature.py --stage develop`. Then start a new attempt.

## Loaded version and routing

- Loaded: `/private/tmp/featrace-claude-0526-w1ged5mr/READY2/.claude/skills/dev/SKILL.md`, read directly with the Read tool. `parallel-build.md` identifies itself as the "(0.5.26)" pilot. I did not invoke the personal/global `dev` Skill at `~/.claude/skills/dev` (0.5.25), and I did not read or change it. This does not show that `/dev` discovers 0.5.26 natively.
- Route I followed from SKILL.md: `develop [ID]` → Scope → Build. With explicit `--parallel`, the normal Scope route comes first (`orchestration.md` + `workflow.md` + `impact-review.md` + `task-semantic-review.md` + `historical-regression.md`), then `parallel-build.md`. Because this is a feature-scoped action, `feature-selection.md` also applies.

## References used and why

| Reference | Why |
|---|---|
| `core/references/orchestration.md` | Required first for any feature mutation; Scope/Build contracts, stop rules |
| `core/references/workflow.md` | Develop invariants; says parallel does not skip Scope |
| `core/references/feature-selection.md` | Feature-scoped action; requires confirming ID and title; **source of the blocker** |
| `core/references/impact-review.md` | Scope prerequisite before business-code edits |
| `core/references/task-semantic-review.md` | Scope prerequisite; checked task-review freshness |
| `core/references/historical-regression.md` | Scope prerequisite; checked regression-review record |
| `core/references/parallel-build.md` | Explicit `--parallel`; eligibility rules, and what to do when Scope is blocked |
| `profiles/generic/PROFILE.md` | Project profile for a Python fixture, used to judge the check commands |

Not loaded, because no condition called for them: `module-context.md` (no catalog, and I was told not to scan), `project-baseline.md`, and the Requirement/Repair/Verify/Deliver references. I did not open `specialists/featrace-build/SKILL.md` because dispatch never happened.

## Existing review freshness and develop result (read-only)

- `feature-status.py`: confirmed=1, blocked=0; TASKS done=0/2; HISTORICAL_REGRESSION candidates=0, pending=0; TASK_SEMANTICS current (history=1); unresolved fixes/clarifications 0; MODULES unclassified.
- `validate-feature.py --stage develop project FEAT-001` → `FEATURE_VALID` (exit 0).
- `task-review.json`: current digest = reviewed digest `8e46deb2…451b`; covers T-UP and T-LOW against R-1 and `sources/prd-original.txt:1`. Current.
- `regression-review.json`: exists; zero candidates; review digest `d38b327c…73eb`; paths `lower.py`, `upper.py`. The validator accepts it. I did **not** re-run `regression_review.py sync` because it writes.
- `impact.json`: base `0999e6e`, allowed paths `upper.py` and `lower.py`, all six mechanisms marked `reviewed`.
- Tasks T-UP and T-LOW are both `planned`. The primary business worktree is clean; `.agent-workflow/` is gitignored.

Scope concerns that are not the deciding blocker, but would need attention in an authorized Scope pass:
- Every mechanism in `impact.json` has the same placeholder evidence ("Synthetic independent files reviewed"), with no file/line findings.
- `impact.json` has only one `change` behavior (B-1). It has no `preserve` behavior, even though `plan.json` says to preserve "Do not change the other entry point".
- There is no `module_scope` or module label (MODULES: unclassified), and I did no module investigation, per the instructions.
- `impact.md` has not been rendered.

A green validator result checks structure, not truth. It does not override the selection failure.

## Plan eligibility (reviewed, unchanged)

`plan.json` is well formed for the helper. It has two tasks with no overlapping `allowed_paths` (`upper.py` and `lower.py`), no dependencies, and real unittest argv checks for each task plus an integration check, with timeout 10. Independence evidence (`upper.py:1-2`, `lower.py:1-2`) matches the code: two separate pure `convert` stubs with no shared state. I left the plan unchanged. On its face it would have been eligible if Scope had exited `ready`. Note that `parallel-build.py prepare` does not call `feature-context.py` itself; it checks the develop validator and ownership. It probably would have succeeded. The block comes from the router's routing rules, not from a helper failure. I did not run `prepare` to test this.

## Worker and integration results

None. No workers, patches, check logs, integration candidate, timing or token measurements exist. No speed gain can be claimed or measured from this run.

## Primary unchanged evidence

I recorded the state before and after my commands (HEAD, `git write-tree`, `git status --porcelain --ignored`, SHA-256 of every non-.git file, `.git/index` hash). `diff` showed them identical:

- HEAD `0999e6e36fa8ad2a4ee91fbf70f7275a6c4a6bfd`, tree `44768ed41cd88bdb76fcc34da0e25fe317211624`
- status: only `!! .agent-workflow/` (ignored, pre-existing)
- `.git/index` sha256 `052c7d34…41fe2`, unchanged
- `git worktree list`: only the primary checkout
- no `__pycache__` created under the Skill directory

The only file I wrote is this assessment (plus scratch snapshots at `/tmp/ready2-primary-{before,after}.txt`). There were no commits, pushes, network/MCP calls, or changes to settings, plugins or the personal install.

## Limitations

- The snapshots cover files and Git state at those moments. They are not a sandbox or an audit of every process.
- I couldn't re-confirm regression-review freshness beyond the validator without a writing sync.
- My Scope concerns about impact evidence are judgments. I did not act on them.
- This run shows that the router stops at the selection gate. It does not show how the 0.5.26 Build specialist behaves, how integration behaves, or any timing.
