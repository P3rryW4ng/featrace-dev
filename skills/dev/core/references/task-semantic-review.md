# Task semantic review (0.5.13)

Use after generating tasks and whenever task wording, scope, requirement links, dependencies or other task meaning changes. This is part of PRD/develop/revise/fix flows, not a user-facing command.

Progress and meaning are separate. Changes to `status`, `test_evidence`, `test_waiver`, verification, implementation revision, timestamps or assignee do not change the semantic digest. Other task fields do. A digest detects changed content; it cannot decide whether the new wording matches the product requirement.

Run `task_review.py sync <PROJECT> <ID>` after editing task semantics. Read only the changed tasks, their previous reviewed snapshot, linked requirements, relevant source items, approved decisions/revisions/fixes, and affected tests. Do not reread unrelated PRD sections solely because task progress changed.

After the comparison, record it with `task_review.py review` and exact repeated `--task`, `--requirement` and `--evidence` arguments. Evidence must identify what was actually compared, such as a requirement/acceptance criterion, source item, approved decision, revision or linked fix. The helper requires the task and requirement sets to match the detected change; its success records attribution, not semantic correctness.

New workspaces opt in through `feature.task_review_required`. Existing workspaces adopt when sync first runs; do this before their first semantic task edit so the prior wording is not lost. Missing, stale or unreviewed task semantics block develop/check only after adoption. `task-review.json` is canonical, `task-review.md` is generated, and superseded reviews remain in tamper-evident history.
