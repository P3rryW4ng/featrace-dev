# Requirement workspace schema

Each feature is stored at `.agent-workflow/features/<feature-id>/`.

```text
sources/                 Immutable original document/HTML PRD parts, API, Figma exports and links
spec/prd-intake.json      Reading inventory, source excerpts and coverage review
spec/prd-analysis.md      Generated reading/coverage view
spec/requirements.json   Canonical requirement records
spec/spec.md             Generated, human-readable requirement view
tasks.json               Atomic implementation slices and status
decisions.json           Conflicts, user choices, and supersession history
decisions.md             Generated decision view
traceability.json        Source → requirement → task → code → test links
traceability.md          Generated traceability view
fixes.json               Canonical mismatch/repair records
fixes.md                 Generated fix history
delivery-report.md       Quality-gate result and remaining risk
```

## Requirement fields

- `id`: stable identifier such as `R-012`.
- `status`: `inferred`, `confirmed`, `blocked`, or `deprecated`.
- `source_item_ids`: stable references to mapped items in `spec/prd-intake.json`; required for active requirements before development.
- `sources`: array of `{type, ref}` objects naming a precise PRD heading, API operation/field, Figma node, or decision ID.
- `statement`: one testable behavior.
- `acceptance_criteria`: observable outcomes, including loading, empty, error, and permission states where relevant.
- `assumptions`: unresolved facts. Each must state what evidence would confirm it.
- `tasks` and `tests`: stable IDs, never prose-only promises.

`requirements.json`, `tasks.json`, `decisions.json`, and `traceability.json` are the editable product workflow records; `spec/prd-intake.json` separately records reading evidence and coverage; `fixes.json` records observed mismatches, primary/contributing causes, task description before/after, and regression evidence without duplicating PRD authority. Run `render-workspace.py` after editing them; generated Markdown must not become a second source of truth.

## Actual record shapes and state limits (0.4.7)

The files under `core/schemas/` describe only shallow containers. The Python validators are the executable contract. The following fields are the ones most often needed when editing a feature; this list does not claim full JSON Schema enforcement.

- `requirements.json`: `feature.id` must match the folder. Active requirement `status` is one of `inferred`, `confirmed`, `blocked`, `deprecated`. Each requirement needs text `id`, `title`, `statement`; `sources` is a non-empty array of objects with non-empty `type` and `ref` (e.g. `{"type":"prd","ref":"sources/prd-original.html#section-2"}`). `acceptance_criteria`, `tasks`, `tests`, `assumptions` are arrays. Develop/check require non-empty acceptance, task and test arrays for active requirements. Source-item links and review follow `prd-analysis.md`.
- `tasks.json`: top level `feature_id` and `tasks` array. Each task has an `id`, a `status` of `planned`, `in_progress`, `blocked`, or `done`, and a non-empty `requirement_ids` array naming existing requirements. Check requires a done task to have `test_evidence` or `test_waiver`; the current validator tests presence, not whether the evidence is true or a particular type. Prefer a readable string with the actual run result and code revision.
- `decisions.json`: top level `feature_id` and `decisions` array. Each decision needs an `id`; `pending` and `blocked` prevent develop/check, and `approved` needs a `chosen` value. Other states and confirmation provenance are not yet fully validated; keep the original user confirmation reference, scope and supersession details and review them manually.
- `traceability.json`: top level `feature_id` and `links` array. Every link requires an existing `requirement_id`; check requires at least one link for every active requirement. The validator does not fully prove task/code/test reverse links.
- `fixes.json`: see `fix-workflow.md`. `verification` and `evidence` must be arrays of non-empty strings. `regression_test_ids` is an array of declared test ID strings for verified repairs; `regression_scope_notes` maps selected cross-scope test IDs to non-empty reasons. `closed` uses a `closure` object with `outcome`, `reason` and `evidence`, with further fields per outcome.
- `spec/prd-intake.json`: each registered source has `id`, a relative `path` under `sources/`, and `kind` (`document` or `html`). Each coverage aspect points to a requirement `statement` or an acceptance criterion using `field: "acceptance_criteria/0"` (zero-based index), with exact `target_text`; the validator intentionally treats changed targets as requiring review. Do not silently refresh `target_text` and leave the review marked verified.

Minimal shape of a task and a PRD source registration; replace IDs and text with actual evidence:

```json
{"feature_id":"FEAT-001","tasks":[{"id":"T-1","title":"Implement one slice","status":"planned","requirement_ids":["R-1"]}]}
```

```json
{"id":"SRC-01","path":"sources/prd-original.html","kind":"html"}
```

The synthetic fixtures in `tests/intake_helpers.py` and `tests/test_fix_flow.py` exercise these shapes against the actual validators. Their text is test data, not a source of product intent. Unknown or unreadable content remains a gap; changing these fields to satisfy a validator is not a semantic review.

For clarification decisions introduced in 0.4.8, the opt-in `clarification` fields and application checks are documented in [clarify-workflow.md](clarify-workflow.md). Legacy decisions are not automatically migrated.

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


## Optional module and archive metadata (0.4.11)

`feature.modules` is a unique array of nonempty, trimmed module labels; absent means unclassified. `feature.archive` is optional (absent means active) with `{archived: boolean, history: [...]}`. History alternates archive and restore events. Every event has action, at (UTC timestamp), reason; archive additionally records revision, feature-relative evidence report path and evidence_sha256. It preserves the supplied historical delivery revision, not necessarily current HEAD. `feature_lifecycle.py` validates metadata shape and state/history agreement; timestamps and revision truth remain evidence checks by the Agent.

Only `feature-archive.py` changes archive metadata in normal use. Completion status stays independent; archive does not set complete, restoration does not erase old acceptance. Optional metadata does not affect the PRD semantic review digest. Generated spec.md and feature-status show archive state/module labels. See [archive rules](feature-archive.md) for record checks, manual acceptance review and shared Git behavior.


## Opt-in semantic baselines (0.5.0)

`feature.baseline` is managed by revise.py and validated by revisions.py. It contains `version`, `digest`, `initial_requirements` (historical semantic snapshot), `registered_at`, `reason`, `applied`, `cancelled`, `deliveries`. Current requirements stay in the existing top-level array. The digest covers id/title/statement/status/acceptance_criteria/assumptions, not editable workflow links or feature progress. Applied events reference immutable `revisions/CHG-*.json` and preserve their digest, resulting version/digest and confirmation snapshot digest. Delivery events bind a baseline version/digest to actual code revision and evidence report hash. Proposal source bytes, if supplied, live under sources/revisions and remain source-sharing opt-in.

No baseline field means legacy behavior; it is not an implicit version 1 or a claim of verified delivery. Pending revision, direct semantic drift and premature complete are guarded. Fields, example input, adoption limits and current/verified version distinction: [revision workflow](revision-workflow.md). Render-workspace produces revisions.md; do not edit generated history as authority.


For superseded intake aspects, optional `superseded_by` names an applied CHG record and `supersession_reason` explains why. The original target_text must match that change's before statement or indexed before acceptance criterion. Keep current non-superseded source coverage; unchanged aspects are checked normally. Applied revision JSON can be a registered document source, and must remain byte-content equivalent to its applied proposal digest. This explicit relationship does not infer whole-document precedence.
