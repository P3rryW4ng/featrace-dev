# Archive preflight, lifecycle and module classification (0.5.10)

Archive is a visibility/lifecycle marker in `spec/requirements.json`, independent of `feature.status`. It preserves directories, IDs, sources, fixes, decisions and delivery evidence. No compression, deletion or automatic upload. Since 0.5.4, module-context.md separately defines reviewed current module dossiers; archive itself does not merge historical requirements into them.

## Agent commands

- `/dev list`: active (nonarchived) features only, including completed but unarchived ones.
- `/dev list --archived` / `--all`: historical only / both. Map to helper `--scope archived|all`.
- `/dev list --module <label>`: exact module label filter, combinable with either scope. Use `feature-context.py list <PROJECT> --scope active|archived|all --module <label>`; inspect metadata only, not the entire project's source tree. Invalid metadata entries remain visible as errors even under a filter.
- `/dev classify [ID] --module <label> [--module <label> ...]`: set the whole module list. Reuse existing project labels; a feature can belong to multiple modules. `/dev classify [ID] --clear-modules` clears labels. Label corrections on archived features are allowed. Labels describe grouping, not authoritative current behavior or proven code coverage.
- `/dev archive [ID]`: inspect completion and delivery evidence, then archive using the helper below.
- `/dev restore [ID]`: restore visibility before further feature work, preserving all historical delivery conclusions. Restoration itself does not reset product status; new fixes/clarifications retain their existing complete→provisional behavior.

Resolve optional IDs with the session rules and show project/ID/title. Neither archive, restore nor classify changes the current selection or Git branch. `use` and `status` can read an archived feature; clearly display archived state. When a previously selected feature has been archived in another session, re-reading metadata detects it before further work. For develop/check or source/requirement/task edits, restore first. The user asking to fix or clarify an archived feature authorizes restoring it for that work: state this and record the reason, then register the problem; do not silently leave it hidden. Read-only historical questions do not require restoration.

## Archive boundary

Since 0.5.5 the helper prints GIT_RECORD_STATUS after metadata changes (also on idempotent archive/restore). It lists candidate shared feature records and registered module files that are untracked, uncommitted or ignored by policy. This is not a commit manifest or sensitivity approval. Originals/raw evidence are excluded from default candidates. Missing Git/upstream is reported as unavailable/unknown, not saved or uploaded. Local ahead/behind counts do not verify remote freshness; no fetch occurs.

After rendering views, inspect final Git status again. Tell the user separately: archive state, uncommitted shared records, and known local tracking state. Recommend committing reviewed records with the corresponding code branch; commit/push only when authorized. Never claim archived means saved to Git, silently stage everything, force-add ignored files, or switch/stash their working tree. Untracked/ignored files can follow branch switches; tracked dirty files also require deliberate handling. This check informs rather than blocks archive, because the archive metadata change itself needs a subsequent commit.

Latest integration: adopted impact, verification-list and module-context checks also run through the structural check below. Stale current-worktree evidence can block archive even when an older report describes accepted delivery. Do not manufacture new evidence to bypass this. See module-context.md for module dossier updates and this historical/current eligibility limitation.

Before archiving, verify that the feature is complete, required decisions and fixes are resolved, and actual delivery has been accepted on the recorded code revision. Start every `/dev archive` with the deterministic preflight below. It runs structural validation and read-only delivery audit, reports current Git disposition, module candidates/path roots, impact presence, and each registered source's tracked/ignored/untracked/missing state. It never stages, uploads, builds, runs device tests, changes modules, or marks acceptance.

If the evidence report is missing or empty, preflight creates `delivery-report.md` from existing requirements, tasks, decisions, traceability tests, fixes and quality results. The generated report carries `ARCHIVE_REPORT_DRAFT_REVIEW_REQUIRED`. Read every cited record, correct misleading gate coverage, add only supported limitations/conclusions and the accepted revision, then remove the marker and change the draft status. Final archive rejects the marker. A nonempty existing report is never overwritten; preflight still returns diagnostics for review.

Read the delivery report and its referenced results: test/gate and manual evidence, applicability, known limitations. Missing evidence or open cleanup blocks archive; do not set complete merely to make archive succeed. Resolve useful module labels before archive when catalog/path evidence supports them; suggestions are not automatic classification. Decide source sharing explicitly and never force-add ignored evidence. An old accepted revision need not equal today's project HEAD: later unrelated deliveries do not invalidate the historical acceptance. Do not rerun historical builds automatically just to archive.

```sh
python3 core/scripts/archive-preflight.py <PROJECT> <ID> --revision <ACCEPTED-REVISION> --evidence delivery-report.md
# Agent reviews/edits the report and removes the draft marker only after evidence review.
python3 core/scripts/feature-archive.py archive <PROJECT> <ID> --revision <ACCEPTED-REVISION> --reason <REASON> --evidence delivery-report.md
python3 core/scripts/feature-archive.py restore <PROJECT> <ID> --reason <REASON>
python3 core/scripts/feature-archive.py classify <PROJECT> <ID> --module wallet --module identity
```

The final archive helper requires complete, confirmed active requirements, all tasks done, resolved source applicability, passing structural check (including decisions/fixes), and a nonempty reviewed local delivery report without the generated-draft marker. It records the supplied accepted revision and report SHA-256. These checks cannot prove that report text is truthful, that a named revision was installed, or that a build actually passed; the Agent must inspect the evidence. Do not invent acceptance or revision information. Original sources required by check must be restored from their authorized location if missing.

After a successful metadata change run `render-workspace.py <PROJECT> <ID>` to refresh generated views; a rendering failure does not undo metadata, so report it and retry rendering without reinitialization. Archive/restore are idempotent and append transition history only when state changes. The helper replaces only requirements.json after a change check; it is not a global transaction/lock across all feature records. Avoid concurrent writers on one feature and resolve conflicting edits before retrying.

Metadata is shared with the existing canonical JSON under the project's Git policy; session selection stays private to the conversation. Never delete historical decisions, regressions, source evidence or reports to reduce disk usage. Existing scan backup retention remains separate. For a genuinely new requirement use a new feature ID and reference relevant historical IDs/decisions in its sources and analysis; don't claim all archived rules still apply. Module tags help locate prior work but related current code, callers and tests must still be inspected. Version authority, supersession and automatic change propagation remain phase two.
