# Two-task isolated Build execution (0.5.30)

Load after `build-strategy.md` selects two workers, including a compatible explicit parallel request. Ordinary develop/next chooses automatically; `--serial` forces serial. This pilot creates two detached Git worktrees and a third integration candidate outside the primary project. It does not launch processes by itself, apply changes to the primary checkout, commit/push, update task status or approve delivery. If the host cannot provide two independent execution contexts, report unavailable and offer ordinary serial Build.

## Router eligibility and plan

Parallel Build replaces only the execution of an eligible Build slice; it is not a shortcut past Scope. Before preparing a plan or dispatching, load `orchestration.md`, the develop section of `workflow.md`, `impact-review.md`, `task-semantic-review.md` and `historical-regression.md`. Load the applicable project profile before choosing or interpreting commands; load `module-context.md` only when module selection/catalog/dossier rules apply. Do not load unrelated Requirement/Repair/Deliver references just because this mode is parallel.

Use those ordinary Scope rules to inspect current authority, task meaning, change/preserve boundary and historical protection. Existing current reviews may be checked and reused; do not manufacture new reviews or refresh timestamps merely for dispatch. If review records are absent, the router completes their existing sync/review flow **before** prepare, only when record writes and any required decisions are authorized. If the user restricts the run to read-only, sync-only or disallows choices, report Scope blocked and stop; do not use compatibility warnings as permission, silently switch to serial, or ask a worker to fill records.

For this two-worker mode, both `task-review.json` and `regression-review.json` must exist and pass the existing develop validator, even for legacy features where missing records would ordinarily warn. A missing record stops prepare before creating scratch/worktrees; stale/pending/invalid records also stop. A zero-candidate history sync is a valid record, not permission to invent a retest. This additional eligibility rule does not retroactively change ordinary serial develop or historical delivery validation.

The router's Scope exit must identify the selected tasks, requirement/source basis, current review evidence, impact paths/preserved behavior, applicable module/profile constraints and actual develop result. Then move to Build → prepare → preflight → dispatch. After prepare, no canonical writes are allowed until workers stop; a necessary Scope correction requires a new attempt. Hash/structure checks cannot prove that the Agent loaded instructions or understood their meaning.

Complete the ordinary Scope prerequisites first: confirmed requirements, reviewed task meaning and source authority, module/impact investigation and historical regression review when required. Existing develop validation remains in force; warnings are not permission to skip the investigation. Restore archived features before changes. This pilot additionally requires a reviewed impact.json with exact allowed paths and a clean business worktree. Preserve pre-existing work and use serial Build when there are uncommitted business files, submodules, ignored assigned business paths or unsupported paths.

Select exactly two existing planned/in_progress tasks. Read entry points, callers, shared state/resources and interfaces to assess independence. No overlapping file or ancestor/descendant ownership, no task dependencies, no unresolved interface decisions. Different files alone are insufficient: if both modify the same behavior or one relies on the other's new output, serialize them. Record a concise technical rationale with file/line evidence, agreed interfaces and behavior to preserve. A script checks declarations, not semantic independence.

Put the reviewed plan in a fresh external scratch location. Example shape (replace the task IDs, paths, evidence and approved commands):

```json
{
  "schema_version": 1,
  "independence": {
    "reason": "Two separate pure functions with no shared mutable state",
    "evidence": ["upper.py:1-2", "lower.py:1-2"],
    "interfaces": ["convert(str) returns str; imports remain unchanged"],
    "preserve": ["Each task preserves the other entry point"]
  },
  "tasks": [
    {"task_id": "T-UP", "allowed_paths": ["upper.py"], "depends_on": [],
     "checks": [["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_upper.py"]]},
    {"task_id": "T-LOW", "allowed_paths": ["lower.py"], "depends_on": [],
     "checks": [["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_lower.py"]]}
  ],
  "integration_checks": [["python3", "-m", "unittest", "discover", "-s", "tests"]],
  "timeout_seconds": 120
}
```

Commands are actual argv arrays approved for this task/environment, not strings evaluated by a shell. Review their effects; arbitrary programs are not made safe by an argv array. Include integration assertions for cross-task behavior and relevant preserved/history behavior. No real tests configured means no eligible parallel attempt; do not substitute a synthetic exit 0.

```text
python3 core/scripts/parallel-build.py prepare <PROJECT> <ID> --plan <PLAN> --out <NEW-EXTERNAL-RUN>
python3 core/scripts/parallel-build.py preflight <RUN>
```

Prepare captures current primary inputs with the existing Verify helper, freezes canonical evidence under inputs/, checks develop eligibility and path ownership, and creates two detached workers from current HEAD. It writes only external scratch and Git worktree metadata. Existing output directories are refused. Failure may leave worktree registration and partial scratch; preserve and inspect them. The input manifest is disposable attempt data, never another authoritative project state.

## Dispatch two workers

Include the worker sequencing constraint in dispatch: wait for edit/write success, then inspect the actual diff and wait for that result, then invoke `finish` separately. Never batch these dependent steps or leave a writer running during checks. This ordering is required inside each worker, not between independent workers.

After successful router preflight, use the host's native independent Agent mechanism. Give each worker only its task ID, its worktree, RUN, frozen input path, Skill root, `specialists/featrace-build/SKILL.md` and side-effect restrictions. They use the same specialist with separate contexts/code directories. Do not pass a guessed implementation answer or give either worker write access to the primary/shared records. State whether permissions enforce the split or it remains an instruction plus post-run checks.

Workers return through parallel-build.py finish. Each return has its own directory; failed/blocked/missing returns stop integration, and cannot be silently overwritten. Source/requirement/Skill drift, frozen input edits, code changes after checks, edits to workflow records, or expansion beyond assigned paths also block. A cancelled Agent is not a successful empty patch. Do not automatically retry while the other worker writes; retain edits and arrange a new attempt when the cause is resolved.

## Integrate and hand back

Wait for both Agents to finish; never integrate while workers are still writing. Inspect the actual return records, patches/logs and preservation/interface compatibility before deciding whether to call any integration command.

**Return gate:** if either return is failed, blocked, missing, invalid or stale, preserve both workers and their evidence, report the concrete blocker, and end this Build attempt **without invoking `integrate`**. Do not call it as a refusal probe, diagnostic, smoke test or “proof the guard works”; the helper's rejection is a backstop, not the next workflow step after a known failure. Read-only inspection of existing evidence is allowed. Do not overwrite a failed return, retry, adopt only the successful peer, switch to serial over the attempt or promote completion.

A separately requested negative integration probe is a distinct diagnostic action with its own result; do not infer that request from “rehearsal”, “resilience” or “verify”. It never repairs or advances the failed attempt.

Only two current `ready` returns with matching code/check evidence and compatible reviewed semantics permit the router to call:

```text
python3 core/scripts/parallel-build.py integrate <RUN>
```

The helper rechecks primary/frozen inputs and exact worker patches/logs, applies both patches in a new integration worktree and executes the approved integration commands. Ownership collisions fail before dispatch/acceptance; Git apply conflicts and nonzero/timeout/unavailable integration checks retain the failed candidate. Inputs modified by checks are not accepted as green. No repeated integration over an existing candidate.

`candidate_checks_passed` means only that this external candidate passed those commands. The report names the base and candidate Git tree; it is not a final primary commit or a delivery quality report. Return to the router with that candidate, patches, actual results, scope and remaining gaps. Primary adoption remains an ordinary authorized Build step, not a new command or automatic approval:

1. Inspect the completed candidate and return evidence read-only. Verify the full candidate diff/tree, approved paths and actual check logs still match the integration report and ready returns. Do not stage, reset or edit the candidate to inspect it; use a private index when a tree calculation requires one. A changed or unverifiable candidate stops adoption.
2. Immediately before applying the full validated patches, run the existing `parallel-build.py preflight <RUN>` as a **separate blocking call**. Require exit 0 and `PARALLEL_BUILD_INPUTS_CURRENT`; any error/nonzero exit stops before primary code or record writes. Printing a digest comparison or recapturing inputs is not this guard: `False` printed by a successful process cannot stop adoption. Do not repair the old snapshot or refresh records to make it current.
3. Apply only the complete validated code under the ordinary task authorization, preserve pre-existing/staged content, then serially update existing task/traceability records from actual changes and results. Adoption changes the primary inputs by design; the old attempt preflight is not a post-adoption acceptance check and cannot be refreshed into one.
4. Run ordinary Verify/check/audit against the actual adopted primary worktree. Reconcile assertion coverage through the existing verification workflow; candidate logs do not become primary evidence. Leave unmet criteria and incomplete delivery explicit. An explicitly requested independent Verify runs after writers pause. No automatic complete/verified state or remote publication.

Retain scratch/worktrees until changes and evidence are safely handled. Cleanup is explicit: inspect `git worktree list` and use ordinary `git worktree remove <PATH>` only for a clean workspace. Never force-delete uncommitted work or remove another attempt. The helper has no automatic cleanup, worktree pool, retry scheduler, concurrent record writes, partial-task eligibility or broad dependency graph. Git worktrees share metadata and are not security sandboxes; ignored environment/build outputs, Git filters, external side effects and semantic completeness remain limits. Measure total preparation, both worker times, integration, interventions and token cost before wider adoption.

Worker check evidence also binds the visible worktree and index state; staged-index or visible-file changes during/after checks require a new attempt. Other ignored environment files, Git filters and external inputs are not fully bound. Frozen authority inventory additions are rejected as well as edits. These hashes detect drift; they are not signatures or a security sandbox.
