# Impact-classified verification and explicit project policy

Load for new development or an incremental change to an existing delivery before
choosing tests. This replaces indiscriminate full-PRD reacceptance, not evidence,
product authority, failure handling or project-required protections. Categories
are reviewed effect declarations; the helper cannot infer true dependencies or
prove an assertion's semantic coverage.

## Entry and contract selection

Inspect `verification_policy.py <PROJECT> <ID>` before offering a format choice.
Report the actual verification schema, project execution contract and preparation
conditions, not “use the installed version's batch review.” Schema5 batch is not
schema6 acceptance v1 or schema7 scoped acceptance.

- New work: initialize the normal records with `init-feature.py ... --verification-policy`
  or `init-change.py ... --verification-policy` within authorized intake.
- New change/defect after a completed delivery: normally create one **incremental
  work item** with a distinct local ID, rather than reopening the historical PRD
  and treating all old criteria as new obligations. Use
  `init-change.py <PROJECT> <CHANGE-ID> --kind change|defect --request-file <REPORT>
  --parent <PARENT-ID> --delivery-revision <FULL-SHA> --delivery-evidence <SOURCE>
  --verification-route legacy|scoped`.
  Confirm the delivered SHA from existing evidence, never infer it from HEAD.
  This captures the committed complete parent and background changed paths while
  leaving all parent records untouched. Add only current objectives and relevant
  preserved/regression criteria to the increment; register sources normally.
  It certifies this increment at the target revision, **not the whole parent or
  every feature in the merged application**. An explicit in-place revision keeps the user’s requested scope; record identity
  alone never broadens testing. An explicit whole merged-build certification does
  require its actual broader scope.
- An already active revision/fix keeps its current identity. Do not move a known
  failure into a new ID to escape its negative history. A follow-up does not
  waive historical repairs: the ordinary historical-regression investigation and
  the relevant existing controls still apply.

The increment's `change_context` binds the parent record and delivery, uses its
captured starting HEAD as the local impact baseline, and lists delivery-to-start
background changes separately. Investigate these once in groups with concrete
shared exclusion evidence; affected groups require current regression claims,
unknown groups stay unresolved. Captured parent failures/open fixes/negative review findings must also be partitioned as unaffected/covered/unknown in `prior_findings` (`id`, `effect`, `claims`, `evidence`). Related findings require current regression criteria; unknown relevance blocks scoped certification. No original failed observation is turned into a pass. No new whole-parent completion claim is implied.
Do not rename a failing merged-build certification as a harmless merge review.

Parent association is traceability, not acceptance selection. A linked intake must
explicitly choose `--verification-route legacy|scoped`; omitted/conflicting routes
refuse before creating records. `--verification-policy` remains an explicit alias
for scoped. Do not recommend a development-only route when the user requested a
completed delivery without clearly explaining that it cannot reach that endpoint.

- Scoped uses the existing `feature.verification_policy: 1` and schema7. Existing
  scoped work does not fall back to legacy; do not edit/remove its marker to close.
- Guarded legacy planning uses `feature.verification_policy: 2`. This is a route
  discriminator, **not acceptance contract2 or execution contract2**. It keeps the
  same reviewed effect plan, background/negative obligations and effective rules
  but uses existing schema1–5 facts, stamps and full current-work final review.
  It does not gain schema7 judgment/reuse guarantees. Old policy readers reject
  marker2. Do not migrate retained/composite records just to use this route.

Before creating a linked item, inspect prospective readiness without writes:
`verification_policy.py <PROJECT> <NEW-ID> --inspect-route legacy|scoped --parent <PARENT-ID>`.
The parent argument is a prospective relationship hint, not proof of parent
delivery; creation still verifies the exact committed parent and delivered SHA.
For an existing item inspect the actual route; a conflicting requested route
refuses. Readiness reports actual execution/verification formats, project-wide
participant and missing-selection inventory, uncommitted/composite originals,
unknown host capability/authority and the execution/registration entry. It is
structural guidance, not semantic approval, host attestation or a migration.
Only a scoped route still needing preparation inventories other active features.
Legacy and already-prepared routes inspect their own inputs, not every unrelated
record; unavailable unrelated records do not become legacy route blockers.
Resolve genuine missing authority once; reuse authorization already covering
the operation. No business testing is needed to inspect this.

Use `verification.py run <PROJECT> <ID>` for selected checks needing acceptance
registration. In legacy execution, direct `project.py check` is diagnostic and
cannot later be adopted as a gate result; do not run it first when the same suite
must be registered. With execution2, a direct check records an attempt but still
needs actual assertion mapping. Never repeat just for a stage transition.
Unprepared scoped work refuses ordinary develop/final-gate execution before
commands; explicit development diagnostics remain separate facts and do not
grant delivery credit. Preparation/status commands never grant test permission.

Scoped preparation remains explicit: inspect project-level execution-contract2
participants and hosts, preserve originals, and obtain any genuinely missing
preparation authority once. With `feature.verification_policy: 1`, acceptance
prepare creates **schema7 / acceptance_contract1** and requires each host to attest
`schema6_capable: true` and `verification_policy_capable: true`. Older readers
reject schema7. Existing schema1–6 projects are not migrated; active composite
carry/scope sources are not force-converted. Do not offer schema5 preparation as
an equivalent escape route for a scoped increment. A temporary legacy list can
be planned/executed, but cannot certify scoped delivery without schema7.

## Select by effect, combine and deduplicate

Classify each actual change unit, not the entire historical feature:

| Category | Boundary | Required layer |
|---|---|---|
| A | Non-runtime content; no build or acceptance-meaning change | Content/link/format inspection |
| B | Local presentation, no behavior change | Target display, wrapping/clipping, adjacent layout and relevant states |
| C | Shared presentation, behavior unchanged | B plus affected distinct consumers/layout constraints |
| D | Local validation/state/data/error handling, bounded dependencies | Behavior boundaries/errors and directly related regression |
| E | Shared/cross-page behavior, contracts, persistent data/execution | Dependency-scoped integration/compatibility and needed end-to-end behavior |
| U | Unknown effect, dependency or identity | Targeted investigation; do not default to every suite or silently preserve a pass |

Risk tags strengthen only the actually affected scope: funds, security,
permission, privacy, language, font, accessibility, device, compatibility,
migration. A payment page name does not turn an icon edit into payment testing.
A currency/unit, action meaning or click/semantic change may not be presentation.
Classify provisionally before implementation and confirm against final diffs,
references/consumers and shared effects. Evidence may justify narrowing as well
as widening. An omitted dependency is unknown, not “unaffected.”

Use the union of unit checks plus interaction checks, removing duplicate physical
execution. Shared paths/claims require an explicit interaction assessment; other
real couplings must also be investigated. Do not invent all-device/language/font
matrices or new product promises. Pure-display behavior/integration checks need
an applicable project rule (`source: policy:<RULE-ID>`) or a justified behavior
unit. Read actual assertions: mapping a suite to DISPLAY does not make its
unrelated tests relevant.

Store one `verification_plan` inside existing `impact.json`; no second test ledger:

- `schema_version: 1`, `environment`, `operations` (all actual side effects such
  as test/build/device), `units`, `checks`, `interactions`, `background`, `prior_findings`,
  `gate_map`, `overlap_reasons`, `policy_digest`.
- Unit: `id`, `category`, `paths`, `claims` (`R-1:1` or `B-1`), `sharing`
  (local/shared/unknown), `effects`, `reason`, `evidence`, `tags`.
- Check: `id`, `units`, `claims`, `kind` (static/resource/build/display/behavior/
  integration/accessibility/compatibility), `reason`, `source`.
- Interaction: two `units`, `effect` (independent/interacting/unknown),
  `check_ids`, `evidence`; an interaction needs a check covering both units.
- Background group: `paths`, `effect` (unaffected/affected/unknown), `claims`,
  `evidence`. Partition the captured background once, without copying old claims.
- `gate_map` maps exactly the selected gate names to check IDs. Identical physical commands must execute once. Overlapping different suites require both gates to be effective project obligations plus an evidenced unavoidable constraint in `overlap_reasons`, keyed `gate-a|gate-b` (sorted).

See `verification_policy.py` for supported effect/tag enums and validation.
Unknown/missing plans block the scoped boundary; they do not trigger a new suite.
The executor validates before commands and when checking current attempts. This
is not per-gate caching or mixing passes from multiple attempts. Existing whole
input identity can still expire an execution. Keep focused diagnosis separate
from the applicable final run; retain a safe owned environment rather than
recreating it at each stage. Never weaken a required assertion to fit a category.

## Reuse judgments without a second deep review

Schema7 uses the same single resolver/event judgment chain as schema6. Inspect
complete changes once; partition every current claim into assess/reuse/pending,
with grouped exclusion evidence for reuse. Final composition checks currentness,
coverage and the original delivery controls, not a second full claim review.

For an existing schema5 project, `claim_review.py capture` exposes `review_work`:
current supported applicability references versus claims needing assessment.
The independent final reviewer can inspect and cite a current prior finding with
`applicability_ref` (exact provided ref), check contradictions, coverage and full
composition; it need not redo the same complete Git investigation. Every claim
still needs a final finding. Stale/negative/partial/unadopted findings are not
reusable. This is a reference to the existing judgment, not a new automatic pass
or a backport of schema7. New evidence or an actual contradiction warrants deeper
inspection. Never rerun a test merely to hand it from Test to Verify.

## State and publication observations

Use `feature.status` for product status. Free `status_note` may contain conditions
and **remains a semantic input**; do not strip or rewrite it to preserve green.
For a publication update use `delivery_metadata.py <PROJECT> <ID> --revision
<FULL-SHA> --tracking-ref refs/remotes/<REMOTE>/<BRANCH>`. This records only typed
commit/ref/time facts in `delivery-metadata.json`, outside applicability meaning.
It neither fetches/pushes nor certifies today's remote state or acceptance.
Unknown fields/free prose are rejected. Status reads label it a historical local
tracking observation. Original reports/notes stay historical with accurate scope;
semantic corrections still follow normal review. Do not reopen business checks
just to state a publication observation.

Pure A housekeeping may use existing content-only handling when no feature-level delivery is requested; do not create a feature or business gate just for a comment. For explicit feature certification with no applicable executable command, report the current execution-contract preparation limitation instead of inventing checks or claiming an empty execution passed.
