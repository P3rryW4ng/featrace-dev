# Explicit check execution facts and current acceptance

Load only when the project explicitly enables the feature-scoped execution contract below. This is an internal extension of ordinary Technical Test/Verify, not a new Skill, additional stage, service or authority to execute commands. Legacy projects keep their existing execution path until explicitly prepared; installing a tool never migrates a business project.

## Prepare a feature selection

After authorization to enable the new contract in this workspace, retain the project check definitions in `.agent-workflow/project-baseline/quality-gates.json`. Put an explicit array of selected definition names and this feature's `test_ids` in authorized ignored scratch, for example `[{"name":"unit-wallet","test_ids":["TEST-1"]}]`. Then:

```text
python3 core/scripts/check_runs.py prepare <PROJECT> <ID> --selection <request.json> --reason <inspected-selection-reason>
```

This writes the feature's `check-selection.json`, preserves the old config in `check-contract-v2-origin.json`, and explicitly marks the project config `execution_contract: 2`. Ordinary command definitions are shared; TEST mappings and selection reason belong to the feature. No check executes. Definitions must exist, choices must be distinct, and all commands/paths/timeouts are validated before any write. Preparation and execution take the same nonblocking workspace lock. Unresolved earlier processes prevent new selection or execution. A partial opt-in can be explicitly retried only against its exact recorded original config; conflicting inputs require investigation. Other participating hosts must understand the new marker. Older validators reject it; do not delete the marker to borrow legacy green reports.

## Execute and keep facts

Use ordinary `verification.py run <PROJECT> <ID>` after reviewed scope, module/task eligibility and actual check selection. The router invokes `project.py check --feature <ID>`; the direct latter command also uses the same lock, feature selection and attempt writer. No feature ID means no execution in this mode. Capture includes B1's actual Git/index/worktree and declared local input identity, not only HEAD or a manifest list. Necessary ignored/external inputs must be explicitly registered; unsupported Git/files/environment remain gaps, not certified input identity.

Each new execution writes a unique feature-local `check-runs/<attempt>/start.json` and an immutable terminal `result.json`, plus a `check-head.json` latest pointer. The start freezes resolved commands, cwd/timeout, test IDs, feature and input identity. Results preserve actual start/end, exit or unavailable/interrupted state, bounded output and input comparison. No command result is manufactured from an older run. Project-wide `quality-report.json` is not read or overwritten as a new-mode authority. Different features keep their own attempts; the workspace lock rejects overlapping execution before commands start, without claiming to coordinate shared devices or another worktree/machine.

Only a complete successful latest attempt with matching current input/selection can certify execution. A later failed/interrupted/missing/corrupt result cannot fall back to earlier success. Timeout/interruption terminates the owned POSIX process group and checks it has ended; unresolved groups or unfinished/orphaned attempts block further runs and certification. Hard crashes require read-only process/record investigation, not automatic retry or manual re-signing. Automatic recovery/queueing and non-POSIX process-group execution are not implemented. Lock release alone does not prove child processes exited.

Attempt records are local workflow artifacts and may contain command output; keep sensitive raw output private/ignored under project policy. No helper auto-commits or uploads them. Shared durable evidence requires the existing explicit privacy/archival process. Hashes bind recorded bytes; they do not prove command honesty, external environment stability or semantic coverage.

## Bind actual assertions to current claims

Execution truth is separate from acceptance. `verification.py run` may bind generated command-success rows to the actual latest attempt, but does not automatically pass every mapped product claim merely because commands exited zero. Inspect current complete requirements, preconditions, assertions and preserved behavior as ordinary Verify already requires. For explicit automatic targets:

```text
python3 core/scripts/verification.py capture-check-mapping <PROJECT> <ID> --items <item-id> <item-id>
python3 core/scripts/verification.py adopt-checks <PROJECT> <ID> --review <mapping-review.json>
```

Save the captured JSON in authorized scratch. The review supplies `input_digest`, the exact `item_ids`, real `reviewer`, `status: "supported"`, and one finding per target with `item_id`, `verdict: "supported"`, actual executed `test_ids`, `assertion_evidence` locating inspected assertions/output, `required_scope`, and `counterexample_check`. There is no new mandatory human approval or extra independent Agent for every ordinary mapping; the authorized Verify agent records its actual inspection. These fields are attestations, not proof of semantic correctness. The normal final v6 independent full-claim review still applies.

Only executed tests from the mapped gates can be selected. Partial/unasserted new requirements remain uncovered even when a reusable execution fact exists. Mapping input freezes the current plan and semantic contract; changed input, newer attempt or concurrent plan edit refuses application without overwriting others. Apply references the original attempt's tested revision/time; it is not a second command execution or manual/device observation. Repeating the exact same adoption is idempotent and unchanged rows do not acquire duplicate history. Successful execution with a failed registration can be inspected and adopted without rerunning commands; corrupt/incomplete execution cannot.

New-mode verification uses schema 4 and explicit `check_attempt` references. Old histories stay readable without invented attempts. Ordinary per-row mapping changes expire that row's binding rather than all unrelated mapping rows; complete requirements/decisions/impact semantics remain conservatively bound. New decisions or actual semantic changes still need re-evaluation, not automatic green status. Actual code/test/config input changes still invalidate execution in this first batch, including unrelated test additions; no symbol-level reuse or cross-attempt green-result assembly exists.

Audit, revisions, status, Test/Verify views, report drafts and final review read the same latest feature attempt/currentness. Manual evidence digests and device continuity keep their own contracts. Unresolved manual claims, authority, fixes or final review still prevent completion even when all execution facts are current. Schema/selection/entrypoint incompatibilities must be resolved before using a new-mode workspace with old tools; reverting only the installer is not data rollback.


## Managed directory links (0.18.1)

The source candidate accepts committed, index-unchanged relative links directly to existing managed directories inside the Git project. Leading `../` is supported without escaping the root; absolute targets, intermediate `..`, link chains/nested links, submodules, missing or unmanaged/ignored target members and workflow/Git control targets remain unknown. Link target bytes and the complete tracked target membership/content remain inputs; there is no `.claude` or `.agents` exemption. Descriptor-relative no-follow reads reject path replacement and capture drift.

Check identities use schema 2 only when these links exist; regular projects keep schema 1. Earlier identity readers reject schema 2, so participating readers must be updated before resuming. This does not change the feature verification schema, opt in execution contract 2, migrate records or re-certify old unavailable results. Execute the already-selected checks anew after input recognition is available. Explicit evidence/workflow paths retain their existing no-link restrictions; a link added or changed by the feature still needs normal impact handling. This compatibility is included in 0.18.1.
