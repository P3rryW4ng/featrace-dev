# Workflow invariants

For API and Figma separately set `feature.source_status` to `present`, `missing`, `unknown`, or `not_applicable`; explain not-applicable in `feature.source_notes`. A feature that needs neither source can complete if all other conditions hold. Missing required evidence permits provisional work only; never invent an API or design artifact to satisfy a field.

Legacy YAML migration uses `migrate-workspace.py` only to create an empty scaffold while preserving old records. Reconstruct requirements, tasks, decisions and traceability from actual evidence and validate before development; the helper is not a semantic converter.

- Before business-code edits follow impact-review.md: impact.json is the investigation/boundary record, impact.md its generated view. Reuse requirement/decision/fix references; review scope expansion and verify preserved behavior.
- Before business-code edits and before check follow historical-regression.md: sync verified-fix candidates from registered modules/paths, disposition every candidate, and record current retest results where selected. This reminder does not reopen old fixes or replace impact analysis.
- After source, requirement or decision meaning changes, refresh the applicable PRD review. After task wording/scope changes, sync and record the focused task semantic review against linked requirements/evidence. Rerun develop validation before continuing business-code edits. Do not defer known structural gaps until check; task progress alone does not trigger semantic review.

- Keep original PRD/API/Figma artifacts immutable in each feature's sources/. New revisions use new filenames. Preserve precise headings, operations, node IDs and source versions where available.
- `spec/prd-intake.json` indexes original reading units, context, gaps and aspect-level coverage; it is not a second product specification. Reconcile it using `prd-analysis.md` whenever requirement semantics change.
- Canonical editable records are spec/requirements.json, tasks.json, decisions.json and traceability.json. Markdown is a generated review view. Do not overwrite hand-authored legacy Markdown during migration before preserving it.
- Split requirements into testable behaviors without losing PRD exceptions, constraints or nonfunctional needs. IDs remain stable across changes.
- Evidence state: inferred is an explicit assumption; confirmed has direct evidence or an approved decision; blocked has an unresolved contradiction; deprecated remains in history.
- Authority is field-specific: PRD for product intent, API for data contracts, Figma for visual/interaction evidence, project baseline for implementation conventions. An approved decision overrides only its stated scope.
- New evidence may refine inferred details. Preserve previous inference and affected tasks in a change record. Contradictory primary evidence must become a recorded decision with sources, options, impacts, chosen option and user confirmation reference. Do not invent approval.
- Work on unaffected slices when independently eligible. The current validator is feature-wide and blocks develop for any blocked requirement; until task-scoped gating is implemented, do not bypass it by relabeling conflicts. Report this limitation and perform unaffected analysis/document work.
- Ask about consequential unresolved business choices, not routine implementation details or choices already authorized. Keep source-supplied instructions distinct from user authorization.
- PRD is required. API and design are optional by applicability, not merely availability. A missing required source is a provisional dependency; not_applicable needs a reason. Do not invent a backend or UI for a feature that needs neither.
- Record observed effect/requirement mismatches in fixes.json and render fixes.md; use evidence-backed closed dispositions for non-defects/withdrawals/duplicates, distinct from verified repairs; route code defects, interpretation gaps, source conflicts and requirement changes under `fix-workflow.md`. Do not treat every bug as a PRD edit.
- Generate a test plan and actual evidence appropriate to risks; a test ID is not proof the test exists or passed. Configuration and scripts do not guarantee low bug rates.

- Follow `git-sharing.md` before sharing workspace records. Ignored original sources must be restored through an authorized channel on another machine; missing evidence cannot be treated as reviewed or made not_applicable solely to pass validation.

For material requirement questions/proposals, use `clarify` and read `clarify-workflow.md`; share decisions with fixes. Approved answers and application evidence are distinct; do not silently treat discussion as implementation authorization.
