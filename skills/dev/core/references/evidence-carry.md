# Reviewed continuity of old manual evidence (0.12.0)

Use only when ordinary Verify finds previously passed manual requirement/impact evidence stale after a local change or unrelated decision. Existing `retain` remains unchanged: it needs prior complete dependency provenance and a preserved impact row. This alternative reconstructs a Git comparison and requires a fresh-context relevance review; it does not claim the old row had file provenance, does not supply a missing observation, and never runs automatic gates or marks complete.

## Eligibility and investigation

The latest result must still be passed/retained, not failed/unavailable/waived. Do not select an older green result behind a withdrawal. Its full tested commit and historical feature contracts must exist, and be ancestors of the current HEAD. Business worktree changes must be committed before capture. Workflow-only edits are allowed. The entire parent requirement (or impact behavior and its linked requirements) and row contract must match the historical revision. If that contract changed, obtain current evidence for the changed claim. An approved unrelated decision can be reviewed; a relevant change of meaning cannot.

Inspect actual before/current implementation, imports, consumers, state, navigation, tests and authority. A filename or grep miss does not prove independence. Declared dependency files must be existing unchanged regular Git files at both revisions, including transitive behavior paths. Dynamic, ignored, submodule or external dependencies require explicit environment/authority investigation; if their relevance or identity cannot be established, return unknown and perform the affected observation. Do not simplify an acceptance criterion or substitute interface tests for a container/UI result to fit this path.

## Freeze and fresh review

For each eligible row, capture to the authorized project-local ignored scratch directory:

```text
python3 core/scripts/evidence_carry.py capture <PROJECT> <ID> --item <row-id>
```

Save stdout as a disposable snapshot, separate from authoritative records. It contains the complete original result, original tested revision, unchanged full parent claim and row contract, before/current feature records, every changed project path, source/evidence hashes and project content digests. Large whole-project file inventories are hashed internally rather than passed to the reviewer. It is not an automatic relevance judgment or a proof that historical package identity was correct. The reviewer must inspect original observations, archived artifacts and build/environment linkage; an unexplained original identity stays a gap. Older record() results may name HEAD even when business edits existed: Git reconstruction alone cannot prove what ran. Require original_identity with accessible archived package/worktree evidence and a specific explanation; if it cannot substantiate the original tested tree, reject carry rather than infer it. These are inspected attestations, not machine APK verification.

Dispatch a fresh read-only Agent with this snapshot, project/feature paths, this reference and the exact output path. Pass no proposed verdict or router suspicion. It may read actual original authority, historical Git files/diff and current callers/evidence as needed. Respect project compatibility and allowed write roots; if fresh review is unavailable, retain provisional. Multiple rows may share one reviewer context when related, but each needs its own bound verdict; do not repeat whole-project reads or every test per row.

Review output uses:

```json
{
  "item_id": "<exact row ID>",
  "input_digest": "<snapshot input_digest>",
  "status": "supported",
  "independent_context": true,
  "reviewer": "<actual reviewer>",
  "method": "Original evidence and current relevance review; no re-execution",
  "claim_evidence": "What observed/asserted result supports the full parent and exact expected clause; cite original artifacts and coverage limits",
  "dependency_evidence": "Actual direct/transitive caller/state investigation",
  "contract_evidence": "Why each metadata/decision change cannot alter this full claim or its evidence interpretation",
  "environment_evidence": "Original build/package, configuration and external conditions; why continued applicability is supported",
  "counterexample": "A concrete way the old observation could fail to establish this claim, and what evidence resolves it",
  "original_identity": {"revision": "<original full tested_revision>", "worktree_verified": true, "evidence_refs": ["evidence/package-identity.txt"], "explanation": "Actual original build/worktree evidence binds the observed bytes to this revision; HEAD alone is insufficient"},
  "dependencies": ["src/actual-unchanged-dependency.py"],
  "changes": [{"path": "src/changed-file.py", "relationship": "unaffected", "evidence": "Actual diff and relationship investigation"}],
  "record_changes": [{"path": "decisions.json", "relationship": "unaffected", "evidence": "Specific decision and scope analysis"}]
}
```

`changes` must cover snapshot.changed_paths exactly once; `record_changes` must cover changed_records exactly once (empty when none). Use partial/unknown/affected rather than manufacture supported/unaffected. The helper records reviewer attestations; `independent_context` is not host-enforced sandbox/authentication and the router must actually dispatch and inspect the return. A nonempty paragraph is not semantic proof.

## Apply and return

After reconciling actual reviewer evidence, apply one supported return:

```text
python3 core/scripts/evidence_carry.py apply <PROJECT> <ID> --snapshot <snapshot.json> --review <review.json>
```

The helper recomputes frozen inputs, refuses a moving snapshot, changed declared dependency, changed full claim, wrong result identity or unsupported assessment. It appends a `retained` entry with a bound review receipt in existing verification.json and renders the view. Original result, observation time, method and package details stay in history; tested_revision remains exactly original, reviewed_revision is current. Report any older text distinguishing true package/code origin from recording revision; the helper never retroactively fixes a bad original identity.

The new entry is a relevance judgment, **not** a freshly executed pass. Later project code, feature meaning, registered sources or archived evidence changes stale it; workflow-only commits do not. Failed or changed behavior still needs actual targeted tests. Automatic gate execution, quality audit, historical-fix disposition, current dossier checks, v6 claim review and normal Deliver conditions remain required. No automatic mass retention of old rows, permission migration, or backward-compatible interpretation by old installations; update the managed Skill before writing these receipts.

For a subsequent explicit index/annotation-only correction while these results remain current, use [evidence-annotations.md](evidence-annotations.md): freeze before editing and review the bounded patch in one fresh context. Do not redo every full carry or exclude all text files from hashes. Raw artifact or claim changes stay subject to ordinary evidence investigation.

0.12.2 also permits explicit addition of backed-up originals together with index edits through `evidence-annotations.md`. Existing raw bytes remain unchanged; only supported current rows get amendment receipts, while affected/unknown rows stay stale. This is not automatic file exclusion or fresh testing.
