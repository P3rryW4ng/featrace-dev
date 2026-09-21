# Historical fix regression review (0.5.11)

Use before business-code edits through develop, fix implementation or revise implementation, and refresh before check. This is part of existing commands, not a user-facing command.

Run:

```sh
python3 core/scripts/regression_review.py sync <PROJECT> <ID>
```

The helper reads the current feature's registered module labels and code paths from traceability/impact records. It scans the current and other feature workspaces for `verified` fixes and proposes a candidate when a module overlaps or an exact/parent code path overlaps. It does not read all source code, infer semantic equivalence, reopen a fix, or claim that every relevant historical defect was found.

Review `regression-review.json`. For every candidate choose exactly one:

- `retest`: explain why the repaired behavior is exposed and add nonempty `planned_checks`. At check, add a `result` with `status` (`passed` or `waived`), `method`, `evidence`, `tested_revision`, and the current `review_digest`. A waiver also needs `residual_risk` and `approval_ref`.
- `not_applicable`: explain concretely why the current change cannot affect the repaired behavior. Module overlap alone is not a reason to retest, and “unrelated” alone is not an adequate reason.

Each disposition copies the candidate's `candidate_digest`. Re-run sync when current modules/paths or historical verified-fix evidence changes. Unchanged dispositions survive sync; changed or removed candidates require review, and old retest results become stale when the overall review digest changes. Do not edit candidate fields manually.

`validate-feature.py --stage develop` blocks adopted workspaces with missing, stale or undispositioned candidates. `--stage check` additionally requires current retest evidence. Legacy workspaces without adoption receive a warning; before new business-code edits, run sync to adopt the record instead of relying on that compatibility path. Rendered `regression-review.md` is a review view; JSON is canonical.

Candidate discovery is deliberately narrow. Missing module labels, incomplete traceability/code refs, renamed paths and fixes recorded outside this workflow can cause false negatives. Broad module matches can cause false positives, which the explicit `not_applicable` reason handles. Continue normal impact investigation and code review; this record does not replace them.
