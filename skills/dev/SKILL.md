---
name: dev
description: Deliver PRD-driven software features with persistent specifications, source reconciliation, tasks, and validation. Use for dev session mode, help/next/revise/archive/restore/classify/list/use/scan/prd/api/figma/develop/clarify/fix/check/status requests, or continued feature-delivery messages after mode activation; not isolated coding questions. Android has a bundled adapter; other stacks use evidence-based generic configuration.
---

# Feature Delivery

Use the project root supplied by the user or established by the current workspace. All paths below are relative to this Skill directory, not the target project. Run scripts with explicit project paths. Never create project records inside the installed Skill.

## Commands

For `/dev` with no arguments, `dev off`, or continued messages after activation, read `core/references/session-mode.md` first. Empty `/dev` activates delivery mode without starting work. While active, ordinary feature-delivery text defaults to `next`, and bare recognized command words are accepted for this conversation and project.

Handle `help [command]` first, before project setup, feature selection or any workflow action. Read `core/references/command-help.md` and answer in the user's language. Help needs no project or selected feature; do not scan, run checks, create records, change selection, install anything or execute the command being explained. Return after showing help. Unknown help topics get a short correction and the command list, never an inferred execution.

Claude Code: `/dev next <description>`, `/dev scan`, `/dev prd <file> --feature FEAT-001 [--source <file>]`, `/dev develop FEAT-001`, `/dev fix FEAT-001 <problem>`.
Codex: `$dev next <description>`, `$dev scan`, `$dev prd <file> --feature FEAT-001 [--source <file>]`, `$dev develop FEAT-001`, `$dev fix FEAT-001 <problem>`.
Accept plain `dev ...` when this skill is selected. These are agent instructions, not shell commands or a deterministic CLI. Do not promise that plain `dev` always activates the skill.

| Action | Behavior |
|---|---|
| mode (no arguments) / off | Enter or leave conversational delivery mode for the current project and session |
| help [command] | Show grouped command summaries or one command's usage, example and distinctions; no project required |
| next [description] [--feature ID] | Read current state, route natural-language input to the applicable existing workflow, and perform it |
| list [--archived / --all] [--module <label>] | List active features by default; optionally include history or filter modules |
| revise [ID] <change> [--source <file> ...] | Propose confirmed requirement changes, check base version and track delivery separately |
| archive [ID] | Archive accepted complete features in place after checking delivery evidence |
| restore [ID] | Restore an archived feature to the active list, preserving delivery history |
| classify [ID] --module <label> ... | Set module labels for lookup; --clear-modules removes labels |
| use <ID> | Validate and select an existing feature for this conversation and project |
| scan [--module <label> ...] | Refresh project baseline, or investigate selected modules and registered related paths |
| prd <file> --feature <ID> [--source <file> ...] | Preserve original, extract atomic requirements, tasks, test plan, render and validate draft |
| api <file-or-link> [--feature <ID>] | Preserve new evidence, reconcile data semantics, record affected tasks/code/tests |
| figma <file-or-link> [--feature <ID>] | Preserve node references and available exports, reconcile visuals and behavior |
| develop [ID] | Validate development eligibility, implement slices, update records and evidence |
| clarify [ID] <question-or-proposal> | Record a pending decision, investigate existing behavior and impact, resolve and track application |
| fix [ID] <problem> | Register an observed mismatch, investigate cause, repair or reconcile evidence, verify and render fix history |
| check [ID] | Generate verification checklist, run mapped checks, collect remaining manual evidence and validate delivery |
| status [ID] | Read state and summarize next action; no source or code mutation |

For list/use, creation, and feature-scoped commands read `core/references/feature-selection.md`. IDs may be omitted after a successful selection in this conversation and project. Validate the target with `feature-context.py` and display project/ID/title before work; explicit IDs override only that invocation. Never infer a default in a new or uncertain context. Successful new PRD creation selects the new feature after draft validation; failed creation or an existing ID preserves the previous selection. Ask for an inaccessible source; never infer its contents. Online API/Figma retrieval requires an available authorized connector or supplied export; this package does not install connectors.

For `/dev next`, read `core/references/next-workflow.md`. Resolve the feature and inspect status first, announce the chosen route briefly, then execute the underlying existing workflow. Classify evidence by its role: a replacement/expected image is design evidence, while a screenshot of an observed failure is fix evidence. Ask only when ambiguity changes product authority or the record type. `next` does not bypass any review, impact, module, restore or verification gate and creates no separate routing record.

## Requirement revisions

Read `core/references/revision-workflow.md` for revise or any semantic edits in a feature with `feature.baseline`. Keep original PRDs, current requirements and revision proposals distinct. Later date alone is not authority; approved evidence applies only to affected rules. Controlled baselines must change through a version-checked revision. A pure code bug leaves requirement meaning unchanged. Adoption is opt-in; do not migrate old features automatically.

## Archive and history

Read `core/references/feature-archive.md` for archive/restore/classify and historical lookup. For archive, run the archive preflight before the final helper: it preserves an existing report or creates a review-required draft from current structured evidence, reports module/source/Git gaps, and never invents acceptance. Review and edit the draft before removing its marker; final archive rejects an unreviewed generated draft. Re-read archive metadata before feature work. Archived records remain readable; restore before further development, checks, fixes, clarifications or source/spec edits. Default list excludes archived features; archive is independent of completion and preserves all evidence. Use module tags to locate relevant history, then verify current code; tags are not a current-behavior index.

Before business-code edits and again before check, read `core/references/historical-regression.md`. Sync related verified-fix candidates from registered modules and code paths. Sync only discovers candidates: it never authorizes a disposition. If the user limits the action to sync/list/inspection or says not to choose, leave new candidates pending and stop. Otherwise, disposition each candidate as retest or not applicable only under the user's current instruction or an unambiguous documented policy, with evidence. Never reopen historical fixes or claim semantic completeness automatically. Superseded dispositions/results remain audit history and never satisfy the current gate.

## Entry and profile selection

For scan and scoped feature work read `core/references/module-context.md`. Establish a project module catalog at initial scan; when available, select feature modules and inspect scoped dossiers/dependencies/callers before code changes. New workflow workspaces must set `module_context_required` and either select/review modules or record a specific `module_context_note` explaining why the catalog does not apply. Refresh stale module evidence before develop and after affected code changes. `/dev scan --module <label>` uses this scoped workflow; unknown topology requires broader investigation. Dossiers are source-reviewed implementation knowledge, not acceptance or product authority.

Read `core/references/prd-analysis.md` before analyzing a PRD or changing requirement meaning. Inventory reading gaps, preserve contextual source items, map conditions/exceptions, and record semantic review before development.

Read `core/references/task-semantic-review.md` after generating tasks and before/after changing task meaning. Sync and locally review changed tasks against only their linked requirements and evidence; task progress and execution evidence do not trigger this review. Existing workspaces adopt before their first semantic task edit so the prior wording is preserved.

Read `core/references/workflow.md` for all feature work and `core/references/requirement-schema.md` when editing records.

Before first use in a business project or adopting Git sharing, read `core/references/git-sharing.md` and run `python3 core/scripts/setup-workflow-git.py <PROJECT>`. Preserve existing ignore policy; report conflicts and already tracked local files without silently untracking them. Never commit/push as a setup side effect.

1. Read project `.agent-workflow/config.yaml` if present. Otherwise copy `core/assets/config.yaml`; this file is agent guidance, not an executable policy engine.
2. For initial baseline/full refresh run `python3 core/scripts/project.py scan-prepare <PROJECT>`; `verify <PROJECT>` checks the global baseline and reports whether HEAD, manifests, registered evidence or non-workflow working-tree paths changed. Review the listed paths before choosing scoped dossier review or a full refresh; do not equate every HEAD change with a semantic baseline change. With a valid module catalog and known feature scope, use module_context.py plan and inspect affected dossiers first instead of repeating full-project baseline analysis. Root evidence/topology changes or unknown scope require broader review. On a fresh clone reuse shared notes and verify their evidence; do not reinitialize feature records. Inventory and matching hashes are not proof of semantic understanding.
3. Android: read `profiles/android/PROFILE.md`. All other stacks: read `profiles/generic/PROFILE.md`. In mixed repositories select the feature's actual target module and record it; don't run a root build merely because a manifest exists.
4. Read `core/references/project-baseline.md` for full scan and verification. Cross-check descriptive docs against modules, retain rule exceptions and register evidence. Keep global baseline edits in `baseline-draft/baseline`; module dossiers use their separate `.agent-workflow/modules` paths. Preserve unrelated reviewed scopes. Publish global baseline only after review with project.py scan-publish; unchanged content creates no backup, and a reviewed HEAD-only refresh updates only the fingerprint without backing up identical prose. Manifest, registered-evidence or baseline-content changes retain the latest 3 managed backups. Scoped module review follows module-context.md instead of republishing unrelated global notes. Review quality-gates.json against build/CI; keep unresolved candidates separate. End scan with project.py validate-gates (no build execution); empty selection is not passed.
5. Create a feature using `bash core/scripts/init-feature.sh <ID> <PRIMARY-DOCUMENT-OR-HTML> <PROJECT> [--source <ADDITIONAL-FILE> ...]`. Only one part is required; HTML can be primary. Script preserves source bytes and extension. Interpret Word/PDF through available readers before decomposing; do not pretend binary input is Markdown.
6. Register and review every supplied part, including observable HTML states and actions. Missing dynamic dependencies or inaccessible interactions remain reading gaps; conflicts between document and interaction are decisions, not silent precedence choices. Populate `spec/prd-intake.json` and requirement `source_item_ids` under the PRD analysis contract. Review the original against the spec, then record the full review with `core/scripts/review-prd.py`. If reading gaps or pending items remain, record only a partial draft review using `--stage draft` and state the gaps in the notes; this never satisfies develop/check. Empty/missing/stale intake blocks develop/check, including legacy workspaces; draft only warns about incomplete work.
7. Run `python3 core/scripts/validate-feature.py --stage draft|develop|check <PROJECT> <ID>` at the corresponding boundary. This is a structural guard, not a substitute for semantic review or quality evidence.

For `/dev api` and `/dev figma`, first preserve the accessible export or an Agent-authored evidence manifest as a regular local file, then use `python3 core/scripts/register-source.py <PROJECT> <ID> <FILE> --kind api|design`. This single operation copies immutable evidence and synchronizes intake sources with `feature.prd_paths`; do not edit those two lists separately. Links that cannot be exported must be represented by a local manifest containing the exact URL/node/version and access gaps, never invented content. Every registered part still needs reading units, mapping and a fresh review.

After adding/reconciling a source, requirement, approved decision or semantic task description, rerun the full PRD review when its digest is stale and then `validate-feature.py --stage develop` before any further business-code edit. Do this at each semantic boundary, not only during final check.

## Clarifications

Read `core/references/clarify-workflow.md` for `/dev clarify <ID> <question-or-proposal>` (Codex: `$dev clarify`) or material requirement doubts discovered in ordinary conversation while this Skill is active. Persist them in existing `decisions.json` with `record-clarification.py`, return the D-number, investigate sources and existing behavior, and distinguish a confirmed answer from its application. Reuse linked decisions from fixes; pure explanations need no new record. Honor no-writing requests; analysis alone does not authorize business-code changes. Pending choices retain existing develop/check blocking; approved but unapplied clarifications block check. Source interpretation, impact discovery and evidence truth remain Agent responsibilities.

## Fixes

Read `core/references/fix-workflow.md` for `/dev fix` or any reported effect/requirement mismatch. First run `core/scripts/record-fix.py <PROJECT> <ID> "<problem>"` to create a traceable record in the existing feature. Do not infer missing expected behavior or silently rewrite a PRD. Keep cause unclassified until evidence distinguishes requirement mapping, generated task wording and code behavior; multiple contributing causes can be recorded. Update affected canonical records, then verify the behavior with a regression test or record an explicit waiver. `fixes.json` is editable; `fixes.md` is generated. An open fix warns during develop and blocks feature check. Non-defect dispositions use evidence-backed `closed` records under the fix workflow; a duplicate points directly to its original, which remains blocking until resolved. Regression tests must cover affected requirements/tasks, or carry per-test cross-scope reasons. A completed feature with a new report becomes provisional.

## Delivery

For check and post-implementation acceptance, read `core/references/verification-workflow.md`. Generate/synchronize the verification list, review automated coverage mappings, run configured checks once through verification.py, and present remaining manual scenarios. Preserve failed/old results; never infer manual acceptance from build success. Continue the overall validation/audit below without rerunning the same unchanged checks unnecessarily.

Before business-code edits in develop/fix or following revise, read `core/references/impact-review.md`. New workspaces already set `impact_required=true`; create and review the per-feature checklist before the first edit. Investigate related mechanisms, distinguish changed/preserved/unknown behavior, and validate develop before editing. At check compare actual scope and record current regression evidence. Untouched legacy features remain compatible; no automatic whole-project impact discovery.

Implement independently testable slices using project conventions. After each slice update canonical JSON and run `python3 core/scripts/render-workspace.py <PROJECT> <ID>`. Use `feature-status.py` for summaries.

Before each check, select applicable commands from the candidate catalog using current change scope and project policy; honor existing authorization and record why they were selected. Do not automatically run every candidate. Use verification.py run to invoke the existing project.py check runner and capture results; do not run both back-to-back for the same unchanged selection. Mark `test_ids` only after checking that actual commands execute those tests; behavior-to-gate mappings additionally need assertion coverage review. Run `validate-feature.py --stage check` and `audit-delivery.py <PROJECT> <ID>` after results are collected, reporting remaining manual evidence or failures. Inspect task/decision meaning, tested code and assertions, and update the delivery report. Audit and list completion cannot prove semantic/UI correctness. Controlled requirement baselines additionally need revision-workflow delivery registration; confirmation or structural validation alone never means complete.

Legacy YAML: `migrate-workspace.py` creates an empty migration scaffold and preserves old records. The agent must faithfully reconstruct requirements/tasks/decisions/traceability and validate before development; it is not an automatic semantic converter.

## Completion

For API and Figma separately record `present`, `missing`, `unknown`, or `not_applicable` in feature.source_status. Record why a source is not applicable in feature.source_notes. Missing/unknown required evidence permits provisional work only. A feature that needs neither source can be complete if all other conditions pass. No fake API is needed for purely local computation.

Complete requires: active requirements confirmed against evidence; all tasks done; no unresolved fixes or pending conflicts; all required sources reconciled or justified as not applicable; traceability and test evidence; applicable quality gates actually passed. A manual checklist remains necessary where the validator has documented gaps. If checks cannot run, report unavailable and provisional, never success.
