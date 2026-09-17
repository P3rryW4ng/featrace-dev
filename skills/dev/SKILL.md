---
name: dev
description: Deliver PRD-driven software features with persistent specifications, source reconciliation, tasks, and validation. Use for dev scan/prd/api/figma/develop/check/status requests or staged feature delivery; not isolated coding questions. Android has a bundled adapter; other stacks use evidence-based generic configuration.
---

# Feature Delivery

Use the project root supplied by the user or established by the current workspace. All paths below are relative to this Skill directory, not the target project. Run scripts with explicit project paths. Never create project records inside the installed Skill.

## Commands

Claude Code: `/dev scan`, `/dev prd <file> --feature FEAT-001 [--source <file>]`, `/dev develop FEAT-001`.
Codex: `$dev scan`, `$dev prd <file> --feature FEAT-001 [--source <file>]`, `$dev develop FEAT-001`.
Accept plain `dev ...` when this skill is selected. These are agent instructions, not shell commands or a deterministic CLI. Do not promise that plain `dev` always activates the skill.

| Action | Behavior |
|---|---|
| scan | Detect profile, scan project, inspect representative code and complete baseline |
| prd <file> --feature <ID> [--source <file> ...] | Preserve original, extract atomic requirements, tasks, test plan, render and validate draft |
| api <file-or-link> --feature <ID> | Preserve new evidence, reconcile data semantics, record affected tasks/code/tests |
| figma <file-or-link> --feature <ID> | Preserve node references and available exports, reconcile visuals and behavior |
| develop <ID> | Validate development eligibility, implement slices, update records and evidence |
| check <ID> | Validate records, execute applicable project checks, report actual results and unmet conditions |
| status <ID> | Read state and summarize next action; no source or code mutation |

Use an unambiguous active feature if ID is omitted; ask only when multiple choices exist. Ask for an inaccessible source; never infer its contents. Online API/Figma retrieval requires an available authorized connector or supplied export; this package does not install connectors.

## Entry and profile selection

Read `core/references/prd-analysis.md` before analyzing a PRD or changing requirement meaning. Inventory reading gaps, preserve contextual source items, map conditions/exceptions, and record semantic review before development.

Read `core/references/workflow.md` for all feature work and `core/references/requirement-schema.md` when editing records.

Before first use in a business project or adopting Git sharing, read `core/references/git-sharing.md` and run `python3 core/scripts/setup-workflow-git.py <PROJECT>`. Preserve existing ignore policy; report conflicts and already tracked local files without silently untracking them. Never commit/push as a setup side effect.

1. Read project `.agent-workflow/config.yaml` if present. Otherwise copy `core/assets/config.yaml`; this file is agent guidance, not an executable policy engine.
2. Run `python3 core/scripts/project.py scan-prepare <PROJECT>` for a first baseline or a requested refresh; use `verify <PROJECT>` to check an existing baseline. Read the resulting profile and draft. On a fresh clone, reuse shared notes and review current evidence before publishing a local fingerprint; missing local state does not justify reinitializing feature records. Scanner output is inventory, not proof of architecture understanding.
3. Android: read `profiles/android/PROFILE.md`. All other stacks: read `profiles/generic/PROFILE.md`. In mixed repositories select the feature's actual target module and record it; don't run a root build merely because a manifest exists.
4. Read `core/references/project-baseline.md` for scan and verification. Cross-check descriptive docs against actual modules, retain rule scope/exceptions, record coverage status, and register evidence dependencies. Read representative code; fill architecture, conventions and reuse examples with file evidence before business-code changes. Review `.agent-workflow/project-baseline/quality-gates.json` against build files and CI. Keep conditional/template checks in `quality-candidates.json`; `quality-gates.json` holds only selected concrete commands. During scan, edit only `baseline-draft/baseline`; preserve unrelated reviewed scopes. Publish with `project.py scan-publish <PROJECT>` only after review; failed publication keeps the current baseline. Unchanged content creates no backup, changed content retains the latest 3 managed backups. See the baseline reference for draft recovery, pinning and retention. End scan with `project.py validate-gates` (no build execution). An empty selection is not passed.
5. Create a feature using `bash core/scripts/init-feature.sh <ID> <PRIMARY-DOCUMENT-OR-HTML> <PROJECT> [--source <ADDITIONAL-FILE> ...]`. Only one part is required; HTML can be primary. Script preserves source bytes and extension. Interpret Word/PDF through available readers before decomposing; do not pretend binary input is Markdown.
6. Register and review every supplied part, including observable HTML states and actions. Missing dynamic dependencies or inaccessible interactions remain reading gaps; conflicts between document and interaction are decisions, not silent precedence choices. Populate `spec/prd-intake.json` and requirement `source_item_ids` under the PRD analysis contract. Review the original against the spec, then record that review with `core/scripts/review-prd.py`. Empty/missing/stale intake blocks develop/check, including legacy workspaces; draft only warns about incomplete work.
7. Run `python3 core/scripts/validate-feature.py --stage draft|develop|check <PROJECT> <ID>` at the corresponding boundary. This is a structural guard, not a substitute for semantic review or quality evidence.

## Delivery

Implement independently testable slices using project conventions. After each slice update canonical JSON and run `python3 core/scripts/render-workspace.py <PROJECT> <ID>`. Use `feature-status.py` for summaries.

Before each check, select applicable commands from the candidate catalog using current change scope and project policy; honor existing authorization and record why they were selected. Do not automatically run every candidate. For checks run `python3 core/scripts/project.py check <PROJECT>` after reviewing configured commands. Record results in the feature's delivery report, tied to the tested code revision. A pass on JSON validation alone never means complete.

Legacy YAML: `migrate-workspace.py` creates an empty migration scaffold and preserves old records. The agent must faithfully reconstruct requirements/tasks/decisions/traceability and validate before development; it is not an automatic semantic converter.

## Completion

For API and Figma separately record `present`, `missing`, `unknown`, or `not_applicable` in feature.source_status. Record why a source is not applicable in feature.source_notes. Missing/unknown required evidence permits provisional work only. A feature that needs neither source can be complete if all other conditions pass. No fake API is needed for purely local computation.

Complete requires: active requirements confirmed against evidence; all tasks done; no pending conflicts; all required sources reconciled or justified as not applicable; traceability and test evidence; applicable quality gates actually passed. A manual checklist remains necessary where the validator has documented gaps. If checks cannot run, report unavailable and provisional, never success.
