# Scoped module knowledge (0.5.6)

Use during scan, feature intake/develop/fix/revise investigation and delivery. Keep original feature archives unchanged. Module dossiers describe reviewed current implementation; historical requirements document what was delivered then. Neither replaces the other or overrides confirmed product intent.

## Project overview and module files

At first full project scan, inspect build declarations and root rules to establish `.agent-workflow/modules/index.json`. This is Agent-authored, not an automatically inferred dependency graph:

```json
{
  "schema_version": 1,
  "shared_stack": "Kotlin and Compose; versions/configuration evidenced by registered build files",
  "global_files": ["settings.gradle.kts", "gradle/libs.versions.toml", "AGENTS.md"],
  "modules": [
    {"id": "wallet", "summary": "Wallet setup and payment flows", "roots": ["wallet"], "depends_on": ["identity"], "evidence_files": ["app/src/WalletEntry.kt"]},
    {"id": "identity", "summary": "Shared identity state", "roots": ["identity"], "depends_on": [], "evidence_files": []}
  ]
}
```

Use actual existing project paths, register all applicable root rules/build dependency files, omit nonexistent examples. Module IDs are safe stable labels (index is reserved); feature.modules uses these exact IDs. Roots are explicit project-relative file/directory paths, no globs or `.`. dependencies list known IDs; shared/cross-module files belong in evidence_files or a registered module. Overlapping roots are allowed but can increase review cost. On a structure/build-topology change review the catalog; don't merely acknowledge hashes. Broader dependency relationships may need registration in both callers' declarations and evidence.

Files: index.json is the editable project overview; index.md is generated. Each module has `<id>.json` containing body and machine review receipt, plus generated `<id>.md`. Keep one current dossier per module; use Git history, not timestamped copies. Store in project `.agent-workflow/modules`, never the installed Skill. Share after normal sensitivity review. Existing architecture/conventions/coverage notes remain useful sources; link or summarize narrowly, do not maintain competing global technical manuals.

## Select scope and inspect changes

```text
python3 core/scripts/module_context.py plan <PROJECT> --module wallet
python3 core/scripts/module_context.py plan <PROJECT> --feature FEAT-001
```

Feature form uses its registered modules. No selection/unknown module is an error, not an invitation to guess. Multiple --module values are supported. Plan expands to declared direct callers of selected modules and recursive dependencies of that set; cycles terminate. It reads only files under those roots and their registered external/global evidence, using Git's tracked/nonignored-untracked inventory. It returns scope, changed files, current digest, dossier path, reviewed commit and current/stale/unreviewed/gaps status. Code additions/deletions/working-tree edits and global evidence changes invalidate relevant receipts; unrelated commits alone do not. It does not read every source module or infer dynamic callers.

Before a new feature, read overview and relevant current dossiers, then inspect the actual insertion point and current caller/state paths. New workflow workspaces use `workflow_version: 2`: when a module catalog exists, develop/check require an explicit module choice. Set `module_context_required: true` with registered `feature.modules`, or set it to false and record a nonempty `module_context_note` explaining why no catalog module applies. This is a scope decision, not a shortcut for an unknown module. A current receipt means recorded bytes/notes match, not that every implementation detail was understood. New requested behavior can require additional reading even with unchanged files. Populate impact.json using actual investigation and classify the feature modules; do not copy a module summary as proof of complete impact analysis.

When a dependency changes, reconsider callers' described behavior even if their own files are unchanged. Plan surfaces the stale dependency, but does not automatically prove whether other dossiers' semantic claims remain valid; update affected descriptions with evidence.

If the catalog is missing, the module cannot be located, roots/topology are changing, or unknown cross-module effects appear, enlarge scope or perform the full baseline scan. `/dev scan --module <id>` requests scoped work; plain scan retains full baseline refresh. Routine feature work can use module plan in place of repeating the full manifest walk when catalog/root evidence is valid; review shared project rules first. The existing project.py verify/check runner still has global manifest checks; this feature does not silently replace their reliability contract.

## Review dossier contents

Prepare a candidate JSON outside scanned source roots (for example in `.agent-workflow/modules/drafts/`), with:

```json
{
  "module_id": "wallet",
  "technology": [{"detail": "Compose screen with module-specific navigation convention", "evidence_files": ["wallet/build.gradle.kts"]}],
  "behaviors": [{"detail": "Current SAVE path preserves the form; cite the applicable confirmed decision when relevant", "evidence_files": ["wallet/src/Nav.kt"]}],
  "entry_points": [{"detail": "SAVE and CONTINUE enter with different stacks", "evidence_files": ["wallet/src/Nav.kt"]}],
  "state_lifecycle": [{"detail": "Consent state and form restoration ownership", "evidence_files": ["wallet/src/State.kt"]}],
  "tests": [{"detail": "Existing test location and what it actually asserts; not a claim it ran", "evidence_files": ["wallet/src/test/StateTest.kt"]}],
  "feature_ids": ["FEAT-001"],
  "gaps": []
}
```

Each section needs actual scoped file references; for an inapplicable area explain why using inspected code as evidence. Missing tests must be described honestly using implementation/build evidence, never invent test files. Gaps are explicit strings, and a dossier with gaps is not current for delivery. Narrow the module boundary to actual investigated responsibility rather than masking unrelated unknowns. feature_ids references existing active/archived history, not automatic rule precedence. In detail cite requirement/decision/fix IDs and distinguish retained, replaced or uncertain historical behavior when applicable.

After investigation, use the digest captured by plan **before reading**:

```text
python3 core/scripts/module_context.py review <PROJECT> --module wallet --input <candidate.json> --digest <captured-digest>
```

Review refuses changed evidence; it stamps current Git revision, file hashes and dossier digest, then generates views. It records Agent source review, not runtime acceptance. Return 2 means selected/caller/dependency scope still has stale/missing/gapped dossiers; review may have succeeded for the requested module. Return 1 indicates input/environment error. Plan is read-only. Concurrent writes are not supported; serialize dossier/catalog editing.

## Delivery and archive

When adopting for a feature set `feature.module_context_required=true` and assign `feature.modules`. Develop and check both require current dossiers for the selected scope; investigate/review before editing, then refresh affected module bodies after edits while preserving accurate unchanged facts and historical links. New workflow workspaces with a catalog cannot silently omit this choice. No automatic baseline migration applies to old untouched features. These fields are metadata, not a product requirement change.

After accepted delivery, add the feature ID to relevant module dossiers and explain final behavior/known limits, then re-register review if notes changed. Archiving retains the same feature folder and module labels; list --archived --module finds history. Archive does not automatically interpret and merge an old PRD into module rules. Restoration preserves history; re-read current module evidence before a new edit.

Existing archive invokes current check, so adopted impact/verification/module gates can refuse stale records. Do not refresh old acceptance tokens to force an archive through. Archive promptly after delivery or reconcile current applicability/evidence honestly. Separating historical acceptance from current-worktree archive eligibility is still a limitation; no automatic historical rerun or deletion is introduced here.

## Limits

Git repository required. Ignored new files, undeclared external services, unregistered callers and root files absent from global_files remain discovery gaps. Explicit evidence can include ignored regular files, but never secrets. Symlinks and submodules are rejected for manual handling. Freshness is per module scope, not per function or semantic correctness. This improves reuse and change localization; speed/accuracy improvements need real measurement. It is not an automatic call graph, automatic rule supersession or exhaustive whole-project scan.
