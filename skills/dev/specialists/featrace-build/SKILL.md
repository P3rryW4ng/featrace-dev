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

Stop if it fails. Preflight precedes reading run.json, task evidence or code. Scope review is the router's completed prerequisite: do not perform adoption, sync, review or canonical writes from a worker. Read `<RUN>/run.json` for your exact task, interfaces, preservation rules, allowed paths and selected checks. Read relevant original sources, confirmed requirements, decisions, impact and reviewed task meaning under `<RUN>/inputs/.agent-workflow/`; use these frozen copies as the authority. Missing detail, a conflicting contract or a newly discovered dependency is a blocker, not permission to invent behavior.

## Implementation boundary

For any temporary scripts or test copies, read `../../core/references/write-scope.md` and use only the router-assigned task scratch under RUN. Never default to system temp, create workflow scratch in the worker or broaden code ownership for temporary files. If no permitted scratch is assigned, stop that temporary operation and report the missing location.

- Edit only the exact paths assigned to your task in your own worktree. Read related local consumers and project conventions as needed; being in different files does not establish semantic independence.
- Do not write to the primary checkout, another worker, frozen inputs or any `.agent-workflow` records. Do not change Git configuration, branches, commits, worktree registration or another task's interface. Leave implementation edits uncommitted; the helper exports them with a private index.
- Do not expand scope to make a test green, weaken existing assertions or accept a regression that violates confirmed preservation. Return blocked with the necessary scope/authority correction instead.
- No builds/installations/network access beyond the explicitly authorized task commands and host permissions. The router selected check argv arrays; do not replace them with a convenient command or claim another task's result as yours.

## Return

Finish all edit/write operations and wait for their tool results. After they succeed, read the actual diff in a separate tool call and confirm the assigned scope and intended change. If an edit failed or its result is uncertain, resolve that before requesting `ready`.

Only after the diff inspection returns, invoke the helper exactly once in a separate tool call. Do not put edits, diff inspection and `finish` in the same assistant message/tool batch, run them concurrently, or launch `finish` while any writer is pending. Keep the worktree unchanged until `finish` returns. These are dependent steps within one worker; the two independent workers may still run concurrently:

```text
python3 <SKILL>/core/scripts/parallel-build.py finish <RUN> <TASK-ID> --status ready --summary <honest-implementation-summary>
```

It checks current authority and file ownership, exports the actual code patch, runs the selected commands with a timeout, and binds their logs to that patch and the visible worktree/index state. `ready` is only a task candidate with passed checks, not a done/verified/complete feature. A failed command changes the recorded return to failed. Inspect the helper output; do not rewrite result JSON, patch, logs or digests, or overwrite a failed attempt to inherit green.

If you cannot implement, return once with `--status blocked` or `--status failed` and the concrete reason. Preserve any edits. If the helper itself cannot run, tell the router that the return is missing/unavailable; do not manufacture it. Missing/failed results prevent integration. Only the router combines candidates, tests their interaction and serially updates canonical task/traceability/verification records through the existing workflow.

Read-only/shared-write boundaries are host instructions unless the host enforces them. Git worktrees isolate code directories but share repository metadata. Scope and hash checks detect final deviations, not arbitrary transient or external side effects. Report actual elapsed time and token use when exposed by the host; do not claim that concurrency automatically made delivery faster.
