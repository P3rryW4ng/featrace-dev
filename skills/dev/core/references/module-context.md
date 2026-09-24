# Scoped module knowledge and capability graph (0.5.21)

## Android Gradle candidate discovery

During Android `scan`, `scan-prepare`, and `scan-publish`, the Skill reads the root `settings.gradle(.kts)` plus discovered module `build.gradle(.kts)` files. It recognizes common literal `include`, literal `projectDir`, and configuration-to-`project(":path")` declarations. It writes:

- `modules/candidates.json`: deterministic candidate records, file hashes, file/line evidence, registered-module matches and parsing gaps;
- `modules/candidates.md`: a readable candidate list and dashed Mermaid dependency graph.

The artifact uses `status: candidate_only`; each module uses `pending_review`. A dependency target absent from static includes remains an unresolved target node with a dashed candidate edge and a line-level gap in the generated views; it is not a discovered or confirmed module. The artifact never edits `modules/index.json`, does not create dossiers, and cannot satisfy scope/develop/check gates. Review actual build configuration and source boundaries before adding accepted modules or dependencies to the formal catalog. Dynamic/composite includes, computed paths, type-safe project accessors, convention-plugin relationships, aliases, reflection, navigation and runtime services may be absent. A missing candidate therefore does not prove that no relationship exists.

If the root settings applies an external settings script, discovery records its file and line as a manual-review gap; it does not execute or parse that script. `add(..., project(...))` dependencies receive a line-level gap. Recognizable variant-specific forms such as `add("${flavor}Implementation", project(":debug"))` additionally become dashed `conditional_candidate` edges, never unconditional facts. Do not put a variant-only relation in the formal catalog's unconditional `depends_on`: graph rendering and scan publish reject that conflict when both modules map uniquely and no ordinary static declaration supports the same pair. Correct the reviewed catalog, then rerender; do not delete the source gap to bypass review. Other computed or plugin-provided declarations may still be missed, so inspect the referenced settings and affected build files before accepting module scope.

Run discovery directly only when inspecting the mechanism:

```text
python3 core/scripts/module_context.py discover <PROJECT>
```

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

Use actual existing project paths, register all applicable root rules/build dependency files, omit nonexistent examples. Module IDs are safe stable labels (index is reserved); feature.modules and module_scope assignments use these exact IDs. Roots are explicit project-relative file/directory paths, no globs or `.`. dependencies list known IDs; shared/cross-module files belong in evidence_files or a registered module. Overlapping roots are allowed but can increase review cost. On a structure/build-topology change review the catalog; don't merely acknowledge hashes. Broader dependency relationships may need registration in both callers' declarations and evidence.

Code modules and business capabilities are different axes. A red-envelope capability can have `wallet=owner` and `chat=host`; do not force it into one label or create a new build module merely because the business capability is cross-module. Supported roles are `owner`, `host`, `provider`, `consumer`, and `shared`. Each assignment records its actual responsibility and evidence references.

New workflow v3 features begin with a pending scope. After PRD analysis run the read-only suggestion helper, inspect the relevant catalog summaries/code and then ask the user to confirm only the ambiguous product ownership or scope:

```text
python3 core/scripts/feature_scope.py suggest <PROJECT> <ID>
python3 core/scripts/feature_scope.py set <PROJECT> <ID> --input <scope.json>
python3 core/scripts/feature_scope.py not-applicable <PROJECT> <ID> --reason "documentation-only change"
```

The set input contains `capability: {id, name}`, nonempty `assignments`, and an optional note. Every assignment contains `module_id`, one supported role, a concrete responsibility, and nonempty `evidence_refs`. `suggest` uses registered path matches only and never chooses a semantic owner. `set` writes `feature.modules` from the assignments and enables dossier checks. Pending scope blocks develop/check. Not-applicable is allowed only with a specific reason and no runtime module assignments.

Files: index.json is the editable project overview; index.md is generated. Each module has `<id>.json` containing body and machine review receipt, plus generated `<id>.md`. Keep one current dossier per module; use Git history, not timestamped copies. Store in project `.agent-workflow/modules`, never the installed Skill. Share after normal sensitivity review. Existing architecture/conventions/coverage notes remain useful sources; link or summarize narrowly, do not maintain competing global technical manuals.

## Select scope and inspect changes

```text
python3 core/scripts/module_context.py plan <PROJECT> --module wallet
python3 core/scripts/module_context.py plan <PROJECT> --feature FEAT-001
```

Feature form uses its registered modules. No selection/unknown module is an error, not an invitation to guess. Multiple --module values are supported. Plan expands to declared direct callers of selected modules and recursive dependencies of that set; cycles terminate. It reads only files under those roots and their registered external/global evidence, using Git's tracked/nonignored-untracked inventory. It returns scope, changed files, current digest, dossier path, reviewed commit and current/stale/unreviewed/gaps status. Code additions/deletions/working-tree edits and global evidence changes invalidate relevant receipts; unrelated commits alone do not. It does not read every source module or infer dynamic callers.

Before a new feature, read overview and relevant current dossiers, then inspect the actual insertion point and current caller/state paths. New workflow v3 workspaces require confirmed `module_scope` or a specific not-applicable reason before develop/check. Legacy workflow v2 retains the earlier rule: when a module catalog exists, set `module_context_required: true` with registered `feature.modules`, or set it to false and record a nonempty `module_context_note`. Neither path is a shortcut for an unknown module. A current receipt means recorded bytes/notes match, not that every implementation detail was understood. New requested behavior can require additional reading even with unchanged files. Populate impact.json using actual investigation and classify the feature modules; do not copy a module summary as proof of complete impact analysis.

When a dependency changes, reconsider callers' described behavior even if their own files are unchanged. Plan surfaces the stale dependency, but does not automatically prove whether other dossiers' semantic claims remain valid; update affected descriptions with evidence.

If the catalog is missing, establish it during the initial scan. If a module cannot be located, roots/topology are changing, or unknown cross-module effects appear, enlarge scope or perform the full baseline scan. Do not ask the user to guess internal code-module names when repository evidence can identify candidates. `/dev scan --module <id>` requests scoped work; plain scan retains full baseline refresh. Routine feature work can use module plan in place of repeating the full manifest walk when catalog/root evidence is valid; review shared project rules first. The existing project.py verify/check runner still has global manifest checks; this feature does not silently replace their reliability contract.

After creating or revising the catalog, and after changing confirmed feature scope, run:

```text
python3 core/scripts/module_context.py graph <PROJECT>
```

This writes generated `modules/graph.json` and `modules/graph.md`. The graph contains declared module dependencies and confirmed capability-role edges, plus explicit gaps for legacy labels without roles. When a valid Gradle candidate artifact exists, unconfirmed relationships appear as dashed `candidate` edges; recognized variant dependencies use dashed `conditional_candidate` edges. Unmatched build modules and unresolved dependency targets appear as separate pending nodes. Unknown targets keep their line-level gaps and do not become formal modules. Mermaid is a human navigation view; JSON is the deterministic generated view. Static declarations and confirmed feature records do not reveal every runtime call, reflection, dynamic route, remote flag or external service, so the graph must not be presented as exhaustive.

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

Workflow v3 uses `feature.module_scope` as the confirmed classification and mirrors its module IDs into `feature.modules`; `feature.module_context_required=true` then activates current dossier checks. Develop and check both require current dossiers for the selected scope; investigate/review before editing, then refresh affected module bodies after edits while preserving accurate unchanged facts and historical links. Legacy workflow v2 retains its explicit modules-or-reason contract and is not bulk migrated. These fields are metadata, not a product requirement change.

After accepted delivery, add the feature ID to relevant module dossiers and explain final behavior/known limits, then re-register review if notes changed. Archiving retains the same feature folder and module labels; list --archived --module finds history. Archive does not automatically interpret and merge an old PRD into module rules. Restoration preserves history; re-read current module evidence before a new edit.

Existing archive invokes current check, so adopted impact/verification/module gates can refuse stale records. Do not refresh old acceptance tokens to force an archive through. Archive promptly after delivery or reconcile current applicability/evidence honestly. Separating historical acceptance from current-worktree archive eligibility is still a limitation; no automatic historical rerun or deletion is introduced here.

## Limits

Git repository required. Ignored new files, undeclared external services, unregistered callers and root files absent from global_files remain discovery gaps. Explicit evidence can include ignored regular files, but never secrets. Symlinks and submodules are rejected for manual handling. Freshness is per module scope, not per function or semantic correctness. Role confirmation remains a product/engineering judgment; a path match is not ownership. This improves reuse and change localization; speed/accuracy improvements need real measurement. It is not an automatic call graph, automatic rule supersession or exhaustive whole-project scan.
