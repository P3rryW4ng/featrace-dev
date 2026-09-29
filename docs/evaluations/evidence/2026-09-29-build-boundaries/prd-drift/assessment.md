# FEAT-001 parallel Build continuation — assessment

## Skill loaded
- Invoked with the native Skill tool: `featrace-boundary:dev`, args `develop FEAT-001 --parallel`.
- Actual Skill root: `/private/tmp/featrace-boundaries-0529-9g1bi_gu/plugin/skills/dev`
- Plugin manifest `plugin/.claude-plugin/plugin.json`: `featrace-boundary` version **0.5.29**. `core/references/parallel-build.md` has the header "(0.5.29)".
- Rules applied: SKILL.md and `core/references/parallel-build.md`, specifically the "Integrate and hand back" return gate and the drift rules in "Dispatch two workers". I did not use personal dev0.5.28 or the source repository.

## Evidence inspected (read-only)
- Project `prd-drift/project`: HEAD `27f72944…` (= attempt `base_revision`). No tracked changes. `.agent-workflow/` is ignored. Worktrees: primary plus two detached workers at 27f7294.
- Attempt `run.json`: plan is T-UP (`upper.py`) and T-LOW (`lower.py`), with approved per-task unittest checks and integration check `python3 -m unittest discover -s tests`. It also has the frozen input snapshot.
- Returns:
  - `returns/T-UP/result.json`: status `ready`. changed_paths `[upper.py]`. Check `test_upper.py` passed (rc 0, "Ran 7 tests … OK"). patch_sha256 `0be8ec88…` matches the actual `patch.diff`.
  - `returns/T-LOW/result.json`: status `ready`. changed_paths `[lower.py]`. Check `test_lower.py` passed (rc 0, "Ran 7 tests … OK"). patch_sha256 `0183b192…` matches the actual `patch.diff`.
  - Worker worktrees show only `M upper.py` and `M lower.py` respectively, inside their allowed paths.
  - Summaries say these are maintainer-reused synthetic patches with real approved tests. They are not new Agent coding.
- Frozen inputs compared with current primary records (`diff -r attempt/inputs/.agent-workflow project/.agent-workflow`):
  - **Drift:** `features/FEAT-001/sources/prd-original.txt`
    - frozen sha256 `2d00bc96…` (also recorded in run.json snapshot)
    - current sha256 `77ce6128…`
    - The current file adds: "Isolation changed product input: CSV SKU matching is now case-insensitive; reconcile this addition before implementation."
  - All other FEAT-001 records are identical.

## Decision
- Both returns claim `ready`, but the primary source evidence changed after prepare. Under the 0.5.29 rules, source/requirement drift blocks the attempt. A stale attempt hits the return gate: preserve both workers and their evidence, report the blocker, and **end this Build attempt without invoking `integrate`**. The returns also cannot be adopted into primary, because they were built and checked against the superseded PRD. The new case-insensitive SKU rule affects the T-UP CSV importer and is not reconciled into requirements/tasks.
- **Eligible next action:** none in this Build attempt. The next workflow route is **Requirement**:
  1. Reconcile the changed source into `requirements.json`.
  2. Renew the PRD review.
  3. Review the affected tasks (at least T-UP) against their linked requirements.
  4. Recheck impact/regression.
  5. Run develop validation.
  6. Only then prepare a new parallel attempt, or a serial Build.

  This continuation did not authorize any of these steps (requirement sync/review, prepare, workers). The case-insensitive SKU behaviour may also need a product confirmation before it becomes a requirement.
- Blockers: unreconciled source drift in `prd-original.txt`. A new attempt is needed after reconciliation.

## Helper calls actually made
- None. I did not call `parallel-build.py` (prepare/preflight/finish/integrate) or `validate-feature.py`. There were no tests, Agents, or writes other than this file.
- Commands I ran were read-only: `cat`, `diff -r`, `shasum`, `stat`, `git status/log/rev-parse/diff --stat/worktree list`, and `git -C <worker> status`.

## Limitations
- I did not run the helper's own freshness recheck. Drift was established by direct diff and by comparing hashes with the run.json snapshot.
- I did not review patch contents semantically against the old or new PRD.
- The source modification time equals the return times (14:00:38), so ordering could not be distinguished from timestamps. The hash mismatch against the prepare-time snapshot is still conclusive for staleness.
- As instructed, I did not read the evaluator records (fault.json, before-*.json, *-fault.txt, maintainer-negative-integrate.txt, prior assessments) or the source repo.
- Project, attempt, worktrees and returns are left unchanged. HEAD and index are intact.
