# Clarification workflow (0.4.8)

If the feature has `feature.baseline`, changes to requirement meaning must follow [revision-workflow.md](revision-workflow.md). Reuse this workflow’s decisions and fix evidence; code-only fixes do not revise requirements. Preserve original sources and prior delivery conclusions.

Use `/dev clarify <ID> <question-or-proposal>` for incomplete details, ambiguous rules, proposed changes or uncertainty about effects on existing behavior. It is an investigation and record entry point, not blanket permission to implement a new product rule.

## Register and investigate

Use the existing feature and read its decisions first. Reuse an existing pending decision for the same issue; retain follow-up wording as evidence instead of replacing the original question. Otherwise run:

```bash
python3 core/scripts/record-clarification.py <PROJECT> <ID> "<original question>"
```

The script appends a pending D-number to `decisions.json`, renders `decisions.md`, deduplicates exact pending questions, and changes a complete feature to provisional. It does not initialize a feature, modify a source, approve an answer, or change business code. Ordinary explanation/progress questions need no record unless they expose a material requirement or acceptance gap. Report the recorded D-number to the user; do not claim persistence before writing it.

Read original sources, prior decisions and relevant code/tests before asking the user. For changes in an existing flow, inspect applicable entry points, callers, state lifetime, return/re-entry and automatic/manual transitions. Record the intended change, behavior to preserve and unknowns in `clarification.impact_review`; use decision `impact` for affected requirement/task IDs and code/test references. Check conditions and exceptions: an instruction about resuming after confirmation must not silently apply before confirmation. This is Agent investigation, not automatic impact analysis.

Classify the answer as an existing rule, a confirmed change (including a missing detail settled by a product choice), or withdrawal. An existing rule needs source evidence, not another approval. User choices not settled by evidence remain pending; never treat silence, a hypothesis or current code alone as product approval. Cite an already explicit user confirmation instead of asking again. Distinguish original-source misreading from a later revision by comparing original wording and the confirmed scope. Preserve important qualifiers in excerpts.

## Record contract

Existing decisions without `clarification` keep their previous contract. New clarification decisions use the usual `id`, `title`, `status`, `sources`, `options`, `chosen`, `impact` and optional supersession fields, plus:

```json
{
  "clarification": {
    "question": "Original question, preserved verbatim",
    "recorded_at": "ISO timestamp",
    "evidence": [],
    "impact_review": "",
    "resolution_kind": "unclassified",
    "confirmation_ref": "",
    "application": {"status": "pending", "evidence": []}
  }
}
```

- Decision status: `pending`, `blocked`, `approved`, `superseded`. Pending/blocked retain the existing feature-wide develop/check gate; unrelated investigation may continue. No task-level eligibility is implemented.
- `resolution_kind`: `unclassified`, `existing_rule`, `change`, `withdrawn`. Approved requires a non-empty `chosen`, classified resolution, evidence array of non-empty strings and an impact review (including a reason if nothing is affected). Change/withdrawal also requires `confirmation_ref` identifying actual authorization.
- Application status: `pending`, `applied`, `not_needed`. Pending/blocked decisions cannot claim application. An approved change must be `applied`, with evidence, before check passes; develop allows approved changes awaiting implementation. `not_needed` is only for existing-rule explanations or withdrawals and needs a reason in its evidence array. Applied means the affected records/implementation were reconciled; it does not mean overall delivery or device acceptance passed.
- Supersession: preserve the old record and use `superseded_by` pointing directly to another approved decision. Explain the supersession and preserve links from fixes. Unknown, self or unresolved replacements fail validation.

## Apply and verify

After the answer is grounded or confirmed, synchronize affected requirements, tasks, source mappings and acceptance/test plans. Preserve before/after scope in decision evidence or linked fix records. If requirement meaning changes, perform the PRD/intake review again; copying target text does not constitute review. Investigate affected completed code and old tests; retain historical results and explicitly identify the verification that must be rerun. Implement only within the user's existing authorization; a request for analysis alone is not authorization to change code.

Record actual synchronization evidence or a justified no-change result in `application`; render views and run the appropriate validate stage. Run applicable checks and the delivery audit after implementation, then refresh the delivery report with tested revision, results and missing manual evidence. Do not automatically restore complete or claim validation verifies semantic correctness.

For an observed mismatch, use `fix` and link its `decision_ids` to this decision. If a fix already raises the question, reuse its decision rather than creating a duplicate. Keep the fix's cause/evidence and the decision's product choice in their respective records; clarification alone does not close or verify a fix.

## Ordinary conversation

While this Skill is active on a known feature, material doubts/proposals discovered in ordinary chat follow this same flow; pure explanations remain conversational. If the user explicitly requests discussion without writing, honor that and say it has not been recorded. This rule does not monitor conversations where the Skill was not loaded and cannot guarantee that an Agent recognizes every issue. `/dev clarify` is the explicit persistence entry point.
