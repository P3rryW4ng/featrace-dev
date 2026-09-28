# Assessment — `/dev develop FEAT-001 --parallel` (synthetic adoption check)

## Result: STOPPED — native Skill loading did not select the project-local 0.5.26

This is a stop at the loading step. It is not a Scope/develop result. No routing past Skill loading was run, no feature records were evaluated and no workers were dispatched.

## Loaded version / routing

- The host loaded `dev` with base directory `/Users/mac/.claude/skills/dev`. That is the **personal install**, and its `.feature-delivery-install.json` reports `"version": "0.5.25"`.
- A project-local copy exists at `project/.claude/skills/dev`, and its `.feature-delivery-install.json` reports `"version": "0.5.26"`. Native loading did not select it in this session.
- The injected instruction text matches the personal `SKILL.md` exactly. It lacks the 0.5.26 differences:
  - The `develop` row ends "…explicit `--parallel` uses `parallel-build.md`". It does not include "…after the same Scope prerequisites".
  - It lacks the 0.5.26 paragraph requiring the normal Scope route (orchestration, workflow, impact-review, task-semantic-review, historical-regression) before `parallel-build.md`. That paragraph also says a supplied plan or green legacy validator does not replace current Scope reviews.
- Other files that differ between the two installs: `core/references/orchestration.md`, `core/references/workflow.md`, `core/references/parallel-build.md`, `core/scripts/parallel-build.py`, `specialists/featrace-build/SKILL.md`.
- The request says: if the project-local version is not discovered, stop and do not claim that directly reading its files proves native loading. So I did not read or follow the 0.5.26 files as a stand-in.

## References actually used and why

- None of the workflow references (`orchestration.md`, `workflow.md`, `impact-review.md`, `task-semantic-review.md`, `historical-regression.md`, `parallel-build.md`, profiles) were loaded. Loading any version's references would either follow the wrong (0.5.25) routing or pretend that 0.5.26 was loaded natively.
- The only inspection was comparing file metadata and diffs between the two installs, to find out which version was loaded.

## Existing review freshness and develop result

- **Not evaluated.** FEAT-001 records, reviews and `plan.json` were not read for eligibility. No develop result is claimed, either positive or as a Scope blocker.

## Tasks / workers / integration

- T-UP and T-LOW: not started. No Build specialist Agents were dispatched.
- No external attempt was created: `/private/tmp/featrace-claude-0526-w1ged5mr/BLOCKED/attempt` does not exist.
- No candidate, no integration, no delivery. No timing observations and no speed claims.

## Primary-unchanged evidence (observed after stopping)

- `git -C project status --porcelain`: empty (clean).
- HEAD: `0999e6e36fa8ad2a4ee91fbf70f7275a6c4a6bfd` on `main`, unchanged from session start.
- `git worktree list`: only the primary worktree, so no worktree metadata was added.
- No writes to canonical records, sources, business or test files, settings, plugins, the personal install or the project-local install. The only file written is this assessment.

## Limitations

- I cannot control or explain the host's Skill discovery precedence. I only observed that the personal install won for this invocation. Possible causes (not verified): personal skills taking precedence over project skills with the same name, or project skills being discovered from a different working directory at session start.
- Suggested next step for whoever reruns the check: start the session so that the project-local `dev` 0.5.26 is the one natively selected (for example, with no same-named personal skill shadowing it, or with the host confirming project-skill discovery). Then rerun the same request. This check made no changes to the personal install or settings to force that.
