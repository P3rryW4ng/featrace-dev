# Acceptance contract v1 (schema 6, explicit opt-in candidate)

Use this reference only when `verification.json` has `schema_version: 6` and
`acceptance_contract: 1`, or when explicitly evaluating preparation. Installation
never prepares projects. Schema 1–5 keep their original workflow. Do not downgrade,
re-sign observations, use old carry/adoption writers, or reopen completed features
to evaluate this contract.

## Responsibility and entry

The existing check executor records actual execution. Acceptance judges whether
facts support current requirements and preserved behavior. A change to a record
means applicability needs review; it does not by itself require a physical rerun.
Changed code/test/config inputs still follow the existing whole-selection execution
contract. This version does not provide per-gate caching or combine older attempts.

Ordinary status, inventory, impact evidence, audit and final review read one resolver.
Output separates `fact_status`, `applicability`, `coverage_verdict` and blockers.
`acceptance_eligible` is only coverage; `delivery_eligible` is established by full
composition with original guards, never by a row-status sum.
A supported judgment is not proof that a test was executed again. The original
version, time and Git/evidence reference remain unchanged.

Preparation is explicit, not a normal response to stale evidence. It requires the
existing project-level execution contract 2, inventory of participating active
features and capable hosts, authorization, and recoverable committed originals.
Active composite carry/scope/adoption sources currently refuse preparation. Do not
omit them to get through. Unknown/old hosts and uncommitted originals require
resolution; preparation does not commit them. Fresh features may initialize without
inventing old observations. Historical complete features are not migration targets.

Advanced internal operations (not new user-facing `/dev` commands):

```text
verification.py prepare-acceptance ROOT ID --approval approval.json
verification.py sync ROOT ID [--resolutions source-alignment.json]
verification.py status ROOT ID
claim_review.py capture ROOT ID
claim_review.py apply ROOT ID --request request.json --review review.json
verification.py compose-acceptance ROOT ID
```

Approval names every current active feature and each participating schema6-capable
host, with the actual authorization evidence. It cannot assert knowledge of unknown
machines. A changed criterion, split, merge or retirement needs explicit source
alignment; text similarity is not evidence of equivalent product meaning.

## One review, then differences

Capture is permitted with incomplete, failed or unknown coverage. It freezes the
complete world, facts, active claim versions, latest prior assessment and generation.
There is no “first pass all acceptance in order to capture its first assessment”
cycle. Do not run checks just to enter capture.

The independent context inspects every change and the current complete claim set:

- Classify each delta as affected, unaffected with evidence, or unknown, identifying
  targets and inspected evidence. Dependency absence alone does not establish no
  impact. Unknown changes leave gaps.
- Partition all current claims exactly once into `assess`, `reuse` or `pending`.
  Reassessment names required/observed scope, source, original facts and a contrary
  case. Reuse cites the latest prior supported judgment, complete exclusion proof
  and semantic equivalence across changed versions. New/split keys do not inherit
  support. Shared exclusion evidence can be grouped once.
- Resolve a prior negative only with explicitly targeted new evidence or legitimate
  changed authority. A new reviewer, unrelated change, renamed key, retired row or
  older success does not resolve it. Waivers need original authority and current
  scope, not conversion from a passed observation.

A reuse group has `targets` (each `claim_key` / `from_key` pair), `evidence` and
`semantic_equivalence`. Fresh findings contain `claim_key`, `verdict`, `source_basis`,
`required_scope`, `observed_scope`, `evidence_ref`, `counterexample_check`, `fact_refs`.
`pending` names a key and reason. The return also binds `request_digest`, reviewer,
reviewer evidence, all `change_findings`, and explicit `barrier_resolutions`.
Supported/partial/unknown/approved_waiver are distinct judgments; a fully negative
return is saved, not discarded. Hash and field checks cannot prove semantic truth.

The review provenance is a regular local host artifact under
`.agent-workflow/scratch/acceptance-reviews/ID/`, referenced by path and SHA-256.
It records the frozen `request_digest`, `host`, actual separate `context_id`,
`reviewer`, and `fresh_context: true`. Preserve the actual host output that supports
those fields. Never manufacture a separate context by assigning a new label.
If the host cannot provide a truthful fresh independent context, leave provisional.
Provenance is rechecked before apply. It is a judgment output, not recursively an
input to the same captured world. A matching JSON declaration is not independent
certification by the helper.

Apply holds execution then plan locks, rechecks live inputs and commits one atomic
verification event. Drift refuses without partial adoption. Repeating the exact
already-applied return is idempotent only while its inputs still match. Do not select
an older favorable `from` judgment.

## Complete composition, not whole repeated judgment

Final composition still covers every current business claim, required gate and
existing source/task/fix/device/module/lifecycle guard. Grouped reuse reduces repeat
judgment; it does not reduce delivered scope. Controlled `feature.baseline.deliveries` registrations are delivery outputs, excluded
from the semantic world and still checked by original terminal validation. Free-form
`status_note` is not ignored; stabilize such explanations before review.
New manifest/review/Markdown files are
rebuildable projections, not additional manually editable approval ledgers. Rebuilding
views never runs checks. Generated views cannot stale the evidence they describe.

Original history lives in recoverable Git objects with commit, blob, byte hash and
JSON Pointer. Missing original objects, unsafe links and unknown environments do not
become green from a digest. No automatic privacy rewrite, upload or history rewrite.
Actual new observations use normal record with the current frozen input and revision;
no old observations are registered as new tests.

A pre-use restoration is explicit and only possible before new facts/judgments and
while controlled inputs still match. Otherwise preserve the schema6 records and stop;
no destructive automatic downgrade. Known old readers reject schema6, but the helper
cannot isolate arbitrary old binaries writing other records.

Exit 0 means an operation succeeded or a view is readable, not product acceptance;
1 is invalid/unsafe/conflicting input; 2 is valid but unfinished acceptance/execution.
Typed blockers identify reconciliation, absent originals, unknown input, incomplete
review, unresolved negative, unavailable execution, drift, busy writers and disabled
legacy writers. Resolve the specific cause; do not fall back to global legacy stamps.
