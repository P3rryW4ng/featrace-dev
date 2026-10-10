# Commit a completed Build task

Load when the router is finishing an implemented task in the primary Git checkout, whether Build was serial or a parallel candidate has been adopted. This is an internal Build handoff, not a new user command or a Git hook. The product owner's default is one local commit per completed task, soon after that task's code, focused checks and task/traceability records are ready; do not accumulate independent tasks into one end-of-feature commit. An explicit no-commit/read-only request, repository policy, or unavailable Git identity takes precedence. Do not push, open a PR, archive or mark the feature complete as a side effect.

## Separate task readiness from delivery acceptance

Before committing, confirm the task's linked requirement meaning and Scope/develop prerequisites are current. Inspect the actual changed behavior and run the focused checks needed to support this task; record the command, result and limits in its existing `test_evidence` or an honest waiver. A compile-only check is not proof of UI or product acceptance. Update the task to `done` only when its implementation slice is done, with corresponding traceability and rendered views. A requirement may remain provisional, and manual acceptance or other tasks may remain pending. Do not run the full feature `check`, `audit-delivery`, device matrix or whole-project scan merely to create this task commit; those run when their actual risk or Verify/Deliver stage requires them. Reuse a still-current earlier check instead of rerunning it for Git bookkeeping.

## Isolate and inspect the commit

1. Read Git status, including staged, unstaged and untracked paths, before staging. Identify this task's code, tests, and shareable task/traceability records. Follow `git-sharing.md` for ignored original sources, local quality reports, secrets and repository access. Do not stage generated local state or unrelated changes.
2. Stage only exact task paths or reviewed hunks; never `git add -A` for this automatic task commit. If the index already holds unrelated changes, a task file contains inseparable pre-existing edits, another writer is active, or the task cannot be isolated from a peer's uncommitted work, stop the automatic commit and preserve the work. Explain the concrete overlap; do not reset, stash, discard or silently include somebody else's edits. For independent parallel tasks, workers and the integration candidate do not commit. After full candidate adoption into the primary checkout, the router updates shared records serially and stages/commits each truly separable task in turn. If the adopted changes cannot be honestly separated, report that limitation instead of pretending each task got an independent commit.
3. Read the full staged diff, run `git diff --cached --check`, and compare staged paths with this task's actual scope and focused check evidence. If any check failed or the staged diff is not understood, fix or leave the task uncommitted; do not bypass with a vague message. Commit locally once this review succeeds, then report the commit hash, task ID, actual checks and remaining feature-level verification. A later code edit needs new relevant checks and evidence. A records-only follow-up commit may be needed after final Verify/Deliver; it is not a substitute for the task commit.

## Commit message

Use `<type>(<feature-ID>/<task-ID>): <observable outcome>` as the subject. Choose `feat`, `fix`, `refactor`, `test` or `docs` by the actual change. Describe the business or developer-visible result, not the command or file-edit activity. Keep one coherent task per subject; do not claim the whole feature is complete when only one task is done. Add a short body when it improves review:

```text
feat(OGFR-6256/T-1): show document reminder after Basic Info save

Why: R-1 requires a reminder before identity verification.
Checks: DocPrep unit tests passed; app compilation passed.
Pending: device acceptance and feature-level check/audit.
```

Use the project's normal language and commit convention when one exists; preserve feature/task IDs and concrete outcome. Name unavailable or unrun checks as pending, never as passed. No fabricated co-author line, tested revision or approval. Do not amend or rewrite a prior task commit merely to tidy its wording without separate authorization.
