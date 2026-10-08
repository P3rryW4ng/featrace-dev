# Historical fix regression review (0.5.38)

Use before business-code edits through develop, fix implementation or revise implementation, and refresh before check. This is part of existing commands, not a user-facing command.

Run:

```sh
python3 core/scripts/regression_review.py sync <PROJECT> <ID>
```

The helper reads the current feature's registered module labels and code paths from traceability/impact records. It scans the current and other feature workspaces for `verified` fixes and proposes a candidate when a module overlaps or an exact/parent code path overlaps. It does not read all source code, infer semantic equivalence, reopen a fix, or claim that every relevant historical defect was found.

Review `regression-review.json`. For every candidate choose exactly one:

- `retest`: explain why the repaired behavior is exposed and add nonempty `planned_checks`. At check, add a `result` with `status` (`passed` or `waived`), `method`, `evidence`, `tested_revision`, and the current `review_digest`. A waiver also needs `residual_risk` and `approval_ref`. For a newly created schema v3 review, `result.checks` must contain one entry per `planned_checks` item, in the same order, with the exact `planned_check` text, `status`, `method` and observed `evidence`. A waived item also needs its own `residual_risk` and `approval_ref`; if any item is waived, the overall result must be waived. A single paragraph about only some planned steps cannot pass the check gate.
- `not_applicable`: explain concretely why the current change cannot affect the repaired behavior. Module overlap alone is not a reason to retest, and “unrelated” alone is not an adequate reason.

Sync is discovery, not disposition. A `retest` action is still a workflow and risk choice; do not infer it merely because paths overlap. If the user says to only sync, list, inspect, stop, or not choose, leave every newly discovered candidate pending and stop after reporting it. Record a disposition only when the current request authorizes review/decision, or an already documented project policy gives one unambiguous outcome. An explicit user limit always takes precedence.

Each disposition copies the candidate's `candidate_digest`. Re-run sync when current modules/paths or historical verified-fix evidence changes. Unchanged dispositions survive sync. Changed or removed candidates require review; their prior disposition and result move into top-level `history` with the old candidate snapshot and replacement digests. History is audit evidence only and never satisfies the current gate. Do not edit candidate or history fields manually.

Example for a two-step v3 retest (use actual observations, not this fixture text):

```json
"result": {
  "status": "passed",
  "method": "unit test and device observation",
  "evidence": "both planned checks completed",
  "tested_revision": "current-build-identity",
  "review_digest": "current-review-digest",
  "checks": [
    {"planned_check": "Run the existing regression test", "status": "passed", "method": "unit test", "evidence": "test command exited 0"},
    {"planned_check": "Verify the return destination", "status": "passed", "method": "user device observation", "evidence": "returned to the previous page"}
  ]
}
```

Existing schema v1/v2 records remain readable and sync does not silently migrate their results. For those records, the Agent must still compare the free-text evidence against every planned step; a structurally valid legacy result does not prove full coverage. Split broad planned text into observable steps when the result would otherwise be ambiguous.

`validate-feature.py --stage develop` blocks adopted workspaces with missing, stale or undispositioned candidates. `--stage check` additionally requires current retest evidence. Legacy workspaces without adoption receive a warning; before new business-code edits, run sync to adopt the record instead of relying on that compatibility path. Rendered `regression-review.md` is a review view; JSON is canonical.

Candidate discovery is deliberately narrow. Missing module labels, incomplete traceability/code refs, renamed paths and fixes recorded outside this workflow can cause false negatives. Broad module matches can cause false positives, which the explicit `not_applicable` reason handles. Continue normal impact investigation and code review; this record does not replace them.
