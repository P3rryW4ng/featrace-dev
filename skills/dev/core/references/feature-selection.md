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

`/dev prd <path> --feature <ID> [--source <path> ...]` keeps its existing syntax and requires an explicit ID for new features. Check for an existing feature directory before initialization. If present, do not initialize, overwrite, infer that this is an approved revision, or switch selection; clarify whether to continue the existing feature or create a distinct one. The initializer also refuses existing directories.

Only after initialization, PRD analysis, rendering and draft validation succeed, validate the new selection with `feature-context.py use`, then set it as current. Draft warnings/pending business decisions do not imply development eligibility. A failed or interrupted import preserves the previous selection; report partial new records and resume them explicitly without reinitializing. The standalone initializer creates files but cannot select a conversation on its own.

For develop/check/status, the optional positional ID remains compatible. api/figma accept optional `--feature <ID>` after selection. For fix/clarify prefer `--feature <ID> <description>` for an explicit override; legacy `<ID> <description>` is supported when the ID is unmistakably an identifier in command position. Do not strip a word from free-text descriptions merely because it matches a feature title or resembles an ID. If parsing is ambiguous, ask rather than write to a guessed feature. Supplying an explicit ID for any ordinary action does not update the default; only successful use or new PRD creation does.

Archive/restore/classify also accept session-selected or explicit IDs. Selection may point to an archived feature for reading; this does not authorize continued writes without restoration. A feature archived elsewhere must be detected by re-reading its metadata before each action.

revise accepts the selected feature or an explicit ID, without changing the default. Route to revision-workflow.md; a new source supplied to an existing prd ID is not an implicit approved revision.
