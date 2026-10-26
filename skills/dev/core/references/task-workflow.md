# Current tasks: claims, facts and scoped execution

Read this for authorized development. One bounded current task; no feature ledger, permanent replay, project schema preparation or automatic old-record migration. Contract3 is for new tasks. Format1/2 and `.agent-workflow` work use their fixed old tool; do not change IDs or formats to hide failures.

## Project and intent

Inspect actual project rules/hooks and current same-scope grants. Read project-compatibility before the first affected operation. `policy ROOT --json FILE` prepares one `.featrace-policy.json` and a narrow ignore block for local `.featrace`. It is an authorized edit, not a permission-granting flag. Existing tracked data, unowned policy or custom ignore conflicts refuse. Source changes require reconciliation; higher-priority host permissions and hooks still apply.

Policy shape remains `{policy_contract:1,authority,timezone,retention_days,cleanup:manual|compact|forget,handoff:null|path,rules:[]}`. Each rule has source/sha256, paths, operations, environment, decision, permission and real authority. See project-compatibility for actual conflict resolution. An empty rules list records reviewed absence, not proof no injected rules exist.

`begin ROOT ID --request "original intent"` creates a new task only for requested work. Activation/help/status do not initialize projects. Read real source contents, relevant code/callers/configuration/tests and design. Code and hashes cannot define product intent by themselves.

## Plan causal scope and proof

`plan ROOT ID --json FILE` requires reason, categories, scope, exclusions, constraints, unknowns, criteria, checks and review. Categories combine presentation/interaction/state/interface/shared/device/configuration; they do not automatically authorize a maximal suite or establish safe local scope. Compiler inputs may be broader than behavioral effects.

- `scope`: owned relevant code/test paths. Exclusions are optional actual no-impact explanations, not an inventory of every branch change.
- `constraints`: source path to `{decision,criteria:[IDs],checks:[IDs]}` for local rules; a string explicitly applies task-wide. Neither actual scope nor authorization may be silently narrowed.
- `unknowns`: `{reason,criteria:[IDs],checks:[IDs]}` for local gaps, or text for genuine task-wide uncertainty. They block relevant work and always block closure; independent work can continue. `run --investigate` permits authorized investigation, not bypassing permissions/source drift.
- Each criterion: `{id,expected,kind:changed|unaffected,inputs:[paths],proof:{any_of:[[kinds]],reason},sources?:[paths],validity?:{...}}`.

The impact label and proof are independent. `proof.any_of` lists sufficient combinations; kinds within one combination are all required. Kinds are `static_analysis`, `runtime_observation`, `command`. Example: `[["static_analysis"]]` for a fully inspected structural invariant; `[["runtime_observation"]]` for actual rendered UI; `[["static_analysis","runtime_observation"]]` when both are needed. Alternatives describe justified evidence paths, not a ranking or permission to choose an easier unsupported one. A command fact proves its invocation/outcome, not automatically that nested tests physically ran or business assertions covered the criterion.

Split promises only when they need independently different dependencies, proof, freshness or verdicts. A composite promise can use multiple necessary facts; do not make one row per pixel/statement. State actual proof coverage and assumptions. New rendering, device effects and live external responses need corresponding observation; sufficient static causal proof need not be followed by a redundant runtime test. The kernel checks declared relationships, not whether the selected proof requirement or investigation is semantically correct.

`shared` describes actual propagation, not an independent-review requirement. Inspect real consumers and public compatibility commitments: a common filename, directory, multiple tests or hypothetical future reuse is not enough. An exported API can have external consumers absent from local search. State the causal path and relevant variants in the existing plan reason; unresolved dynamic use is a scoped unknown, not proof of no impact or a reason to reaccept every business flow. Shared rendering calls for affected rendering coverage; it does not automatically call for unrelated logic tests.

Choose `review:{independent:bool,reason,criteria:[IDs]}` separately. Explain whether a second context adds a necessary check: require it for applicable explicit project/user rules, serious funds/authorization/data-loss or public-contract risks, or complex propagation/meaningful blind spots that warrant an independent perspective. A single caller may still be high risk. Low-risk private or shared presentation/simple mapping with bounded effects and sufficient inspected evidence may use self-assessment when no rule requires otherwise. Do not infer safety merely from line count, a UI label, passing tests or a small caller count. Missing runtime evidence, credentials or product authority needs its own resolution; a reviewer cannot replace them.

Select explicit relevant criteria in new plans (`[]` when no independent review); omit unrelated claims. Existing plans with independent true and no selection retain their conservative task-wide meaning. Honor concrete project requirements and existing decisions; do not remove a label, requirement or promised review to bypass a failure or silently waive an obligation. If a requirement genuinely changes, reconcile its actual authority and only the affected judgments. The kernel checks declared scope/provenance, not completeness of caller discovery or whether the semantic review decision obeyed a natural-language project rule. Unknown host capability is not permission to invent provenance.

Execution validation retains input/scope, environment, cache, constraints, authorization and unknown checks. Acceptance proof/review-policy validation is separate; it is not a command authorization gate. A review-only implementation change is outside the new execution protocol closure; the producer still records the original complete workflow hash. Actual execution-validation changes still invalidate checks. The initial separation changes the old protocol: retain active old tasks on their pinned tool; no automatic migration, predecessor hash allowance or re-signing of old facts is provided.

## Handle a new instruction by its actual delta

Before acting on a material new instruction, compare it with the current accepted intent and actual code. Identify whether it adds a promise, clarifies the same promise, changes an agreed outcome, or corrects the Agent's earlier interpretation. These are reasoning distinctions, not new required labels or an approval questionnaire. Mixed instructions may affect different claims differently. Ask only when the product meaning or authority is genuinely unresolved; reuse applicable authorization for execution.

Preserve the original request. Update only affected criteria.expected/proof/inputs/sources and their necessary checks; use plan.reason briefly for the current decision, its real authority and affected IDs. Existing sources should identify actual authoritative material; remote/chat authority can be identified honestly in existing text without inventing a source file. Keep unrelated plan entries and original fact IDs/times. Reassess affected judgments; rerun a physical check only when its real inputs, validity or required coverage demand it. If code already satisfies the clarified requirement, implementation may be unnecessary. A correction to a completed retained task uses correct; genuinely additional work may be a separately agreed scoped task, without concealing the original failure.

Do not redefine an observed failure as a clarification, silently exclude an unmet promise, or create another ID to bypass it. A real product withdrawal that conflicts with retained failure protections must be surfaced as a contract boundary for an explicit supported decision, not fabricated as a successful runtime resolution. No automatic withdrawal or migration route is provided. The kernel validates declared relationships, not whether the new instruction was interpreted correctly.

## Checks and execution identity

Each check declares `{id,argv,inputs,covers,reason,timeout,environment}`. It may include input_sets, external_inputs, env_keys, cache and operation. Inspect real assertions and mandatory project gates; deduplicate commands. `covers` is a proposed causal mapping, not proof from a test name.

`input_sets:[{kind:file|tree|git_tree,path}]` fingerprints selected actual members/bytes transiently. git_tree includes tracked and nonignored untracked sources; tree also includes ignored contents. Include real dependencies/configuration and ignored sources when needed; exclude output/cache trees unless intentionally tested. Managed internal links are accepted only under the input collector's actual restrictions. External file/tree roots declare real toolchain/dependencies. Environment values are hashed, not copied to records. This does not discover every dynamic/compiler/native/remote input.

Environment needs `{kind:local|test|remote|device|production,target:"actual identity"}`; device/remote also require policy_environment. `cache:{mode:content|never,max_age_seconds?}`: mutable device/remote/production checks require never and a positive bound at most86400. Another run then physically invokes again; a prior applicable result may still support its original observation interval. Actual grants are checked before reuse. No shared hermetic cache or automatic device driver is promised.

`run ROOT ID --check NAME` performs only necessary execution or returns the same applicable original attempt. Actual argv, input members/bytes, executable/toolchain/environment, selected constraints/policy and execution protocol determine identity. Execution implementation/collector/policy plus reachable workflow execution helpers bind the protocol. Query/presentation-only workflow changes do not invalidate executions; real relevant code/constant changes do. The producer's full workflow hash remains provenance. There is no per-release predecessor allowlist or caller-provided protocol label; unknown/changed implementation affects the computed protocol. This is local identity checking, not signed remote-origin attestation or proof a dynamic dependency set is complete.

The log has bounded start/result metadata with original attempt/input/protocol/producer/time and command status. It excludes raw environment values/argv from the header; actual command output still needs privacy handling. Caught interruptions, identity drift, timeouts, output limits or unavailable results do not leave the earlier success as the latest result. A capacity reservation occurs before execution. Disk failures/SIGKILL are not guaranteed recoverable transactions.

## Preserve and select facts

The task has one fact map keyed by immutable IDs. Latest observation/check maps are pointers, not the only surviving fact. Retained old successes can be selected when still applicable; newer failed/unavailable checks and unresolved runtime failures remain blocking. Reuse never rewrites an original time, target or input digest.

`attach ROOT ID --file SOURCE` registers an owned evidence copy, at most32 files,16MiB each within64MiB/task. Originals are never deleted. Use returned paths in observations; do not leave scratch as a substitute for managed retention.

```
observe ROOT ID --criterion C --kind static_analysis --observed-at ISO --actual "inspected causal proof and assumptions" --evidence PATH
observe ROOT ID --criterion C --kind runtime_observation --target "actual artifact/device/environment" --observed-at ISO --actual "actual result and scope" --evidence PATH
```

Use `--status failed|unavailable` honestly. No pre-task/future observation time or missing runtime target. Registration HEAD is not installed-build identity. All observations remain separately addressable; a later success path does not erase an earlier negative. Runtime failures cannot be cleared by static/unavailable facts, editing proof or removing references. Only a newer applicable targeted runtime pass resolves the corresponding failure and retains its reference; semantic relevance still requires real judgment.

Optional `--producer ATTEMPT_ID` ties an observed result artifact to a retained successful current command: check mapping/inputs/output must match and actual observed result-production time must fall in that attempt's window. For reused Gradle XML, cite its original producer and original time. A later UP-TO-DATE invocation cannot become the old result's producer. This check cannot establish an XML's truth or manufacture missing metadata; inspect actual artifacts. Device observations without a command producer still require their real artifact/target basis.

`review-input ROOT ID --criterion C` gives candidates, current selected IDs, proof requirements, digest, failure and detail routes. Candidates are not automatically adopted. Use `detail --section fact --criterion FACT_ID` for one exact original source and follow pagination.

```
assess ROOT ID --criterion C --verdict supported --fact FACT_A --fact FACT_B --reason "which promises each fact supports, assumptions and limits"
```

Supported requires explicit nonempty applicable IDs satisfying a declared proof combination. Adding unselected supporting facts does not stale the selected judgment. Changing relevant intent/inputs/review requirements, selected evidence or actual applicability does. Partial/unknown must name the unsupported promise/causal step and minimal missing evidence; do not demand runtime merely because none occurred. Limitations are not silent exclusions. Missing automated regression assets are distinct from adequate current delivery evidence; mandatory project gates remain mandatory.

Independent assessment also uses `--independent --provenance PATH`. A real fresh-context return binds task, criterion, criterion_digest, the explicitly selected facts, verdict, fresh_context:true, host, context_id, reviewer and reason. Do not manufacture host identity. Scope independent review to actual necessary claims, not the whole parent PRD. Structural checks do not prove host independence or business sufficiency.

## Query, correct and retain

status/list/storage/locate/code/detail/review-input are read-only and do not run checks. Active-task status keeps SCOPE_NOT_READY as a blocking marker and adds scope_readiness with a known safe cause and detail route; scope readiness alone does not mean delivery eligibility. Unknown exceptions remain generic. Use previews/cursors; detail sections request/plan/receipt/limitations/criterion/facts/fact/corrections recover selected content. Output is capped at16KiB rather than silently claiming a truncated source complete. Recover current intent, selected facts and failures after context loss, not every historical receipt.

### Resume the decision, not just the status

After a conversation/context change, identify the actual task/worktree and loaded installation. Read status first, then the original request, current relevant plan and live applicable rules. Recover the current accepted outcome, important decisions/authority, selected original fact IDs and their applicability, unresolved failures/unknowns, and the next authorized action. Read selected details and pagination only as needed; a preview or remembered checklist is not the full source. Completed status is an as-of receipt, not permission to edit or certification of the present HEAD.

The current plan/assessments already carry decisions and support. When an important decision or an impending handoff cannot be recovered from them, keep a short current outline in plan.reason alongside its causal analysis: current objective, essential decision/source, specific blocker, next action. Update through plan with the rest of its entries preserved. Replace stale outline text rather than append a transcript; do not write after every operation or introduce a separate resume file. If context was lost before such a note, reconstruct from actual code/selected facts or state the missing piece; never invent a handoff or refresh old observation times.

Verify pending work against actual state before acting, especially installed artifacts, mutable targets, applicable permissions and other people's changes. Continue independent authorized work while a scoped blocker remains. Do not rerun checks, reconstruct every past receipt, or ask the user to restate available decisions solely because the context changed. A missing supported source/permission is a concrete blocker; investigate or ask only for that piece. This is a recovery procedure, not automatic context compression or a guarantee of host memory.

`correct ROOT ID --affected C --reason "specific error" --authority "real scoped approval"` works only on a retained complete contract3 task. It preserves original receipts, selected old judgments and fact references; clears only affected assessments; cannot remove affected criteria/failures or clean an open correction. Reclose links the original receipt. At most8 corrections; compacted/forgotten sources refuse. Old format1/2 needs its pinned old tool, without new-package migration or compatibility bridges.

`prune ROOT ID` previews the count of removable unreferenced passing metadata; `--apply` removes only that metadata. Latest pointers, chosen support, producer dependencies, original negative/resolution evidence and correction roots remain. It never deletes evidence files, which remain owned until normal retention. This is explicit bounded current-fact management, not a permanent event archive or automatic failure cleanup.

`close ROOT ID --limitation TEXT` requires necessary checks, explicit sufficient assessments, related reviews and no unresolved failures/unknowns. It produces an as-of receipt, not perpetual HEAD certification. No registration rerun or full-history report review. Place enduring intent, regression protection and limitations in code/tests/adjacent comments or existing concise project records. Do not confuse local commit, complete, merge readiness, push or publication.

### Keep only knowledge future changes actually need

During implementation, decide whether a newly learned constraint would be lost when task-local data expires: a non-obvious repair cause, intentional behavior boundary, dependency precondition or material unresolved limitation. Check whether current code/tests/nearby comments or an existing concise issue already preserve it accurately. If so, cite that location in the ordinary delivery response; do not copy it into another document. Temporary commands, repeated screenshots and reconstructable implementation details need no permanent handoff.

When durable knowledge is missing, prefer a meaningful regression assertion where appropriate, a short adjacent rationale when code cannot explain the choice, or the project's existing concise issue/constraint location for unresolved matters. Choose the smallest sufficient destination; do not require all three, a test for every UI refinement, or a new per-feature archive. Include genuinely necessary changes in the original scope and applicable checks before final evidence; if discovered later, update only affected inputs/checks. Do not expand unrelated work or silently accept a changed product outcome to make handoff easier.

Report the specific surviving location and remaining limitation, or that no new durable knowledge was needed. No extra manifest, permanent feature dossier, mandatory automation gate or universal close field is added. The kernel does not verify whether every important intent has been preserved. Existing cleanup protects recorded limitations under its actual handoff rules; it does not inspect arbitrary code/comments for missing product intent. Do not claim expired evidence can be reconstructed or delete unresolved facts to satisfy storage targets.

Completed coherent subtasks are locally committed after necessary checks and selected-output privacy review under actual authorization, before whole-task closure. Preserve other changes/index entries; no blanket add/reset/amend, automatic push or HEAD-only retest. Failed or inseparable broken work is not a completed subtask. Actual no-commit/project rules still apply. Report the subtask commit through native progress or ordinary concise prose, not another ledger.

Policy-confirmed seven-calendar-day cleanup runs opportunistically at begin/close or explicit maintain with bounded rotating selection, not a personal daemon. cleanup previews; --apply compacts eligible complete tasks, --forget removes the task only after required surviving limitation handoff. It deletes only exact owned UUID logs and intact registered copies; unknown/modified files, links, incomplete/correcting work and unhanded limits remain. External originals, business ledgers, code and Git are not removed. Expired evidence is not automatically reconstructable.

Limits:256KiB task,128 retained facts,64 criteria,32 checks,512 exact paths/list,32 attachments,16MiB/file and64MiB/task artifacts; transient execution collection250000 entries/32GiB. These are refusal bounds, not a claim every combination fits. Query/storage are bounded/paged; stale incomplete data is visible, not silently deleted. POSIX/local locks only; dynamic dependencies, semantic judgment, remote changes and natural Agent recovery remain empirical limits.
