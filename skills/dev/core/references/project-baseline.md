# Project baseline

Since 0.5.4, module-context.md defines scoped dossier review. Plain scan still uses this full-baseline contract; scan --module and known-scope feature investigation can reuse the module catalog instead of repeating full semantic review. The global snapshot/check behavior below is unchanged. Module receipts are per-scope content checks, not a replacement for quality-report identity.

## Scan contract

`scan` is also project setup: read `.agent-workflow/config.yaml` when present, otherwise copy `core/assets/config.yaml` as Agent guidance. Read the Android or Generic profile for the actual target; in mixed repositories choose the feature's module rather than assuming a root build applies. On a fresh clone reuse shared notes and verify their evidence instead of reinitializing feature records.

`project.py scan-prepare <PROJECT>` prepares an isolated baseline draft, inventories build manifests and chooses android or generic. For Android, it also refreshes `.agent-workflow/modules/candidates.json` and `.md` from supported static Gradle declarations. These are review inputs outside the baseline draft: they do not modify the formal module catalog or certify module semantics. Edit the printed `baseline-draft/baseline` directory, never the current baseline during scan review. Before declaring the scan ready, the Agent must:

1. Cross-check module names and paths against actual build configuration. Distinguish normative rules (how code should be written) from descriptive documentation (which may be stale). Record discrepancies rather than silently treating old docs as observed facts.
2. Inspect representative implementations and record exact paths. An existing empty DI module is a declaration example, not evidence of a binding/provider pattern. Label unexecuted examples as source-reviewed, not runtime-verified.
3. Preserve scope and exceptions when summarizing rules. Link to authoritative sections without flattening module-specific overrides into universal rules.
4. Update coverage.md: actual module/area, reviewed scope, evidence paths, status reviewed / inventory_only / pending, and remaining gaps. Reviewed means only the stated scope, never the whole module by implication. Include included builds/external module lists or explicitly mark them pending.
5. Register the actual rule documents, custom build scripts, locks and sampled code in evidence-files.json: {"files":["docs/coding.md","tools/flavors.gradle","app/src/Example.kt"]}. Paths must be project-relative regular files, not directories or external links. Never include secrets or generated dependency trees.
6. After reviewing/updating draft notes and evidence registrations, run `project.py scan-publish <PROJECT>`, then verify. Publish checks required files and quality configuration, refreshes the fingerprint and replaces the baseline as a directory. It does not certify semantic accuracy or complete coverage. Investigate missing evidence and record gaps before publishing.
7. Run `project.py validate-gates <PROJECT>` before completing scan. This validates configuration only; do not run project builds as part of scan. Report whether execution selection is empty.

## Quality candidates versus selected commands

quality-candidates.json is an Agent-readable catalog, not executed by scripts. Put conditional checks, templates, selection rationale, policy and prerequisites there. Example:

```json
{"candidates":[{"id":"scoped-tests","command_template":["./gradlew","test","--tests","<pattern>"],"when":"Relevant tests changed; resolve test pattern and project authorization first"}]}
```

quality-gates.json contains only the current explicitly selected, applicable commands, all treated as required for that run. Agent must review project policy and existing user authorization before selection; do not ask again where authorization already exists. Re-evaluate selection on each check; never reuse a stale selection just because it was selected previously. Avoid selecting a composite preflight alongside the same individual checks.

```json
{"selection_reason":"Unit tests for current change; authorized by user request","gates":[{"name":"unit","command":["python3","-m","unittest","discover"],"cwd":".","timeout_seconds":600}]}
```

Allowed gate fields: name (unique), command (argument array), cwd (existing project-relative directory), timeout_seconds, purpose, source, selection_reason, test_ids (optional array of distinct declared test IDs actually executed by that command). Unsupported fields, including when/enabled/required, are errors, not silently ignored. No shell evaluation or environment-variable expansion; unresolved angle-bracket, double-brace or ${...} templates are rejected. Supply resolved literal arguments.

`test_ids` is metadata supplied by the Agent after checking the command selector; the runner cannot prove the assertion matches the tests the tool actually executed. The quality report records the selected IDs with each result. `audit-delivery.py <PROJECT> <FEATURE-ID>` is read-only and compares passed selections and current project snapshot against verified fixes. A later Git commit containing only `.agent-workflow/**` records preserves the earlier quality result because it does not change the tested project tree; any tracked change outside that directory still makes the report stale. The historical tested HEAD remains recorded and is not rewritten. If a check changes a tracked manifest, Git HEAD or registered evidence while running, the runner reports PROJECT_CHANGED_DURING_CHECK and does not pass. Unregistered source edits remain outside this snapshot.

Empty gates is valid configuration awaiting selection; validate-gates exits 0 with SELECTION_REQUIRED, but check exits 2 and never reports passed. Validate-gates cannot prove that a build task exists or that execution will succeed. Project policy and applicability are Agent responsibilities, not a machine authorization mechanism.

## Fingerprint and limits

Fingerprint v2 covers Git HEAD, manifest names/hashes, root AGENTS.md and CLAUDE.md, plus registered evidence paths/hashes (missing files recorded as null). Changing the registered path set also invalidates it. v1 becomes stale and requires reviewed refresh. Missing registered files must be investigated and noted before claiming a usable baseline.

`verify` reports separate reasons and paths for HEAD, manifests and registered evidence. It also inspects staged, unstaged and untracked non-ignored paths outside `.agent-workflow/**`; these working-tree paths require review even when the fingerprint itself matches. Paths are evidence for choosing local module review or full refresh, not automatic semantic classification. Output is capped at 50 paths per category and reports the remaining count. A commit containing only `.agent-workflow/**` records may advance HEAD without invalidating the implementation baseline.

This remains a full manifest walk plus Git path diagnostics, not semantic incremental analysis. The working-tree check exposes unregistered changed paths but does not interpret their impact, and ignored files remain outside discovery unless explicitly registered. An unrelated non-workflow commit still requires path review because removing HEAD protection would miss committed unregistered source changes. No claim of complete architecture understanding or complete source coverage follows from BASELINE_VALID.

## Baseline storage and recovery (0.4.2)

- Current: `.agent-workflow/project-baseline/`, one fixed directory. Prepare copies the entire current baseline; update relevant module sections and preserve other scopes and pending gaps.
- Draft: `.agent-workflow/baseline-draft/baseline/`, at most one. An unfinished draft blocks another scan. Resume it or explicitly run `scan-discard <PROJECT>` to discard only that draft. Failed validation leaves both draft and current baseline available.
- Publish refuses if the current baseline or tracked snapshot changed since prepare. Discard/reprepare and re-review against current files rather than overwriting concurrent changes. Newly registered evidence and unregistered source changes still need Agent review; this is not a complete source freeze.
- Backups: `.agent-workflow/baseline-backups/managed-v1/<UTC>/baseline/`. Only changed baseline content creates a full prior snapshot; unchanged scans preserve current file mtimes and create no backup. After explicit scan review, a candidate whose only fingerprint difference is Git HEAD refreshes that fingerprint without backing up identical baseline prose. Manifest, registered-evidence, inventory or reviewed-note changes still create a backup. No per-scan timestamp is added to current files. Content comparison is byte-based; avoid rewriting prose solely to change dates.
- Default retention: latest 3 unpinned managed snapshots. `scan-publish <PROJECT> --keep 2` overrides retention for that publication (1–100). Add an empty `PINNED` file in a snapshot directory to exclude it from cleanup; pinned copies are additional to the limit. Manual/legacy backups, feature sources, PRDs, tasks, decisions and installer backups are outside this cleanup.
- Low-level `scan <PROJECT>` remains a compatibility inventory operation with the same backup/validation protection. It preserves prose and does not certify it. Agent `/dev scan` must use prepare → review draft → publish, so analysis edits are included in the transaction and old notes are backed up before replacement.
- Publication uses a writer lock, whole-directory rename and exception rollback. It is not a filesystem-wide atomic transaction: there is a short rename gap. A process killed in that gap leaves `.baseline-previous`; the next scan operation restores it before proceeding. Do not delete that recovery directory manually. Abrupt termination may leave `.baseline-stage-*` scratch directories or incomplete backups; these are not auto-deleted as completed history. This is not a power-loss durability guarantee.
- Machine checks cover required nonempty files, registered path constraints and selected-command structure. Coverage semantics, rule accuracy and module completeness remain Agent responsibilities.

## Sharing and fresh clones

Follow [Git sharing](git-sharing.md) for selective tracking and local-state ignores. A missing fingerprint on a clone requires evidence review and draft publication while retaining valid shared notes. Never commit the HEAD-dependent fingerprint as a refresh loop.
