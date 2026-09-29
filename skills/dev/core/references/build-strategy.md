# Build execution selection (0.5.28)

Load when an authorized develop step is about to leave Scope for Build, including through next/session continuation. The router chooses serial or one pair of independent workers; the user need not select a mode. This release adapts between one and two, with a hard ceiling of two workers per attempt. It has no arbitrary-width scheduler or dependency-wave executor.

## Cheap first pass

Complete ordinary Scope and its current authority/review prerequisites first. Use existing tasks, impact investigation and source/code evidence; do not rescan the project or reread all evidence just to choose execution. Progress questions, help, mode activation and unresolved product decisions do not start implementation or workers.

Choose ordinary serial Build immediately if the user says `--serial`, no parallelism, no subagents, or equivalent. This restriction wins over a simultaneous `--parallel` preference. Also choose serial for fewer than two eligible tasks, unsupported independent contexts/worktrees, or uncommitted business work that must be preserved. Serial still needs its ordinary gates; missing/stale Scope evidence is a blocker, not a fallback excuse.

## Consider a pair only when worth it

For two or more ready tasks, use the scoped investigation to answer all of these:

- Independence: neither task waits for the other's output or an unresolved interface/decision. Trace callers, shared state/resources, navigation/lifecycle and preserved behavior where applicable. Different modules or files alone are not proof.
- Ownership: exact nonoverlapping files with reviewed impact coverage. Shared mutable resources, generated artifacts, build/check processes or external services must not introduce concurrent interference. If isolation is uncertain, serialize.
- Benefit: both tasks contain substantive independent implementation, investigation or checks. Tiny constant/text edits, nearly identical context rereads or costly integration usually favor serial. State concrete work/evidence; do not invent time/token estimates or select parallel just because two tasks exist.
- Capacity: the host supports fresh contexts and the user/environment's resource, cost and concurrency limits permit two. Unknown capacity or competing work favors serial. No new model choice, purchase or extra permissions is implied.

If any answer is unknown, use serial when ordinary Scope is otherwise eligible. When several tasks qualify, select one clearly independent pair from the existing task boundaries; leave the rest pending. Do not split a task artificially to fill two slots, invent dependencies away, or launch multiple pairs at once. An explicit `--parallel` request remains compatible but never bypasses safety/gates; a user-requested parallel rehearsal may itself justify its overhead, unlike ordinary implementation.

## Execute and report

Announce a short decision with evidence, e.g. “Build: serial — both changes share the payment state” or “Build: two workers — independent importers with separate tests; common schema is already fixed.” This is an execution decision within authorized implementation, not another approval question. Honor read-only/planning-only boundaries: report a proposed strategy without preparing or dispatching.

For serial, continue ordinary workflow in the current Agent. For a pair, load `parallel-build.md`, verify its stricter current task/history reviews and all helper eligibility, and put the independence AND expected-benefit rationale in the existing plan's `independence.reason`, with concrete evidence in `independence.evidence`. No new canonical strategy record or self-attested scope-ready flag. Prepare/preflight before dispatch; workers follow the edit → diff → finish ordering.

If preparation, a worker or integration fails, preserve the attempt, wait for writers to stop, and report the blocker; do not silently retry, switch to serial over its changes, widen ownership or use a smaller result as success. A newly found dependency needs fresh Scope review. After a successful candidate, the router rechecks freshness before any separately authorized primary adoption, updates existing shared records serially and uses ordinary Verify. Reassess execution for a later authorized slice from current facts; do not keep stale parallel decisions or start automatic waves. One valid pair is not permission to grow concurrency.

The policy is Agent judgment constrained by existing prepare/finish/integrate checks. Those scripts enforce declared ownership and evidence freshness, not semantic independence, actual performance benefit or host scheduling.
