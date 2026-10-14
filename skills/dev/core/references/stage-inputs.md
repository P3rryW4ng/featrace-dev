# Test / Verify starting views

Use inside the existing authorized Test or Verify stage when a feature has large records/history, repeated reads, a scoped task/item investigation or an actual handoff. This is a read strategy, not another Skill, permission boundary, test runner, canonical specification or completion check. For a small feature, direct canonical references may cost less; do not generate layers merely to satisfy a format.

```text
python3 core/scripts/stage_view.py capture <PROJECT> <ID> --stage test --task <TASK-ID>
python3 core/scripts/stage_view.py capture <PROJECT> <ID> --stage verify --item <EXACT-ROW-ID>
```

Repeat task/item options for a related slice; omit both for all active requirements. Save a needed handoff snapshot only in authorized ignored scratch. The same snapshot passed downstream must first be checked:

```text
python3 core/scripts/stage_view.py check <PROJECT> <ID> --snapshot <view.json>
```

A stale/content-changed return stops use of that view; regenerate from current authority. After an authorized Test actually writes results, create a new Verify view. Do not reuse the pre-run view or its digest as a result. Never feed a Test-generated recommendation as an independent review's intended answer. Opt-in independent Verify and v6 claim review retain their original binding/dispatch rules; this view does not replace either.

The view includes complete linked requirements (every AC, exception and assumption), related tasks/traceability, preserved and unscoped impact authority, applicable decisions/fixes, every unresolved feature decision/fix, current row contracts/effective states, latest observed results, quality selection/result metadata, source identity and readback references. Shared preservation can expand the parent requirement set. Unknown/unscoped linkage stays visible; omitted IDs are a reading navigation aid, not proof of semantic independence.

Past histories, retained-proof bodies, raw quality output, code/tests and original source contents stay at their exact canonical references. Retained rows flag provenance readback; they are not new execution. Inspect original source clauses, actual assertions and runtime scope before a semantic conclusion; read full history/receipts when interpreting retained results or a withdrawal. Missing sources/plan/reviews or stale mappings are shown as attention items, not passed over. Investigate callers and shared state beyond the selected task. If a projection exposes ambiguous linkage, return to Scope/authority rather than assume omitted material is irrelevant.

Test owns exact check selection/execution, actual assertions, skipped/failed cases and uncovered scope. Verify owns comparison with the complete claim, concrete counterexamples and current evidence; neither a passing command nor this view authorizes complete. Whole-feature audit and all active claims remain mandatory at Deliver, even if the current reading slice is narrow.

`metrics` measures serialized starting-payload bytes and loaded canonical JSON bytes, with an explicit definition; it is not actual Agent read volume, tokens, billable usage or a net-efficiency claim. A small feature may have a larger projection because identities/unknowns add overhead. Views are deterministic and read-only; the existing full input binder covers omitted authority, source/code and Skill changes so a handoff cannot silently survive an omitted-record update.
