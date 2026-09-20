# Confirmed requirement baselines and revisions (0.5.0 minimum)

Read before `/dev revise`, or changing requirement meaning in a feature with `feature.baseline`. `requirements.json` stays the sole current specification. Original PRD bytes stay unchanged; `revisions/CHG-*.json` are separately recorded proposals/diffs. Their later date does not confer authority. Approved decisions and source evidence establish authority only for the affected rules.

## Agent entry

`/dev revise [ID] <change description> [--source <file> ...]` (Codex `$dev revise`) resolves the current feature like fix/clarify. No new document is required for a small clarification. For supplied files, preserve bytes via propose --source. The Agent reads and reconciles content; the helper does not parse PRDs or infer changes. Restore an archived feature before revisions.

Classify first: a pure implementation bug uses fix and leaves requirement meaning unchanged; interpretation_correction repairs a proven misreading, clarification fills confirmed detail, requirement_change changes product intent. Reuse the relevant decision in decisions.json. Explicit user confirmation already in the conversation is sufficient evidence: record its reference, do not ask again merely for procedure. Pending choices can be proposed but cannot be applied. For existing-rule explanations, use clarify's existing_rule evidence rather than inventing a new product decision. Proposal decision IDs may point to pending decisions that are later approved; the immutable proposal itself is not silently edited to change its scope.

## Opt-in adoption

Legacy features continue unchanged until revision control is explicitly adopted. Do not migrate every archived feature or bulk backfill history. For a new feature, finish the original PRD reading/full review and confirm its active requirements before adopting. For an existing complete feature, adoption retains an initial semantic snapshot but changes product status to provisional because version-specific verification has not yet been registered; explain this before adopting as part of requested continued work. It does not retroactively declare old acceptance false. Use a new feature for a genuinely separate product scope.

```sh
python3 core/scripts/revise.py init <PROJECT> <ID> --reason <ORIGINAL-CONFIRMATION-BASIS>
python3 core/scripts/revise.py status <PROJECT> <ID>
```

init runs develop validation, requires confirmed/deprecated requirements, registers baseline 1 and no delivery. Feature.baseline contains the initial semantic snapshot, current version/digest, applied/cancelled event history and version-specific deliveries. This historical snapshot is not a second editable current spec. A current baseline is what is confirmed, not what has been implemented.

## Propose and apply

Prepare JSON from the actual baseline and evidence, using the digest returned in requirements.json. The helper checks the base version and before values rather than guessing a merge. Example (replace fixture strings with actual evidence):

```json
{
  "base_version": 1,
  "base_digest": "<current feature.baseline.digest>",
  "kind": "clarification",
  "reason": "Clarify return behavior",
  "decision_ids": ["D-005"],
  "evidence": ["D-005: user confirmation in the recorded conversation"],
  "impact_review": "Inspect the SAVE and CONTINUE entries, form state and caller navigation; update T-2 and return regression",
  "preserved_behavior": "Feature-off routing and previously accepted verification flow remain unchanged",
  "task_ids": ["T-2"],
  "code_paths": ["app/navigation/WalletNavGraph.kt"],
  "test_ids": ["TEST-4"],
  "changes": [{"requirement_id":"R-2", "field":"statement", "before":"Return to the previous page", "after":"From the SAVE entry, return to the populated form"}]
}
```

```sh
python3 core/scripts/revise.py propose <PROJECT> <ID> --input <PROPOSAL-JSON> [--source <FILE> ...]
python3 core/scripts/revise.py apply <PROJECT> <ID> --revision CHG-001
# Reject/withdraw or replace a mistaken proposal without erasing it:
python3 core/scripts/revise.py cancel <PROJECT> <ID> --revision CHG-001 --reason <REASON>
```

Proposals are immutable files created exclusively; applying updates only the canonical JSON and appends a history event there. Source copies are content-addressed under sources/revisions, and remain subject to the existing source-sharing policy. Duplicate identical proposal input without additional sources is reused. Repeated source bytes reuse the same file. Propose failure may leave unreferenced preserved source copies; report them, never delete original evidence automatically. A failed canonical replacement leaves the proposal pending and retryable. Avoid concurrent edits to one feature: current-byte checks and exclusive proposal creation are not a global multi-file transaction.

Only one proposed revision is allowed; after applying it, verify that baseline before starting another revision. No automatic branch merging. Base/version mismatch or changed before value requires reviewing the current content; cancel and repropose deliberately. Append-only applied/cancelled records preserve proposal hashes. Changed applied history or direct semantic drift is rejected by status/validation.

The semantic version covers id, title, statement, status, acceptance_criteria and assumptions. Patch one named field with before/after. To add a new requirement use field `$requirement`, before null and a full after object with a fresh ID and the ordinary requirement fields. Retire an old requirement by setting status to deprecated; no hard delete or ID reuse. Unchanged rules stay unchanged. Task/test/source-item links and source annotations can still be reconciled separately, but they are not versioned by this minimum semantic mechanism; normal PRD review and traceability checks still apply. This is not full source authority/version management.

Apply requires approved named decisions with chosen values and verifies preserved revision-source hashes. The Agent must confirm that those decisions actually support the patch: structural approval does not prove semantic authority. Impact task/code/test lists are reviewed planning references, not automatically proven dependencies. Empty automatic test_ids is allowed for report-backed manual-only validation; explain coverage in impact_review. Do not claim every code path or test is known.

## After application: requirement version versus delivery version

Apply advances the confirmed baseline and marks feature.status provisional; it does not change task states, code, source applicability or clarification application markers. Inspect affected tasks/code/historical fixes, reopen or update tasks as needed, and reconcile source/decision references and intake aspects without rewriting original PRD bytes. Cite the approved revision when old text and new confirmed intent differ. For a replaced original statement/AC aspect, preserve its old text and target_text, adding `superseded_by: CHG-001` and a nonempty `supersession_reason`. It must match the before value of that applied revision's requirement/field; only those aspects are exempt from matching today's target. Each active requirement still needs current non-superseded coverage. Register the unchanged applied `revisions/CHG-001.json` as a document evidence source/read unit (also update feature.prd_paths if present), then map its confirmed after text to the current requirement; a pending or modified proposal is not accepted as intake evidence. This permits a conversation-backed correction without inventing an external PRD. Run full review-prd after real semantic review; old intake digest is intentionally stale. Mark clarification application applied only when its actual scope has been implemented or otherwise fulfilled.

Pending proposals block develop/check until applied/cancelled. Applied but unverified baselines allow development and check, but cannot be complete. Fixing code to meet unchanged meaning does not require a new revision.

```sh
python3 core/scripts/project.py check <PROJECT> --feature <ID>
python3 core/scripts/audit-delivery.py <PROJECT> <ID>
python3 core/scripts/revise.py verify <PROJECT> <ID> --code-revision <TESTED-GIT-COMMIT> --evidence delivery-report.md
python3 core/scripts/render-workspace.py <PROJECT> <ID>
```

For controlled features, selected quality checks must bind their run to this baseline version/digest; a prior or unbound report cannot verify a new baseline. Checks also compare the binding before/after execution. verify requires structural check, current audit, all tasks done, source applicability resolved, selected automatic revision test IDs, a nonempty report and a supplied commit resolving to current HEAD. Inspect uncommitted code and real test assertions manually; the existing project snapshot is not a full dirty-tree hash. Final code must be committed before these checks. A later documentation-only commit does not rewrite the historical tested commit or mean the earlier audit ran on that new HEAD.

The Agent must inspect actual manual/UI results and report scope before verify. verify records version, semantic digest, code commit and report hash; it does not automatically set complete or prove report truth. Only then apply the existing completion rules and update the delivery report. Historical deliveries stay tied to their original baselines; new fixes may require new verification of the same baseline. Before verify leave feature.status provisional; a premature complete is rejected and must be corrected rather than bypassed.

Generated revisions.md summarizes historical proposals; feature-status and spec.md show confirmed/verified versions separately. No automatic impact graph, module current-behavior index, source supersession inference or regression selection is implemented.
