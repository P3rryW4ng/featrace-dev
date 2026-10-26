# Current-task contract5 candidate: authorization and selected inputs

2026-10-26. User approved the local failure-lifecycle replacement. Contract3 was released as0.26.0/0.27.0; contract4 is released as0.28.0; the approved contract5 candidate adds scoped authorization and selected input roles, not yet released; actual publication/install verification is separate and no project migration is implied. This contract supersedes the A109 record-format details and the 0.25.0 predecessor-compatibility route, while retaining current-task ownership and finite lifecycle.

## Authority and proof

Product intent/sources, causal impact, raw facts and sufficiency judgments are separate. A criterion declares `id,expected,kind,inputs,proof` with optional `sources,validity`. Kind is changed/unaffected, not an evidence gate. Proof is `{any_of:[[static_analysis|runtime_observation|command]],reason}`: one justified alternative must be satisfied in full. Declared shape/type coverage does not prove semantic sufficiency. Agent/reviewer must actually inspect assertions, causal arguments and relevant sources.

Static proof may support a changed structural invariant; new rendering/device effects/live external outcomes require their corresponding observation. A command result certifies invocation/status, not nested test execution. No universal command parser or mandatory full-suite fallback. Composite promises use multiple selected facts, or split only when independently different dependencies/proof/freshness/verdicts justify it. A limitation cannot silently erase an unfulfilled promise.

## One canonical fact map

`facts:{ID:record}` stores each fact once. `observations:{criterion:ID}` and `executions:{check:ID}` are latest pointers. Each assessment explicitly selects actual supporting IDs, not every candidate. Older sources can remain selected when unchanged/applicable; supplemental unselected facts do not stale valid assessments. Independent provenance binds exactly that selected set.

Observation: ID/kind/criterion/status, original observed_at, registration at, actual result/scope, input digest, actual target and evidence identities. Optional producer links an original command result, after checking coverage, identity/artifact and result time within its original execution window. A later cached invocation cannot be relabeled the producer of an old XML. Missing historical data is not reconstructed.

Command: ID/kind/check/status, purpose/input digest/check-definition digest/environment, actual producer, original started_at/at, start HEAD, exit status and log identity. Necessary negative/prior references are IDs. Raw stdout/argv/environment values are not copied into a separate event ledger.

Facts are append-only through normal registration; assessment may change explicitly. Real runtime failures have independent retained references. Unavailable/static evidence, relabeling, selecting another success or dropping a criterion cannot clear them. Registering a pass never resolves failures. Each failed runtime fact stays pending until explicit resolution identifies current passing runtime evidence under the same declared necessary conditions, not earlier than that failure. Multiple failures require separate disposition. Missing conditions require clarification from original evidence, without rewriting its fact/time. Reopen corrects a wrong resolution without manufacturing another runtime execution. Latest failed/unavailable selected checks still block closure even when an older success survives.

## Execution protocol

`task_execution.py` owns process execution, bounded metadata and protocol calculation. Identity still binds actual command/input membership/bytes/toolchain/environment/constraints/policy and intact outputs. Execution protocol binds the actual execution module, collector, policy, and reachable workflow execution functions/constants using location-free AST identities. Full workflow file hash is producer provenance, not itself a reuse veto.

This removes query/presentation-only whole-workflow invalidation, without accepting an arbitrary declared version. Changing relevant helpers, actual protocol/module bytes or inputs invalidates accordingly. Whole execution/input/policy modules remain conservative boundaries; this is not general semantic equivalence, signed provenance, dynamic dependency discovery or a promise that every harmless execution-module edit reuses results. No persistent scan cache or per-release predecessor table.

Log starts with the exact runner ownership line, then input format/digest, attempt/check, start time, producer and definition digest. A bounded result footer records outcome/end time; external task metadata stores the final log hash, avoiding self-reference. Original metadata can be recovered from a surviving log, but the tool does not automatically import orphan logs or turn startup into success. Actual command output still needs privacy handling. Capacity is reserved before running; caught interruptions/identity errors are unavailable. Disk failure/SIGKILL transaction recovery remains unguaranteed.

## Readers, correction and limits

Plan, observe, run, assess, status, detail, review-input, correct, close, prune and cleanup candidate readers use contract5. Old formats1/2/3/4 refuse without writes; no fallback writer/importer or fixed0.24 producer bridge remains. Old contract4 tasks use fixed0.28.0; old contract3 tasks use fixed0.27.0 or their applicable original tool; earlier tasks retain their own original tool. A new ID cannot hide old failure. No business data is modified by installation/development.

Bounded correct preserves prior receipts and selected original judgments/fact references, enters correcting and clears only selected assessments. Affected claims cannot disappear. Reclose links the original receipt; at most8 corrections, no correction after source compaction. All failure/permission/privacy/freshness protections remain. New records cannot be downgraded to old readers; rollback means use the fixed tool for its own data, not delete facts/change schema tags.

Limits:128 retained facts and256KiB per task,64 criteria/32 checks,512 exact inputs/list,32 attachments,16MiB/file and64MiB artifacts/task; original transient input/POSIX lock/query limits remain. Numbers are independent refusal bounds, not guaranteed simultaneous capacity. Prune previews and explicitly removes only unreferenced passing metadata; latest pointers, selected support, producer dependencies, negative/resolution facts and correction roots remain. Files are not removed by prune. Complete/expired owned cleanup may compact/forget according to actual policy and surviving limitation handoff; unfinished/correcting/unknown data remains. Not a permanent history archive.

## Retirement and verification

Retired writers: observations-per-criterion payload replacement; auto-all-candidate assessment; latest-only successful execution metadata; kind=changed blanket static rejection; whole-workflow-source identity veto; format1/2 reader/writer and pinned predecessor bridge. They are replaced, not left behind selectable flags. Five predecessor-only tests retired with that supported behavior; two static tests now assert actual runtime-proof requirements. Other applicable protection tests are ported to IDs and explicit fixture support. No private business fixture is committed.

New counterexamples cover static-vs-runtime requirements, multi-fact/subset adoption, artifact/input/TTL/protocol drift, source/producer attribution, old-format refusal, fresh-process read-only recovery, independent selected proof, metadata privacy, failure preservation, pruning/limits and capacity refusal before execution. Full current-suite evidence and actual size/old-reader probes are indexed in validation. Program results do not certify natural Agent judgment, context compression, Android/Figma outcomes, 50-person concurrency or net savings.

Old daily instructions/designs/reviews that duplicate retired contracts are removed from the current tree; original tracked bytes remain in already-pushed fixed Git `46fa61c`. Runtime instructions and usage describe the current supported contract; MAINTAINER records actual publication and installation. Required long-term intent/constraints and negative knowledge remain in current code/tests/concise policy or fixed evidence, not a parallel old system.

## 2026-10-26候选：review policy is not execution identity

User approved the local replacement after the shared-trigger review. Shared remains an impact category; it no longer alone forces independent assessment. Existing review.independent/reason/criteria expresses the necessary scoped choice. Actual project rules and semantic risk investigation remain the executor responsibility; no automatic natural-language rule engine or risk score is introduced. Required selected reviews still need genuine host provenance and exact supporting facts.

validate_execution_plan and execution_ready retain execution-relevant plan/input/coverage/validity/unknown/constraint validation and normal permission checks. validate_acceptance_plan validates proof and review selection through plan/assessment/status/closure entrypoints. run_check depends on the execution branch, so protocol AST discovery naturally excludes acceptance-only validation without a name/hash exception. Execution validation, wrapper, policy and actual invocation code remain in the closure. Some conservative common criterion metadata remains in execution validation; this is not a universal semantic-equivalence guarantee.

The initial split changes the recorded old protocol identity. Existing active tasks stay on their pinned tool; no predecessor allowance, migration or historic receipt/fact rewrite. Later acceptance-only implementation changes can preserve new-protocol command identity while producer provenance still distinguishes the complete workflow bytes. Published as0.27.0; current identity is in MAINTAINER. The initial split does not migrate old active tasks or certify their prior executions.

## Explicit product exclusion and durable issue context

failure_actions and claim_deferrals store bounded append-only dispositions separately from canonical facts. Resolve/clarify/reopen never erase original failure. Whole-criterion defer --exclude-from-delivery needs actual authority/time, reason and surviving handoff; delaying a still-required promise does not waive it. Assess cannot call a deferred claim supported. Reopen-claim restores its obligation; new negatives or mismatched criterion/context invalidate prior deferral. Complete scoped receipts declare supported count, exclusions and unresolved IDs.

Handoff preserves the exact compact failure summary exposed by paged detail: original actual/target/time, effective conditions and evidence identities, plus expected promise and real reason/authority. This is concise negative knowledge, not permanent logs. Missing handoff blocks cleanup, retained issue references protect prune, and compacted storage still counts unresolved failures. A criterion cannot disappear while carrying pending failure/disposition. Changing expected/kind/condition text is not a repair. See A122 and validation for current implementation evidence.

## Authorized contract5 additions

Standing policy, current scoped approval and prior lawful execution proof are separate. Material rule/source/decision/scope conditions stay in identity; permission/approver metadata do not re-sign facts. Once grants bind exact inputs; explicit task grants cover only the selected action/paths/environment and correction lifecycle. New invocation needs applicable permission. A reservation and grant consumption persist atomically before launch; unknown outcome stays unavailable. Bound active grants at16; used-once/expired slots retire while command facts retain original proof. This cannot authenticate fabricated approval or override host controls.

Selected immutable inputs reuse attachment ownership with input/evidence roles and origin metadata. Checks input_assets and criteria source_assets bind IDs/bytes. Raw control state is excluded consistently through local and external paths; full dynamic dependency discovery is out of scope. Explicit prune preserves live/negative/correction asset references and removes only unused input copies. Complete retention preserves external originals and issue handoffs. New protocol/modules bind actual behavior; old tasks stay pinned, never migrated.
