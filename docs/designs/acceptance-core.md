# Current-task contract3: replacement contract

2026-10-23. User approved re-review and implementation, inheriting useful protections rather than old formats. Released as0.26.0; actual publication/install verification is separate and no project migration is implied. This contract supersedes the A109 record-format details and the 0.25.0 predecessor-compatibility route, while retaining current-task ownership and finite lifecycle.

## Authority and proof

Product intent/sources, causal impact, raw facts and sufficiency judgments are separate. A criterion declares `id,expected,kind,inputs,proof` with optional `sources,validity`. Kind is changed/unaffected, not an evidence gate. Proof is `{any_of:[[static_analysis|runtime_observation|command]],reason}`: one justified alternative must be satisfied in full. Declared shape/type coverage does not prove semantic sufficiency. Agent/reviewer must actually inspect assertions, causal arguments and relevant sources.

Static proof may support a changed structural invariant; new rendering/device effects/live external outcomes require their corresponding observation. A command result certifies invocation/status, not nested test execution. No universal command parser or mandatory full-suite fallback. Composite promises use multiple selected facts, or split only when independently different dependencies/proof/freshness/verdicts justify it. A limitation cannot silently erase an unfulfilled promise.

## One canonical fact map

`facts:{ID:record}` stores each fact once. `observations:{criterion:ID}` and `executions:{check:ID}` are latest pointers. Each assessment explicitly selects actual supporting IDs, not every candidate. Older sources can remain selected when unchanged/applicable; supplemental unselected facts do not stale valid assessments. Independent provenance binds exactly that selected set.

Observation: ID/kind/criterion/status, original observed_at, registration at, actual result/scope, input digest, actual target and evidence identities. Optional producer links an original command result, after checking coverage, identity/artifact and result time within its original execution window. A later cached invocation cannot be relabeled the producer of an old XML. Missing historical data is not reconstructed.

Command: ID/kind/check/status, purpose/input digest/check-definition digest/environment, actual producer, original started_at/at, start HEAD, exit status and log identity. Necessary negative/prior references are IDs. Raw stdout/argv/environment values are not copied into a separate event ledger.

Facts are append-only through normal registration; assessment may change explicitly. Real runtime failures have independent retained references. Unavailable/static evidence, relabeling, selecting another success or dropping a criterion cannot clear them. A newer applicable targeted runtime pass retains the resolved failure reference. Latest failed/unavailable selected checks still block closure even when an older success survives.

## Execution protocol

`task_execution.py` owns process execution, bounded metadata and protocol calculation. Identity still binds actual command/input membership/bytes/toolchain/environment/constraints/policy and intact outputs. Execution protocol binds the actual execution module, collector, policy, and reachable workflow execution functions/constants using location-free AST identities. Full workflow file hash is producer provenance, not itself a reuse veto.

This removes query/presentation-only whole-workflow invalidation, without accepting an arbitrary declared version. Changing relevant helpers, actual protocol/module bytes or inputs invalidates accordingly. Whole execution/input/policy modules remain conservative boundaries; this is not general semantic equivalence, signed provenance, dynamic dependency discovery or a promise that every harmless execution-module edit reuses results. No persistent scan cache or per-release predecessor table.

Log starts with the exact runner ownership line, then input format/digest, attempt/check, start time, producer and definition digest. A bounded result footer records outcome/end time; external task metadata stores the final log hash, avoiding self-reference. Original metadata can be recovered from a surviving log, but the tool does not automatically import orphan logs or turn startup into success. Actual command output still needs privacy handling. Capacity is reserved before running; caught interruptions/identity errors are unavailable. Disk failure/SIGKILL transaction recovery remains unguaranteed.

## Readers, correction and limits

Plan, observe, run, assess, status, detail, review-input, correct, close, prune and cleanup all use contract3. Old formats1/2 refuse without writes; no fallback writer/importer or fixed0.24 producer bridge remains. Old tasks use fixed0.25.0 or their applicable original tool. A new ID cannot hide old failure. No business data is modified by installation/development.

Bounded correct preserves prior receipts and selected original judgments/fact references, enters correcting and clears only selected assessments. Affected claims cannot disappear. Reclose links the original receipt; at most8 corrections, no correction after source compaction. All failure/permission/privacy/freshness protections remain. New records cannot be downgraded to old readers; rollback means use the fixed tool for its own data, not delete facts/change schema tags.

Limits:128 retained facts and256KiB per task,64 criteria/32 checks,512 exact inputs/list,32 attachments,16MiB/file and64MiB artifacts/task; original transient input/POSIX lock/query limits remain. Numbers are independent refusal bounds, not guaranteed simultaneous capacity. Prune previews and explicitly removes only unreferenced passing metadata; latest pointers, selected support, producer dependencies, negative/resolution facts and correction roots remain. Files are not removed by prune. Complete/expired owned cleanup may compact/forget according to actual policy and surviving limitation handoff; unfinished/correcting/unknown data remains. Not a permanent history archive.

## Retirement and verification

Retired writers: observations-per-criterion payload replacement; auto-all-candidate assessment; latest-only successful execution metadata; kind=changed blanket static rejection; whole-workflow-source identity veto; format1/2 reader/writer and pinned predecessor bridge. They are replaced, not left behind selectable flags. Five predecessor-only tests retired with that supported behavior; two static tests now assert actual runtime-proof requirements. Other applicable protection tests are ported to IDs and explicit fixture support. No private business fixture is committed.

New counterexamples cover static-vs-runtime requirements, multi-fact/subset adoption, artifact/input/TTL/protocol drift, source/producer attribution, old-format refusal, fresh-process read-only recovery, independent selected proof, metadata privacy, failure preservation, pruning/limits and capacity refusal before execution. Full current-suite evidence and actual size/old-reader probes are indexed in validation. Program results do not certify natural Agent judgment, context compression, Android/Figma outcomes, 50-person concurrency or net savings.

Old daily instructions/designs/reviews that duplicate retired contracts are removed from the current tree; original tracked bytes remain in already-pushed fixed Git `46fa61c`. Runtime instructions and usage describe0.26.0; MAINTAINER records actual publication and installation. Required long-term intent/constraints and negative knowledge remain in current code/tests/concise policy or fixed evidence, not a parallel old system.
