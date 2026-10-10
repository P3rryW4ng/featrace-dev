# Feature selection (0.4.10)

`list`, `use` and omitted IDs are Agent commands. The helper is read-only: it validates records and returns JSON, never stores a shared pointer or changes a Git branch.

## Session scope and resolution

Keep a mapping of canonical project root → selected feature ID in this conversation only. Preserve it in a conversation handoff/compaction summary when available; if lost, ask the user to select again. Never inherit another conversation's selection, a repository-wide pointer, modification times or a sole feature as an implicit default. This is an Agent context contract, not host-enforced session persistence.

Before feature-scoped work read the selected record again:

```sh
python3 core/scripts/feature-context.py resolve <PROJECT> --current <ID> --current-project <SELECTED-PROJECT>
# Explicit ID affects this invocation only:
python3 core/scripts/feature-context.py resolve <PROJECT> --feature <ID>
```

Display project, ID and title before work. On missing, malformed, mismatched or out-of-project records stop dependent actions; list available features without silently choosing another. Helpers downstream still receive explicit PROJECT and ID. scan and list need no selection. status remains read-only and does not select implicitly.

## List and switch

- `/dev list`: run `feature-context.py list <PROJECT>`, show active IDs/titles/recorded states/module labels and any unreadable entries (history filters follow `feature-archive.md`). Mark current only from this session's mapping. An empty list suggests creating a PRD; no files are created.
- `/dev use <ID>`: run `feature-context.py use <PROJECT> --feature <ID>`. If successful, summarize the previous selection's unfinished work from its records (say unavailable if unreadable), then update only this session's mapping and show the new selection, recorded progress and next action using `feature-status.py` and its records. Failed selection preserves the old mapping. Selection itself is not evidence of development eligibility or completion. No code, source, feature status, staging, commits or branches are changed.

## Creation and explicit arguments

`/dev prd <path> --feature <ID> [--source <path> ...]` keeps its existing syntax and requires the product/work-item ID supplied by the user. Never generate an ID from the title, date or repository state. If absent, ask for it before initialization. Workflow-local `R-*`, `T-*`, `D-*` and `FIX-*` identifiers do not replace the product ID; preserve a separately supplied product subtask reference in the task record rather than changing the feature identity. Check for an existing feature directory before initialization. If present, do not initialize, overwrite, infer that this is an approved revision, or switch selection; clarify whether to continue the existing feature or create a distinct one. The initializer also refuses existing directories.

An independent modification of an existing function or a standalone defect can instead use `lightweight-change.md`: the user provides the same product ID and a short original description, without preparing a formal PRD file or naming internal modules. Its helper creates an ordinary draft with a preserved source; it does not select a feature or confirm expected behavior. Do not apply the PRD-file readiness requirement to this route. Conversely, do not silently attach an unrelated report to whichever feature happens to be selected. If an ID already exists, investigate whether to continue that record or obtain a distinct product ID; never overwrite it. After successful intake/review/draft validation, selection and Scope follow the same rules as `prd`.

When the user clearly wants a **new PRD-backed** feature, accept a natural-language request as well as the exact command. Show one compact readiness line before creation: `新需求准备 · 编号：<ID/待提供> · PRD：<accessible source/待提供> · 模块：待调查`. The ID and an accessible PRD document/HTML source are the only user-supplied creation prerequisites for this route; the project root must also be known. If either is missing, ask for only the missing item(s) in one reply and stop before initialization, source registration or feature selection. A link that cannot be read is a source gap, not a completed PRD. Do not request API/Figma when irrelevant, and do not require the user to name internal code modules. When the ID and PRD are already available, proceed with the existing `prd` workflow instead of requesting confirmation or telling the user to retype a command. An incomplete `prd` command follows this same rule rather than showing only syntax. Do not mistake a request to continue or revise an existing feature for a new-feature request.

Only after initialization, PRD analysis, rendering and draft validation succeed, validate the new selection with `feature-context.py use`, then set it as current. Draft warnings/pending business decisions do not imply development eligibility. A failed or interrupted import preserves the previous selection; report partial new records and resume them explicitly without reinitializing. The standalone initializer creates files but cannot select a conversation on its own.

After a successful draft, continue the existing Scope route: run `feature_scope.py suggest`, inspect relevant module catalog entries, insertion points, callers and code evidence, then display `模块：<evidence-backed roles / 待调查 / 待确认的问题>` in the same short readiness summary. One capability may span several code modules; do not force a single label or invent a new build module. Record supported unambiguous technical assignments through the existing scope workflow; ask the user only when product ownership or scope remains genuinely ambiguous, with the candidate roles and evidence. If the map is missing or a path is outside it, investigate or build the needed map before classifying; do not transfer that internal search to the user. Scope may remain pending in a saved draft, but new-workflow develop/check must stay blocked until it is confirmed or specifically not applicable. This summary is a reply, not a new canonical checklist file or second gate.

For develop/check/status, the optional positional ID remains compatible. api/figma and next accept optional `--feature <ID>` after selection; next treats all other text as a natural-language description, never as a positional ID. For fix/clarify prefer `--feature <ID> <description>` for an explicit override; legacy `<ID> <description>` is supported when the ID is unmistakably an identifier in command position. Do not strip a word from free-text descriptions merely because it matches a feature title or resembles an ID. If parsing is ambiguous, ask rather than write to a guessed feature. Supplying an explicit ID for any ordinary action does not update the default; only successful use or new PRD creation does.

Archive/restore/classify also accept session-selected or explicit IDs. Selection may point to an archived feature for reading; this does not authorize continued writes without restoration. A feature archived elsewhere must be detected by re-reading its metadata before each action.

revise accepts the selected feature or an explicit ID, without changing the default. Route to revision-workflow.md; a new source supplied to an existing prd ID is not an implicit approved revision.
