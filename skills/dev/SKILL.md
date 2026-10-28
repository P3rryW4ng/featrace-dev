---
name: dev
description: Implement and verify features, UI refinements and bug fixes in existing projects, with code-grounded impact analysis, targeted checks and resumable current tasks. Use for /dev delivery sessions and authorized development; not isolated coding questions or historical-record migration.
---

# FeatraceDev

Use the user's project/worktree; script paths are relative to this installation. Claude invokes `/dev`; Codex invokes `$dev`. This package uses the current-task workflow; read the installed marker for the actual version and source identity.

## Session and progress

An empty invocation activates conversational delivery mode for this project only and starts no work. While active, prefix replies `FeatraceDev ON · 项目：<actual project>` (localize as needed). `dev off` ends the mode without changing files; show OFF once. A changed project/new conversation does not inherit activation. Natural-language development instructions are tasks, not a reason to demand internal commands.

Let the host own progress presentation. For multi-step work or an explicit progress-list request, inspect the tools actually exposed in this session. Use an available tool documented to create/update a user-visible task list or progress plan; a private reasoning plan or `.featrace` task record does not create host UI. Follow its actual schema rather than assuming tool names from another host. After identifying the real work items, initialize the visible list before substantive implementation or long-running checks; an empty activation or simple one-step reply needs no list. Keep discovery itself visible if it becomes extended work.

Use the returned item IDs/states or documented plan operations to update actual starts, completions and blockers. A blocked or failed item is not completed; use supported host states and explain the blocker briefly when needed. When scope changes, reconcile the existing list instead of making a parallel one. After context loss, load the selected task status/details and live applicable rules, then query/reconcile the host list when supported; if it cannot be recovered, reconstruct only from verified current work and do not invent prior ticks.

Check each display-tool result. If the relevant tool is absent, say so once; if a call fails, distinguish failure from absence, correct a concrete schema mistake when possible, and avoid repeated blind retries. Continue authorized work with ordinary concise progress prose while display is unavailable; a display failure alone does not block delivery. Tool acknowledgment proves the call was accepted, not that the user saw a particular UI. Do not print a parallel checklist, draw checkbox/status glyphs or loading indicators, impose a fixed stage template, install/invent tools, alter host settings, or create another progress registry.

## One current-task path

For authorized development, read `core/references/task-workflow.md`. Investigate real code/configuration/tests and product intent, choose checks from causal impact, implement, run only necessary missing/changed checks, assess their actual sufficiency, and close when eligible. A UI-only refinement does not require reaccepting the whole parent PRD. Shared rendering expands rendering callers; logic tests need a causal path. Unknown effects need investigation, not an automatic maximal suite. Keep unknowns local to affected claims/checks; unrelated branch changes are context, not an automatic task-wide reacceptance trigger.

When Figma is a design source, read `core/references/figma-design.md` only for that task. Use the host's actual tools and prerequisites, selected nodes/reference images, project components and scoped visual comparison; do not load the entire design file or create a second design ledger. Missing tools/metadata are specific source gaps, and remote design freshness is not automatically certified by the task kernel.

Before the first affected project operation, read `core/references/project-compatibility.md`. Reuse applicable same-scope authorization and current project policy. Ask only for a concrete unresolved decision, required credential or actual host restriction. Selecting this Skill does not grant unrelated account, payment, production, publication or configuration permissions.

The old feature ledger, schema preparation, historical carry/replay, module dossiers and parallel-worker contracts are **retired from this package**. Do not call their old commands or migrate/rewrite/delete `.agent-workflow` data. An explicitly requested continuation of an old record needs its pinned old installation or an explicit new scoped task decision; a new ID cannot erase an unresolved failure. Report that boundary once, rather than silently switching routes.

Use actual source contents, connectors/exports when needed, and code references. A hash, URL, category or successful build does not establish business correctness. Preserve unrecoverable intent, important constraints and unresolved issues in tests, adjacent comments or the project's existing concise records; no permanent per-feature archive is required.

For authorized development, commit each completed coherent subtask locally after its necessary scoped checks and selected-output privacy review; do not wait for final feature acceptance or closure. Stage only that subtask’s changes, including its related tests, and report the commit ID. Reuse valid checks instead of rerunning them merely because HEAD changes. Apply actual user/project commit restrictions and resolve only a genuine outstanding conflict; reuse existing same-scope permission without asking at every subtask. A subtask commit is not a feature-complete claim and does not authorize push, history rewriting or inclusion of unrelated work. See the subtask commit guidance in `core/references/task-workflow.md`.

## Execution and delivery boundaries

For Android, load `profiles/android/PROFILE.md` only when applicable. Separate **behavioral impact** from **execution inputs**: broad compiler inputs do not imply broad business reacceptance. Record actual toolchain/dependency/environment identity, installed artifact and device separately. Never claim complete dynamic dependency discovery or universal cache safety.

Status, list, storage inventory and code lookup are read-only and never rerun tests. Per-check results are reusable only with the same declared inputs/tool/environment/execution protocol and intact output. Select explicit supporting fact IDs and declare justified proof requirements; the changed/unaffected label does not decide the evidence method. Supplemental facts do not replace the original sources. Mutable remote/device checks require nonreusable, time-bounded results. Correct a failure through targeted facts, not relabeling or deleting selection. Unavailable observations cannot erase unresolved runtime failures. Static analysis can support sufficient structural or no-influence proof; it cannot substitute for actual new rendering, device/live-state observations or clear an observed runtime failure. A runtime pass is a fact, not an automatic repair. For actual failures, use the explicit condition-specific failure resolution/clarification/reopen path; approved whole-promise delivery exclusions use defer with surviving handoff and remain unfulfilled, never supported. See the failure-disposition guidance in task-workflow.

Before sharing selected output or committing additions, read `core/references/output-privacy.md`; use exact files, not a whole-history scan. Temporary work belongs in the authorized task's ignored local area; read-only review permits no arbitrary writes. Do not print logs or secrets merely to inspect them. Worker/reviewer write scope is explicit and host-enforced, not inferred from installed specialists.

Project policy governs seven-calendar-day cleanup on later task starts/closures or explicit maintenance. Delete only eligible runner-owned local data; unresolved limitations require a surviving handoff. No personal scheduler, business-original deletion or Git-history rewrite is implied. Commit, push, PR and installation follow actual user scope. Report implemented behavior, validation limits and release/install identity separately.

When an error is discovered in a retained completed current-task record, use the bounded `correct` path in `core/references/task-workflow.md` with real authorization and affected claims. Preserve the original receipt/facts and reopen only necessary assessment; do not hand-edit frozen records, hide the error with a new ID or run a whole suite before confirming the correction route. This source supports only new contract6 tasks. Use the appropriate pinned tool for formats1/2/3/4/5; no automatic migration or predecessor hash bridge. Expired/compacted originals are not reconstructed automatically.


For an explicitly stopped unfinished task, use the non-delivery `retire` route in `core/references/task-workflow.md`. Preserve unresolved issues/code disposition in a necessary surviving issue location; do not fake completion or delete code to meet retention limits. Retired tasks cannot be silently resumed or have old evidence re-signed.
