# Requirement workspace schema

Each feature is stored at `.agent-workflow/features/<feature-id>/`.

```text
sources/                 Immutable original PRD, API, Figma exports and links
spec/requirements.json   Canonical requirement records
spec/spec.md             Generated, human-readable requirement view
tasks.json               Atomic implementation slices and status
decisions.json           Conflicts, user choices, and supersession history
decisions.md             Generated decision view
traceability.json        Source → requirement → task → code → test links
traceability.md          Generated traceability view
delivery-report.md       Quality-gate result and remaining risk
```

## Requirement fields

- `id`: stable identifier such as `R-012`.
- `status`: `inferred`, `confirmed`, `blocked`, or `deprecated`.
- `sources`: a precise PRD heading, API operation/field, Figma node, or decision ID.
- `statement`: one testable behavior.
- `acceptance_criteria`: observable outcomes, including loading, empty, error, and permission states where relevant.
- `assumptions`: unresolved facts. Each must state what evidence would confirm it.
- `tasks` and `tests`: stable IDs, never prose-only promises.

`requirements.json`, `tasks.json`, `decisions.json`, and `traceability.json` are the only editable workflow records. Run `render-workspace.py` after editing them; generated Markdown must not become a second source of truth.

## Decision format

```md
## D-003 — Login destination conflict

- Status: approved
- Conflicting sources: PRD R-012; Figma node 123:456
- Field: post_login_destination
- Options: A. Home; B. Profile completion
- Chosen: B
- Impact: R-012, T-012-03, UI-012
- Supersedes: inferred destination in R-012
- Rationale: product owner confirmation on 2026-09-15
```

Never delete a decision. Mark it superseded and link the replacement when a later decision changes it.
