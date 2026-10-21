# Acceptance contract v1 (schemas 6/7 and explicit schema8 storage)

Use this reference only when `verification.json` has `schema_version: 6` or `7` and
`acceptance_contract: 1`, or for an explicitly prepared schema8 envelope described below, or when evaluating preparation. Installation
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

Preparation is explicit, not a normal response to stale evidence. A declared
legacy planning route (policy marker2) refuses conversion by this helper; do not
silently change the chosen route. Existing scoped marker1 work retains its
schema7 obligation. Inspect readiness before recommending preparation. It requires the
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

Scoped new work uses schema7 with verification_policy1 under [verification-policy.md](verification-policy.md). It keeps the same acceptance event format but requires checked classification/project policy and capable hosts; 0.19.0 readers reject this schema. Existing schema6 remains supported and is not silently changed.


## Explicit snapshot storage (schema8, 0.22.0 explicit opt-in)

Schema8 is a single-file content-addressed envelope around the complete acceptance
record, with `storage.profile` retaining schema6 or schema7 semantics. It is not a
new execution contract and does not reduce claim coverage. Literal evidence stays
text, not compressed. Only the shared loader may interpret logical JSON Pointers;
raw JSON tools see the envelope, not `/items` at its physical root.

Do not rewrite a completed record to shrink it. Existing schemas remain unchanged.
For an active, committed schema6/7 original, explicit authorized preparation is:

```text
verification.py prepare-storage ROOT ID --approval approval.json
```

Approval requires `snapshot_storage: 1`, actual authorization `evidence`, and every
participating `hosts` entry with `name` and `snapshot_storage_capable: true`.
Preparation changes this feature's format only, records the recoverable Git original,
preserves every original fact/event/world digest, and executes no checks. All readers
must support schema8; old readers refuse. New acceptance preparation may explicitly
include the same approval fields; installation alone never selects the format.
No new automatic downgrade is supplied: preserve the original; new events/facts
must never be discarded to run an older tool. Missing, altered, cyclic, unreachable
or excessively expanded objects refuse; never treat a reference hash as recovered
proof. Atomic single-file writes keep the complete reachable object pool together.
Loading still expands the logical record and validates history; no constant-memory
or universal speed improvement is promised.

### Static investigation and observation

Schema8 `record` optionally accepts `--evidence-kind static_analysis` or
`runtime_observation`, together with `--observed-at` (actual ISO8601 time with zone,
not later than registration). `at` remains registration time; `tested_revision`
remains the inspected input revision. Old facts retain their original fields.
Do not date a repeated description as new analysis. Static proof of no influence
may support a preservation claim; it is not runtime proof of all old behavior.

### Negative classification and judgment correction

For new schema8 negative assessments, `negative_kind` can be `observed_failure`,
`evidence_gap`, or `judgment_error`. Review may include `review_context` with actual
`host`, `context_id`, `reviewer`, matching the host provenance artifact. A continued
original independent context is not a second independent source or a newly created
context; do not fabricate either. Omitted classification preserves old conservative
rules. Facts with failed/unavailable status remain independent barriers.

Normally resolve a negative through new relevant facts or legitimate authority.
A narrow `barrier_resolutions` entry may instead use:

```json
{"barrier_id":"<original-event>:<claim-key>","kind":"judgment_correction",
 "error_kind":"scope_overreach","original_scope":{"source_basis":"<exact original>",
 "required_scope":"<exact original>","observed_scope":"<exact original>"},
 "addresses":"Which original inference was wrong and why",
 "evidence":"Exact existing fact references and exclusion reasoning"}
```

`error_kind` is `scope_overreach` or `evidence_misread`. This requires a previously
classified evidence_gap/judgment_error, the same actual independent context, exact
same world and claim authority/version, and the complete same original fact set.
Any corresponding failed/unavailable fact refuses this route. The original negative
and new disposition both remain. Unknown influence or absent proof stays unresolved;
changing reviewer, narrowing facts, changing authority or adding a label is not a
correction. The helper checks structure and identity, not semantic truth. If a real
behavioral gap remains, supply targeted evidence rather than wording a correction.
