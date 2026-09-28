# Optional independent Verify pilot (0.5.24)

Use only when the user explicitly requests independent review, e.g. `/dev check FEAT-1 --independent` or “对当前需求做独立复核”. The existing check path remains the default. This option performs a read-only second review, not a fresh build/test run or automatic delivery. Do not change a progress question into a review. If both testing and review are requested, run authorized ordinary checks first, then bind the resulting snapshot.

## Router preparation

Confirm project/feature and the review scope. Determine a defensible pre-change Git base from impact/feature commits and the user's request; do not silently use HEAD when the implementation is already committed. Ask only if the base cannot be established. Preserve uncommitted work. Verify source access with `verify-inputs.py`; do not fill missing evidence. Obtain permission through the host only when actual delegation or environment access requires it.

Pause writes for this serial review. Use a unique task scratch directory OUTSIDE the project for the input snapshot and result, retain failed attempts there, and do not commit them automatically. The snapshot is a disposable input manifest, not a new authoritative handoff record or state machine.

```text
python3 core/scripts/verify-handoff.py capture <PROJECT> <ID> --base <BASE> [--path <ignored-evidence-file> ...]
```

Save stdout unchanged as the snapshot in scratch. Capture binds Git HEAD/index/worktree diff, visible untracked files, selected feature records and sources, project-baseline/modules, extra evidence and Skill content. It does not copy the repository or semantically scan all source files. Treat unreadable inputs as gaps; do not exclude a troublesome file merely to get current status. A submodule repository is outside this pilot; report that limitation.

## Router preflight before dispatch

Immediately before a host Agent call, run the existing read-only check against the exact prepared snapshot:

```text
python3 core/scripts/verify-handoff.py check <PROJECT> <ID> --snapshot <SNAPSHOT>
```

Dispatch only after exit 0 / `VERIFY_HANDOFF_CURRENT`. A stale, invalid or inaccessible input stops this attempt in the router: report blocked and that no reviewer was started, preserve existing scratch files, and do not synthesize a reviewer result. Do not spawn an Agent to repeat an already known preflight failure. If the user wants a new review after inputs stabilize, capture a new snapshot/output under a new attempt; never overwrite the old snapshot or patch its digest. The reviewer still performs its own preflight because inputs may change after dispatch.

## Dispatch

Use a host capability that creates a genuinely fresh Agent/context (no inherited conversation; e.g. a no-history subagent when the host offers it). Explicitly give it `<SKILL>/specialists/featrace-verify/SKILL.md`; nested Skill files are bundled instructions, not an assumption that the host auto-discovers or loads them. Do not recursively load the dev router into the reviewer.

Supply only project, feature, Skill path, snapshot path, external output path, the neutral review question and side-effect restrictions. Requirements/decisions in canonical files remain available; do not pass the implementer's proposed answer, suspected defect or green summary as instructions. Restrict the reviewer to read-only project access when the host supports it, with output writes only to scratch. When permissions cannot enforce that split, state that read-only is an instruction-level restriction with post-run checks, not a sandbox guarantee.

If the host cannot provide a fresh context, report `independent review unavailable`; offer ordinary check or an explicitly launched new review session. Never silently run in the current context and label it independent. Do not install/login to another tool or add credentials as a side effect. One reviewer at a time. Pause all Build workers before Verify; no concurrent implementation or record writes during review. The optional parallel Build pilot must finish and hand back its integration candidate first.

## Return and reconcile

First require successful Agent completion and a nonempty result. Timeout, cancellation or missing/malformed output is unavailable/failed, not zero findings. Preserve the output; do not auto-retry indefinitely. Before using any finding, run:

```text
python3 core/scripts/verify-handoff.py check <PROJECT> <ID> --snapshot <SNAPSHOT> --result <RESULT>
```

No-result check is only a preflight. `VERIFY_REVIEW_RETURN_CURRENT` means input identity and output shape match, not semantic correctness, test success or approval. If anything drifted, keep the original result as stale and capture/dispatch again when writes are paused; never patch a digest to inherit green. Added ignored evidence also needs recapture/review. Snapshot freshness is not a transaction or proof that no transient writes occurred; Git stat/ignore behavior, external services/devices and concurrent writers remain limits.

Independently inspect each finding's cited file/locator and classify it as confirmed, unsupported or needs decision. Reconcile authority and test coverage using the specialist's [Authority and test evidence](../../specialists/featrace-verify/SKILL.md#authority-and-test-evidence) rules: provisional is not unconfirmed intent, restoring explicit behavior is not a new product choice, and test IDs need evidence mapping rather than matching names. Missing records support gaps, not claims about their contents. A valid JSON result cannot do this for you. Report unresolved gaps even with no findings. For a review-only request, return this reconciled assessment without changing canonical records. When further action is authorized, the router alone uses existing clarify/revise/fix/verification/report flows; restore archived features before mutation. Recheck freshness immediately before writeback and serialize it. A review result never sets complete or verified: ordinary tests, manual evidence, validate and audit remain required.

Keep one reviewer per eligible attempt. Reconcile precise citations rather than doing another full independent investigation, while expanding reads when a finding requires it. Avoid automatically retrying an unchanged review or sending duplicate full rule/source text in the dispatch message; pass the bound paths and the specialist path. These reduce avoidable work without lowering evidence obligations or changing the model.

Record the measured review time (including preparation and reconciliation), meaningful findings, false positives, handoff gaps and token usage when exposed by the host. Current pilot demonstrates mechanics only; no claim of fewer omissions or lower cost without comparative evidence across real work.
