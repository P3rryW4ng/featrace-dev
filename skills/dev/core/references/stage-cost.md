# Optional stage cost observations

Use when evaluating a real workflow or an explicitly requested isolated comparison. This is lightweight local measurement, not a delivery prerequisite; unavailable telemetry must not block coding, testing or closure and must not prompt the user to fill another form.

The optional `stage_cost.py` journal lives only at `.agent-workflow/scratch/<ID>/stage-cost.json`, must be Git ignored and is separate from authority/acceptance. Under existing authorized stage work:

```text
python3 core/scripts/stage_cost.py start <PROJECT> <ID> --category test
python3 core/scripts/stage_cost.py stop <PROJECT> <ID>
python3 core/scripts/stage_cost.py status <PROJECT> <ID>
```

Categories are test, verify, waiting, record_maintenance. Stop the current interval before changing categories. Start waiting before yielding for product/environment input, stop it on resumption; uninstrumented time remains unmeasured. Do not loop commands per file or create a second workflow state machine. A forgotten active interval is not measured completed work. The recorded value is elapsed wall time, including execution waiting within that category; it is not Agent CPU/active-thinking time or automatically the whole feature's duration. Clock/boot inconsistencies preserve the unfinished journal and return unavailable.

Only attach actual interval-scoped provider output through `stop --usage <usage.json>` when available. JSON uses `scope: interval`, a concrete `source`, optional `tokens` with input/output/cache_read/cache_write integer counts, and optional `cost` with value/currency. Keep the scope and provenance; the helper validates shape, not the provider's semantic truth. Do not substitute account quota percentages, session/context-window sizes, cache size or model-price estimates. Without data, tokens and cost are null/unmeasured. Do not sum cache/input classes into a fabricated billed total or compare different measurement windows as A/B.

Starting views separately report their defined byte sizes. These are not measured tool-read bytes or a prediction of token savings. In isolated comparisons, keep input identity, actual tool paths, discoveries/false judgments, elapsed intervals and available usage. Report both output/reading overhead and missing measurements. Optimize only when information completeness stays intact; no useful new discovery or a smaller JSON alone proves real delivery benefit.
