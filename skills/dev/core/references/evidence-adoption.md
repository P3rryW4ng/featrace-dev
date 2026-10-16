# Adopt original observations after an interpretation correction (0.15.0)

Use only for a human-approved correction of how existing sources/behavior were understood. This is separate from ordinary unchanged-contract carry. It can adopt the latest original observation from a retired row into its replacement, or from the same stale active row when its parent changed. Workflow records may be uncommitted. Business code must be committed and clean. It does not execute tests, authorize device/server actions, waive a gap or complete a feature.

## Boundaries

- Establish the full current claim and the approved decision's exact scope before freezing. A new requirement, expanded behavior, actual failure or partial/unknown coverage requires ordinary Verify and targeted evidence.
- Select an explicit source collection (`items` or `retired`), exact row ID and latest history index. No search for an older green result. Source and target must share the same requirement/AC or impact slot. Failed, waived and derived retained sources are refused. An `unavailable` original observation is eligible for investigation only when the approved interpretation explains the old expected-value mismatch; it is never automatically treated as a pass. Review actual observations, every withdrawal, both histories and all conflicting evidence.
- Do not construct historical authority by copying today's corrected requirements and calling them old. Recover the original contract from a saved snapshot, Git record or archived original transcript and document its provenance. If that cannot be established, stop. File hashes prove bytes, not historical truth or reviewer independence.
- Package identity must come from the original archived build/install evidence, not a later local rebuild. A full Git commit alone does not prove the installed package or a dirty build's contents. Unknown package/tree identity remains unknown.

## Prepare once, review the batch once

Archive privacy-checked provenance before capture. One request per target contains `item_id`, `source: {collection, item_id, history_index}`, `decision_id`, `contract_ref`, and distinct `evidence_refs`. Evidence refs are project-relative paths beneath this feature's durable `evidence/` or `sources/`; scratch is not evidence authority. The recovered contract input has the narrow exception below.

`contract_ref` is a JSON archive with `feature_id`, original `row_contract` (all original row fields except history/retention), original `parent_claim` (the complete requirement, or behavior plus linked requirements), `result_hash`, original full `tested_revision`, original `observed_at`, and `provenance_refs` naming archived files in evidence_refs. Its result hash must resolve to the untouched original result. This archive describes recovered facts, not a new observation. The reviewer must verify its actual chronology and source; the helper cannot certify that a newly written contract was historically true.

To avoid staling unrelated carry results merely by adding a contract archive, `contract_ref` may instead name an explicitly Git-ignored regular file under `.agent-workflow/scratch/<ID>/`. It is an input-only recovered contract, not new authority: its complete contents and hash are frozen and then durably stored in the shared review event. Its provenance_refs and all evidence_refs must still point to existing durable feature evidence/sources. Review must establish original chronology from those actual materials. The temporary contract must remain unchanged until apply; after apply it may be removed without invalidating the retained observation. This route does not certify a missing historical contract or authorize omission of missing original evidence.

```text
python3 core/scripts/evidence_adoption.py capture <PROJECT> <ID> --requests <requests.json> --output <PROJECT>/.agent-workflow/scratch/<ID>/adoption-input.json
python3 core/scripts/evidence_adoption.py apply <PROJECT> <ID> --snapshot <snapshot.json> --review <review.json>
```

Give a fresh-context read-only reviewer the snapshot and the exact archived evidence and source/target histories. Do not prepopulate supported conclusions. Review JSON has batch `input_digest`, `status: supported`, `independent_context: true`, `reviewer`, and `rows`. Each row must contain:

- `item_id`, `status: supported`, `change_kind: interpretation_correction`, `coverage_expanded: false`, `contradictions: []`;
- specific `claim_evidence`, `contract_provenance`, `decision_scope`, `source_status_explanation`, `history_review`, `environment_evidence`, `counterexample`;
- `original_identity: {revision, worktree_verified: true, explanation, evidence_refs}` using bound archived paths;
- complete transitive `dependencies` and `changes: [{path, relationship: unaffected, evidence}]` for every frozen changed business path.

These are judgments to be investigated, not defaults or proof from checkbox values. Dependency files must be unchanged regular Git files between original tested code and now. Unknown environment, changed behavior or incomplete claim support is refused. Omit unsupported rows from a newly captured batch, preserve their findings, and obtain the missing evidence. Never relabel an old review for a changed snapshot.

## Result and readers

Apply re-captures all inputs and checks again immediately before an atomic locked save. A successful batch adds one shared `adoption_reviews` event and one `retained / interpretation_adoption` result per target, referencing the original result rather than copying its private text. Original history, tested_revision and observed_at stay intact; adopted_at/reviewed_revision describe the new applicability review. No original failed/unavailable result is rewritten. Other rows and automatic gate histories are untouched.

Timestamp precision: `observed_at` copies the source result's `at` verbatim. That is the original result-recording timestamp, not independent certification of when execution began or ended. Verify actual execution times from the original raw artifacts and review narrative; do not infer them from registration time. The new result's `at` (shown as `adopted_at` in links) is the applicability-registration time, never a new test time.

Only adoption upgrades verification.json to schema 3; use readers supporting this contract for status, sync, final claim review, audit and any later correction. Older readers must reject it. Schema 1/2 remain readable; descriptive corrections never downgrade schema 3. Status, generated views and Test/Verify views expose provenance links. Final independent claim review still covers the actual complete claims and limitations. This command does not bypass it.

Currentness binds current requirements/decisions, code, authority and archived evidence, plus the original history. Later evidence/code/authority changes or a new source withdrawal make the result stale. It deliberately retains the existing whole-evidence-directory identity; unrelated future archive additions can still require a new review. General evidence composition, arbitrary revised claims and new behavior are outside this path. Real CC adoption and net cost remain to be measured.
