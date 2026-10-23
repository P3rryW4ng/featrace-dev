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

`review:{independent:bool,reason,criteria:[IDs]}` selects actual shared/high-risk or project-required claims; omit unrelated claims. An absent selection with independent true conservatively applies task-wide. Shared changes require independent review but do not force all other criteria into it. Unknown host capability is not permission to invent provenance.

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

status/list/storage/locate/code/detail/review-input are read-only and do not run checks. Use previews/cursors; detail sections request/plan/receipt/limitations/criterion/facts/fact/corrections recover selected content. Output is capped at16KiB rather than silently claiming a truncated source complete. Recover current intent, selected facts and failures after context loss, not every historical receipt.

`correct ROOT ID --affected C --reason "specific error" --authority "real scoped approval"` works only on a retained complete contract3 task. It preserves original receipts, selected old judgments and fact references; clears only affected assessments; cannot remove affected criteria/failures or clean an open correction. Reclose links the original receipt. At most8 corrections; compacted/forgotten sources refuse. Old format1/2 needs its pinned old tool, without new-package migration or compatibility bridges.

`prune ROOT ID` previews the count of removable unreferenced passing metadata; `--apply` removes only that metadata. Latest pointers, chosen support, producer dependencies, original negative/resolution evidence and correction roots remain. It never deletes evidence files, which remain owned until normal retention. This is explicit bounded current-fact management, not a permanent event archive or automatic failure cleanup.

`close ROOT ID --limitation TEXT` requires necessary checks, explicit sufficient assessments, related reviews and no unresolved failures/unknowns. It produces an as-of receipt, not perpetual HEAD certification. No registration rerun or full-history report review. Place enduring intent, regression protection and limitations in code/tests/adjacent comments or existing concise project records. Do not confuse local commit, complete, merge readiness, push or publication.

Completed coherent subtasks are locally committed after necessary checks and selected-output privacy review under actual authorization, before whole-task closure. Preserve other changes/index entries; no blanket add/reset/amend, automatic push or HEAD-only retest. Failed or inseparable broken work is not a completed subtask. Actual no-commit/project rules still apply. Report the subtask commit through native progress or ordinary concise prose, not another ledger.

Policy-confirmed seven-calendar-day cleanup runs opportunistically at begin/close or explicit maintain with bounded rotating selection, not a personal daemon. cleanup previews; --apply compacts eligible complete tasks, --forget removes the task only after required surviving limitation handoff. It deletes only exact owned UUID logs and intact registered copies; unknown/modified files, links, incomplete/correcting work and unhanded limits remain. External originals, business ledgers, code and Git are not removed. Expired evidence is not automatically reconstructable.

Limits:256KiB task,128 retained facts,64 criteria,32 checks,512 exact paths/list,32 attachments,16MiB/file and64MiB/task artifacts; transient execution collection250000 entries/32GiB. These are refusal bounds, not a claim every combination fits. Query/storage are bounded/paged; stale incomplete data is visible, not silently deleted. POSIX/local locks only; dynamic dependencies, semantic judgment, remote changes and natural Agent recovery remain empirical limits.
