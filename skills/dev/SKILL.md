---
name: dev
description: Deliver PRD-driven software features with persistent specifications, source reconciliation, tasks, and validation. Use for dev session mode, help/next/revise/archive/restore/classify/list/use/scan/prd/api/figma/develop/clarify/fix/check/status requests, or continued feature-delivery messages after mode activation; not isolated coding questions. Android has a bundled adapter; other stacks use evidence-based generic configuration.
---

# Feature Delivery

Use the user's project root or the established workspace. Paths below are relative to this Skill directory; scripts take explicit project paths. Keep project records in that project, never in the installed Skill. This is an Agent workflow, not a shell CLI. Claude Code uses `/dev`; Codex uses `$dev`. Plain `dev ...` works only when the host selects this Skill.

## Entry and routing

- `help [command]`: read `core/references/command-help.md` and answer without project setup, selection, execution or writes. Return after help.
- Empty `/dev`, `dev off`, and continued messages in delivery mode: read `core/references/session-mode.md`. Activation alone starts no work; mode lasts only for this conversation and project.
- `list`, `use`, new-feature creation and feature-scoped actions: read `core/references/feature-selection.md`. Confirm the project, feature ID and title before mutation. Never guess the selected feature in a new or uncertain context.
- Feature mutation or `next`: read `core/references/orchestration.md` and `core/references/workflow.md`. Route through Requirement, Scope, Build, Verify, Repair or Deliver. Load only the chosen stage's references and direct prerequisites. Save handoff facts in existing canonical records; no second state machine or generic handoff file. This version uses one Agent, without independent context isolation.
- `next [description] [--feature ID]`: also read `core/references/next-workflow.md`. Inspect current status, announce the route and execute its eligible steps. Progress questions stay read-only unless fresh verification is requested. A failure screenshot enters Repair; a replacement or expected visual enters Requirement. Do not bypass any review, impact, module, restore or verification gate.

| Action | Stage or reference |
|---|---|
| `scan [--module LABEL ...]` | Scope; `project-baseline.md`, `module-context.md` |
| `prd FILE --feature ID [--source FILE ...]` | Requirement, then Scope; `prd-analysis.md` |
| `api FILE-OR-LINK`, `figma FILE-OR-LINK` | Requirement evidence; `prd-analysis.md` |
| `clarify [ID] QUESTION`, `revise [ID] CHANGE` | Requirement; `clarify-workflow.md` or `revision-workflow.md` |
| `classify [ID]` | Scope; `module-context.md`; legacy labels also use `feature-archive.md` |
| `develop [ID]` | Scope → Build; `impact-review.md`, `task-semantic-review.md`, `historical-regression.md`, project profile |
| `fix [ID] PROBLEM` | Repair → Verify; `fix-workflow.md` |
| `check [ID]` | Verify → eligible Deliver; `verification-workflow.md` |
| `archive [ID]`, `restore [ID]` | History; `feature-archive.md` (archive requires delivery evidence; restore does not rerun check) |
| `list`, `use ID`, `status [ID]` | Selection/read-only; `feature-selection.md` |

Read `core/references/requirement-schema.md` when editing feature records, `core/references/git-sharing.md` before first project setup or sharing, and the Android or Generic profile for the actual target module. An inaccessible API/Figma link requires an authorized connector or supplied export; a URL alone is not source content. A new feature requires the product/work-item ID supplied by the user; do not invent one.

## Boundaries that apply across stages

- Original evidence remains unchanged. Requirements, tasks, decisions, traceability and fixes use their canonical JSON; Markdown views are generated. Newer text alone does not override an approved requirement. Missing evidence, unresolved product choices and actual failures remain visible.
- After source or requirement meaning changes, renew the PRD review. After task meaning changes, review changed tasks against only their linked requirements and evidence. Task progress alone does not trigger semantic review. Run `validate-feature.py --stage draft|develop|check` at the relevant boundary; it checks structure, not truth.
- Before business-code edits, investigate changed and preserved behavior, module scope and related historical fixes. Historical regression sync is discovery, not disposition: if the user asks to only sync, list, inspect, stop, or not choose, leave new candidates pending and stop. Do not turn a candidate into a retest or exclusion without scoped evidence and authorization.
- Implement independently testable slices, update canonical records, then render their views. Check uses actual selected commands and their results; a test ID or successful build does not prove behavior or manual UI acceptance. Preserve failed and stale evidence. Complete only when requirements, tasks, sources, fixes, decisions and current verification evidence support the delivered revision.
- Archived features must be restored before source, specification, code or acceptance mutations; `restore` itself follows the lifecycle helper. Do not commit or push as a project-setup side effect. When facts or gates are unresolved, continue independent authorized work and report the specific blocker without claiming completion.
