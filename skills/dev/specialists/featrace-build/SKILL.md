---
name: featrace-build
description: Implement one confirmed FeatraceDev task in its assigned isolated worktree and return code with executed task checks. Loaded by the dev router for the router-selected two-task isolated Build; never edits shared feature records or integrates a peer's changes.
---

# Isolated Build worker

Use only the router's assigned attempt directory, task ID, worker path, frozen authority path and Skill root. This is bundled guidance, not another user command. Work in a fresh context; do not load the main dev router or inherit another worker's proposed answer.

Before reading task evidence or editing code, run:

```text
python3 <SKILL>/core/scripts/parallel-build.py preflight <RUN>
```

Stop if it fails. Preflight precedes reading task evidence or code. Then request only this task's read-only view:

```text
python3 <SKILL>/core/scripts/parallel-build.py task-view <RUN> <TASK-ID>
```

Require `PARALLEL_BUILD_TASK_VIEW_CURRENT`. The helper rechecks frozen inputs and returns the assigned worktree, checks, interfaces and the selected task's requirements, related decisions, traceability and change/preserve boundaries. Only `assigned.allowed_paths` permits edits; `impact.reviewed_change_paths` describes the broader reviewed feature, not your ownership. Do not load the full `run.json` or every feature record by default. This view is a starting index, not new authority or a promise that other code is irrelevant: read cited original sources and inspect callers/shared behavior as needed. A decision without explicit requirement linkage and every preserve behavior stays visible. If the view reports a gap, or a newly found dependency needs more records, inspect the frozen originals under `<RUN>/inputs/.agent-workflow/`; return blocked to Scope when the assignment or product authority must change. Do not perform adoption, sync, review or canonical writes from a worker.

## Implementation boundary

For any temporary scripts or test copies, read `../../core/references/write-scope.md` and use only the router-assigned task scratch under RUN. Never default to system temp, create workflow scratch in the worker or broaden code ownership for temporary files. If no permitted scratch is assigned, stop that temporary operation and report the missing location.

- Edit only the exact paths assigned to your task in your own worktree. Read related local consumers and project conventions as needed; being in different files does not establish semantic independence.
- Do not write to the primary checkout, another worker, frozen inputs or any `.agent-workflow` records. Do not change Git configuration, branches, commits, worktree registration or another task's interface. Leave implementation edits uncommitted; the helper exports them with a private index.
- Do not expand scope to make a test green, weaken existing assertions or accept a regression that violates confirmed preservation. Return blocked with the necessary scope/authority correction instead.
- No builds/installations/network access beyond the explicitly authorized task commands and host permissions. The router selected check argv arrays; do not replace them with a convenient command or claim another task's result as yours.

## Return

Finish all edit/write operations and wait for their tool results. After they succeed, call the helper in a separate tool call:

```text
python3 <SKILL>/core/scripts/parallel-build.py inspect-diff <RUN> <TASK-ID>
```

Read its complete `full_diff` content, not just paths, `--stat`, a digest or a summary. Check every changed hunk against the assigned scope, requirement, preserved behavior and interface. The helper emits the exact patch that `finish` will export and records an attempt-local inspection bound to the current patch and worker state. If output is truncated, inspect the missing portions before finishing; if you cannot see the complete patch, return blocked rather than claim `ready`. After any edit, run `inspect-diff` again. If an edit failed or its result is uncertain, resolve that before inspection.

Only after the full diff output has returned and you have reviewed it, invoke `finish` exactly once in a separate tool call. `finish ready` rejects a missing or stale inspection; emitting the diff cannot prove you understood it. Do not put edits, inspection and `finish` in the same assistant message/tool batch, run them concurrently, or launch `finish` while any writer is pending. Keep the worktree unchanged until `finish` returns. These are dependent steps within one worker; the two independent workers may still run concurrently:

```text
python3 <SKILL>/core/scripts/parallel-build.py finish <RUN> <TASK-ID> --status ready --summary <honest-implementation-summary>
```

It checks current authority and file ownership, exports the actual code patch, runs the selected commands with a timeout, and binds their logs to that patch and the visible worktree/index state. `ready` is only a task candidate with passed checks, not a done/verified/complete feature. A failed command changes the recorded return to failed. Inspect the helper output; do not rewrite result JSON, patch, logs or digests, or overwrite a failed attempt to inherit green.

If you cannot implement, return once with `--status blocked` or `--status failed` and the concrete reason. Preserve any edits. If the helper itself cannot run, tell the router that the return is missing/unavailable; do not manufacture it. Missing/failed results prevent integration. Only the router combines candidates, tests their interaction and serially updates canonical task/traceability/verification records through the existing workflow.

Read-only/shared-write boundaries are host instructions unless the host enforces them. Git worktrees isolate code directories but share repository metadata. Scope and hash checks detect final deviations, not arbitrary transient or external side effects. Report actual elapsed time and token use when exposed by the host; do not claim that concurrency automatically made delivery faster.

## Message to the router

The helper's return JSON, exact patch and check logs are the evidence. After inspecting its output, send the router a compact handoff in the user's language with these labels, in this order:

- **Status:** task ID and actual `ready`, `blocked` or `failed` return; use `unavailable` if the helper produced no valid return.
- **Outcome:** one sentence naming the behavior changed, or the concrete reason work stopped.
- **Checks:** selected commands actually run and their pass/fail state; explicitly say `not run` when blocked before them.
- **Risk:** remaining dependency, behavior or evidence gap; say `none found` only within the assigned task scope.
- **Next:** exact return directory and the router action needed. Never tell the user a candidate is delivered or complete.

Use one line per label, no table or nested list; add lines only when distinct material blockers require them. Do not paste the full diff, JSON, command logs, chronological tool narration or repeated project background into this message. The router must read those artifacts directly and must not treat this short text as proof. Do not compress away a failure, an unreviewed hunk, or a changed interface; point to its exact evidence location and state the blocker plainly. Measured time/token use can be one additional line when exposed, otherwise omit it.
