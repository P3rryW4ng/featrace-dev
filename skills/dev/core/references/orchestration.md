# Staged orchestration contract

Use this contract for feature mutations and `/dev next`. It keeps one user entry while loading only the rules needed for the current stage. It does not create another state machine or another canonical record.

## Router boundary

The router may read the selected feature identity, `feature-status.py` output, unresolved decisions/fixes, source freshness, task state, impact state, verification state and the user's current request. It chooses one stage or an explicit short chain, announces that route, then loads only that stage's required references plus any direct prerequisite named below.

The router must not reread every source, code file and test result merely to choose a stage. It must not summarize its way around a failed gate. `help`, `list`, `status` and delivery-mode activation remain read-only and do not require a stage handoff.

The stage view is a read strategy over existing canonical records, not a second store. Requirement reads sources and requirement authority; Scope reads module/code evidence, impact and task meaning; Build starts from its assigned task and preserved behavior; Verify can expand across tasks and consumers; Repair starts from the mismatch and failed evidence; Deliver reads current verification and all unresolved closure conditions. Do not preload all feature records for every stage. A narrow view must expose missing or ambiguous linkage and permit evidence-backed expansion; it cannot silently treat omitted material as irrelevant.

## Capability contracts

| Stage | Enter when | Required input | Required output and exit condition | Load on demand |
|---|---|---|---|---|
| Requirement | A feature is created, source evidence arrives, or confirmed meaning changes | Product ID, accessible sources, current baseline and decisions | Immutable source registration; reviewed requirements or explicit reading/decision blockers; affected meaning identified | `prd-analysis.md`, `requirement-schema.md`, and for changes `revision-workflow.md` or `clarify-workflow.md` |
| Scope | Requirement meaning is reviewable and implementation scope must be established or refreshed | Confirmed/inferred requirements, project baseline, module catalog, related code and history | Capability/module roles, impact boundary, tasks, historical-fix candidates, unknowns and develop eligibility | `module-context.md`, `impact-review.md`, `task-semantic-review.md`, `historical-regression.md`; `project-baseline.md` only for full scan or verification |
| Build | An eligible task slice is authorized for implementation | Reviewed task meaning, allowed paths/behaviors, preserved behaviors, project conventions and planned checks | Code for one independently testable slice; actual changed scope; task/traceability evidence; focused checks and a scoped local task commit when eligible, without a feature-completion claim | `workflow.md`, `build-strategy.md`, project profile, plus already selected Scope constraints; `task-commit.md` only at task handoff |
| Verify | Implementation or repair needs independent assessment | Current requirements, decisions, diff, impact/historical checks, executable gates and manual scenarios | Actual automated results, remaining manual evidence, failures and tested revision; delivery eligibility only when all applicable evidence is current | `verification-workflow.md`, `impact-review.md`, `historical-regression.md`, `project-baseline.md` for quality selection |
| Repair | A mismatch or failed check exists | Expected and actual behavior, reproduction/evidence, current requirement authority, relevant code and failed verification | Classified cause or explicit unknown; repair/reconciliation; regression coverage; return to Verify | `fix-workflow.md`, then only the Requirement or Scope reference required by the cause |
| Deliver | Verify has current results after an authorized implementation/check continuation, or the user explicitly requests closure | Current code revision, requirements/tasks/decisions/fixes, verification and source reconciliation | Feature-local `delivery-report.md` write succeeds, a separate full read succeeds and returns to the Agent, then evidence comparison succeeds before a separate complete mutation; optional authorized commit/PR/archive remain separate; unresolved limits remain visible | `verification-workflow.md`, and `feature-archive.md` only for archive/restore |

At Scope exit, state each task's implementation owner and actual artifact: local code, externally owned configuration, or a mixed/unknown slice that needs more investigation. This is an evidence-backed routing judgment, not a new JSON status. For external configuration, load `external-configuration.md` and show the zero-local-code conclusion before Build. Route only local code slices to Build; an external handoff returns to Verify once the configuration has actually been applied. If ownership or client compatibility is uncertain, keep Scope open.

`scan` is project preparation used by Scope, not a seventh feature stage. `api` and `figma` provide Requirement evidence. `clarify` and `revise` change or confirm Requirement authority. `fix` enters Repair. `check` enters Verify and continues to Deliver when eligible unless the request is explicitly check-only or read-only. `archive` is an optional evidence-gated history action after delivery; `restore` and legacy label classification are lifecycle actions under `feature-archive.md`, not fresh Verify runs.

The router owns local task commits after Build, one completed separable task at a time. Load `task-commit.md` at that handoff, not during read-only routing or for every Worker. A commit records a finished implementation slice; it does not replace Verify, trigger full quality gates by itself, or imply remote publication. If the task cannot be isolated from existing or peer changes, preserve the scene and report why the automatic commit stopped.

After the final active task reaches `done` in an authorized development continuation, the router proceeds to Verify and eligible Deliver without asking the user to type `check` or `complete`. This is a separate stage transition after task commit, not a task-commit side effect. Run actual selected checks once for the final code state, reconcile manual and historical evidence, and stop at the first genuine blocker with `provisional` and the exact remaining observation or decision. Resume that same Verify → Deliver chain when the user supplies the missing evidence; do not require a new command choice. A read-only status question, activation, planning-only/no-execution request or unsupported final evidence does not authorize this mutation.

## Handoff envelope

Before moving between stages, make the handoff recoverable from canonical project records. The concise stage result must identify:

- feature ID and stage result (`ready`, `blocked`, `failed`, or `complete_for_stage`);
- input identity or digest when the existing workflow provides one;
- confirmed facts and unresolved decisions, without replacing their canonical records;
- artifacts changed and evidence references;
- permitted write roots/output paths and the selected scratch location, following `write-scope.md` before any temporary writes;
- allowed next stage or stages;
- blockers and the exact human input, permission or environment change needed.

Write facts to the existing requirement, task, decision, impact, fix, verification, delivery or module records that own them. Do not create a second canonical handoff JSON, duplicate full source text, or treat a chat summary as authority. The optional independent reviewer uses only a disposable scratch input manifest, never a new project state. A downstream stage must reject stale inputs using existing digests and validators rather than trusting prose.

## Loading and isolation policy

This release uses the same Agent with progressive disclosure. Load the orchestration contract first, then only the chosen stage references. A chained route loads the next stage only after the previous exit condition is met. Do not preload every reference "for safety"; load a direct dependency when a real condition activates it.

Independent Verify is opt-in under `independent-verify.md`: a fresh, read-only reviewer loads `specialists/featrace-verify/SKILL.md`, returns evidence, and the router reconciles it. Ordinary check remains unchanged; unsupported hosts report unavailable. A Build pair chosen under `build-strategy.md` requires the same Scope exit first (workflow, impact, task semantics and historical review), plus current task/history review records; read-only missing reviews block instead of exploiting legacy warnings. It is available under `parallel-build.md`, using the bundled `specialists/featrace-build/SKILL.md`, separate detached worktrees and a tested external integration candidate. It never writes canonical records or promotes code by itself. Authorized Build now chooses conservatively between serial and one independent pair; user-forced serial takes precedence. No general scheduler, arbitrary worker count or automatic waves are enabled. Expand only after measuring omissions, false assumptions, handoff loss, interventions, time and token cost against the same-stage baseline.

Specialist messages use the same short `Status / Outcome / Checks or Evidence / Risk or Gaps / Next` shape defined in their own SKILL.md. These messages are navigation aids, not a new record or acceptance proof. The router must inspect the complete structured return and cited artifacts, resolve contradictions and stale inputs, then give the user one concise integrated update in their language: current state, material result or blocker, evidence level and next action. Do not forward every worker's full narrative, raw JSON or repeated logs. If a significant finding cannot fit in the short update, link its exact artifact rather than silently dropping it; the host may still show tool transcripts outside the router's control.

For the independent Build pair, the router passes task identity and frozen input location, not all records inline. After preflight, each worker calls `parallel-build.py task-view` to obtain only its assigned task projection, then reads original evidence when needed. Independent Verify already starts with `verify-inputs.py` and a bound snapshot; it must still search relevant consumers beyond the starting file list. These are context-management aids, not file-system access controls or semantic completeness guarantees.

## Stop and return rules

Stop the current stage when product authority is required, evidence cannot be accessed, permission is missing, a deterministic gate fails, or only a person can perform the remaining observation. Continue independent authorized work that is outside the blocker. Report the stage result, saved evidence, one focused blocker and the next eligible action.

Never call a stage complete because its document exists. Requirement needs semantic review, Scope needs evidence-backed boundaries, Build needs actual code and tests appropriate to the slice, Verify needs executed evidence, Repair needs regression protection or an explicit waiver, and Deliver needs evidence current for the delivered revision.
