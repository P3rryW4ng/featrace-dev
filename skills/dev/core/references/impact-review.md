# Local change impact (0.5.6)

Read before business-code edits through develop/fix or implementation following revise. No new user command. Clarify analysis may draft a checklist but does not authorize code changes.

## Before editing

Also follow [historical-regression.md](historical-regression.md). Impact review explains the current change boundary; historical regression review uses that boundary plus module/traceability paths to remind the Agent of verified repairs that may need protection.

New workspaces created since 0.5.6 set `feature.impact_required: true`; 0.5.15 creates workflow v3 records with the same impact requirement plus module-scope confirmation. Create feature-local `impact.json` before the first business-code edit and keep the marker once adopted. Existing untouched features remain compatible; absence warns rather than retroactively blocking historical deliveries. Continuing code work in an older workspace must adopt it, including repairs to completed features (set provisional). A caller can still bypass the workflow by editing code outside the Skill, but the normal new-feature path no longer relies on the Agent remembering to set the marker.

Inspect relevant implementation and callers, shared state, navigation, lifecycle and legacy behavior. Expand investigation when a dependency appears. Existing code shows current behavior, not automatic product authority: compare PRD and approved decisions. Record business unknowns through clarify; reuse D/FIX/CHG references in evidence/basis. Unresolved mechanisms or behaviors block develop/check; draft permits investigation.

Use one current checklist per feature with Git history. Preserve prior acceptance in the delivery report before updating for a new fix/revision. Keep the original base commit for the current delivery cycle; never advance it to hide an unexpected diff.

## Record contract

Example shape; replace findings with actual investigation:

```json
{
  "schema_version": 1,
  "feature_id": "FEAT-001",
  "base_revision": "<full commit hash before this change>",
  "inspected_paths": ["src/navigation.kt", "src/state.kt"],
  "allowed_paths": ["src/navigation.kt", "tests/navigation.kt"],
  "excluded_changes": {},
  "mechanisms": {
    "entry_points": {"status": "reviewed", "evidence": "src/navigation.kt: SAVE and CONTINUE entry points"},
    "callers": {"status": "reviewed", "evidence": "src/navigation.kt: inspected both callers"},
    "shared_state": {"status": "reviewed", "evidence": "src/state.kt: consent affects automatic launch"},
    "navigation": {"status": "reviewed", "evidence": "src/navigation.kt: SAVE keeps form; CONTINUE has no form"},
    "lifecycle": {"status": "reviewed", "evidence": "src/state.kt: restoration and repeat entry inspected"},
    "legacy_behavior": {"status": "reviewed", "evidence": "D-001 and feature-off branch establish preserved route"}
  },
  "behaviors": [
    {"id": "B-1", "kind": "change", "statement": "Show reminder after save", "basis": "R-1", "requirement_ids": ["R-1"], "verification": {"status": "planned"}},
    {"id": "B-2", "kind": "preserve", "statement": "Flag off retains previous route", "basis": "D-001", "requirement_ids": ["R-1"], "verification": {"status": "planned"}}
  ]
}
```

Six mechanism keys require reviewed/not_applicable/unknown plus evidence or reason. Non-UI work can mark navigation not_applicable. For isolated new components explain isolation under legacy_behavior, rather than inventing preserved behavior. Each behavior needs a known requirement ID for scope; preservation can derive from code and approved decisions. `kind` is change/preserve/unknown. At delivery, verification needs status passed/waived, method, evidence and digest. Waiver evidence must state reason, residual risk and follow-up/acceptance authority; waiver is not a passing test. Honest manual observation is valid evidence.

## After editing and before delivery

Run `python3 core/scripts/impact.py <PROJECT> <ID>` to read changed paths and current digest. Compare committed, staged, unstaged and nonignored new files with explicit allowed files (renames include both paths). Unrelated pre-existing edits need exact-path excluded_changes reasons; do not exclude affected code. Scope expansion requires investigation and updated boundaries; product choices follow existing approval rules. Inspect actual diffs, not just filenames.

Run appropriate regressions for changed and preserved behaviors. Capture digest before and after tests; only if equal record it in verification, with actual method and evidence (test/manual scenario, tested commit/build, observed outcome). `validate-feature.py --stage check` checks scope and evidence freshness. render-workspace.py generates impact.md. Include waivers in delivery-report.md.

The digest includes changed file contents/modes, inspected files and checklist meaning. Editing a registered dependency or boundary invalidates results; workflow progress alone does not. Reassess affected behaviors and rerun appropriate tests. Evidence transfer for demonstrably unrelated changes must be explained, never silently replace old digests. This minimum uses a shared digest, so it can conservatively invalidate multiple behaviors; per-behavior automatic dependency analysis is deferred.

## Limits and sharing

When verification.json is adopted, current impact behavior evidence comes from its corresponding rows; do not duplicate manual results into impact.json. Follow verification-workflow.md for generated lists, mapped checks and manual observation recording. Old inline verification remains historical; missing/stale list evidence cannot fall back to it.

Requires Git with an existing ancestor commit and regular file paths; symlinks/submodules require manual handling and are not automatically validated. Ignored new files and workflow records are excluded from scope discovery; explicitly inspect ignored business sources. The helper reads Git changes and registered files, not a full-project semantic scan. History-only commits do not stale content evidence; still report actual tested build identity. Scripts cannot prove source completeness, authority or test execution. Historical fix verification is not automatically propagated.

Share impact.json and generated view with feature records after normal sensitivity review. No automatic commit, push or installation.
