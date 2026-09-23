# Staged orchestration contract

Use this contract for feature mutations and `/dev next`. It keeps one user entry while loading only the rules needed for the current stage. It does not create another state machine or another canonical record.

## Router boundary

The router may read the selected feature identity, `feature-status.py` output, unresolved decisions/fixes, source freshness, task state, impact state, verification state and the user's current request. It chooses one stage or an explicit short chain, announces that route, then loads only that stage's required references plus any direct prerequisite named below.

The router must not reread every source, code file and test result merely to choose a stage. It must not summarize its way around a failed gate. `help`, `list`, `status` and delivery-mode activation remain read-only and do not require a stage handoff.

## Capability contracts

| Stage | Enter when | Required input | Required output and exit condition | Load on demand |
|---|---|---|---|---|
| Requirement | A feature is created, source evidence arrives, or confirmed meaning changes | Product ID, accessible sources, current baseline and decisions | Immutable source registration; reviewed requirements or explicit reading/decision blockers; affected meaning identified | `prd-analysis.md`, `requirement-schema.md`, and for changes `revision-workflow.md` or `clarify-workflow.md` |
| Scope | Requirement meaning is reviewable and implementation scope must be established or refreshed | Confirmed/inferred requirements, project baseline, module catalog, related code and history | Capability/module roles, impact boundary, tasks, historical-fix candidates, unknowns and develop eligibility | `module-context.md`, `impact-review.md`, `task-semantic-review.md`, `historical-regression.md`; `project-baseline.md` only for full scan or verification |
| Build | An eligible task slice is authorized for implementation | Reviewed task meaning, allowed paths/behaviors, preserved behaviors, project conventions and planned checks | Code for one independently testable slice; actual changed scope; task/traceability evidence; no false completion claim | `workflow.md`, project profile, plus already selected Scope constraints |
| Verify | Implementation or repair needs independent assessment | Current requirements, decisions, diff, impact/historical checks, executable gates and manual scenarios | Actual automated results, remaining manual evidence, failures and tested revision; delivery eligibility only when all applicable evidence is current | `verification-workflow.md`, `impact-review.md`, `historical-regression.md`, `project-baseline.md` for quality selection |
| Repair | A mismatch or failed check exists | Expected and actual behavior, reproduction/evidence, current requirement authority, relevant code and failed verification | Classified cause or explicit unknown; repair/reconciliation; regression coverage; return to Verify | `fix-workflow.md`, then only the Requirement or Scope reference required by the cause |
| Deliver | Verify has current results and the user requests delivery/closure | Current code revision, requirements/tasks/decisions/fixes, verification and source reconciliation | Honest delivery report and status; optional authorized commit/PR/archive; unresolved limits remain visible | `verification-workflow.md`, and `feature-archive.md` only for archive/restore |

`scan` is project preparation used by Scope, not a seventh feature stage. `api` and `figma` provide Requirement evidence. `clarify` and `revise` change or confirm Requirement authority. `fix` enters Repair. `check` enters Verify and may continue to Deliver only when requested and eligible. `archive` is an evidence-gated history action after delivery; `restore` and legacy label classification are lifecycle actions under `feature-archive.md`, not fresh Verify runs.

## Handoff envelope

Before moving between stages, make the handoff recoverable from canonical project records. The concise stage result must identify:

- feature ID and stage result (`ready`, `blocked`, `failed`, or `complete_for_stage`);
- input identity or digest when the existing workflow provides one;
- confirmed facts and unresolved decisions, without replacing their canonical records;
- artifacts changed and evidence references;
- allowed next stage or stages;
- blockers and the exact human input, permission or environment change needed.

Write facts to the existing requirement, task, decision, impact, fix, verification, delivery or module records that own them. Do not create a generic handoff JSON, duplicate full source text, or treat a chat summary as authority. A downstream stage must reject stale inputs using existing digests and validators rather than trusting prose.

## Loading and isolation policy

This release uses the same Agent with progressive disclosure. Load the orchestration contract first, then only the chosen stage references. A chained route loads the next stage only after the previous exit condition is met. Do not preload every reference "for safety"; load a direct dependency when a real condition activates it.

Independent Agent/context execution is not enabled by this contract. If later enabled, Verify is the first candidate because a separate reviewer may reduce implementer self-confirmation. It must receive the handoff envelope and read canonical evidence directly. It must not inherit a green conclusion from Build, and its result must still satisfy the same deterministic gates. Expand isolation only after measuring omissions, false assumptions, handoff loss, interventions, time and token cost against this same-stage baseline.

## Stop and return rules

Stop the current stage when product authority is required, evidence cannot be accessed, permission is missing, a deterministic gate fails, or only a person can perform the remaining observation. Continue independent authorized work that is outside the blocker. Report the stage result, saved evidence, one focused blocker and the next eligible action.

Never call a stage complete because its document exists. Requirement needs semantic review, Scope needs evidence-backed boundaries, Build needs actual code and tests appropriate to the slice, Verify needs executed evidence, Repair needs regression protection or an explicit waiver, and Deliver needs evidence current for the delivered revision.
