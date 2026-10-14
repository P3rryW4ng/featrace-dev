# Technical Test handoff (0.11.1)

Use inside an authorized ordinary Verify after Build/Repair, or when a user asks to run applicable objective checks. This is an internal responsibility boundary, not a new user command, seventh stage, separate Agent, or independently installed Skill. The current router performs Test in the same context; extraction requires a later same-input accuracy/cost comparison. An explicit read-only or `check --independent` request does not run Test. Load only the applicable project profile, quality-selection rules in `project-baseline.md`, and source/impact records needed for this test scope; Deliver and completion rules stay with `verification-workflow.md` and the router.

## Input boundary

Start from the selected feature ID, reviewed requirement/AC and impact rows, current Git/worktree revision, actual implementation diff, changed and preserved behavior, historical-fix planned checks, project CI/profile/candidate commands, and available test environment. Inspect test files and their assertions, not merely test names or a green prior report. Investigate direct and transitive callers when deciding which existing behavior is exposed. Identify external configuration separately; do not compile the client for a task that changes no client code solely because it shares a feature.

## Test responsibilities

1. Build a compact per-claim coverage account in the existing `verification.json`: expected behavior and exact preconditions; test file/case and assertion; actual command and `test_ids`; what is executed versus inferred; tested revision; uncovered branches, inputs, interfaces, environment and device identity when relevant. A `coverage` explanation does not make an incomplete assertion complete. Do not fill every row with the same generic paragraph. Keep human/product observations separate from automatic checks.
2. Select concrete applicable commands from project rules and investigated scope. Bind `quality-gates.json.selection_feature_id` to this feature before execution. Do not reuse a previous feature's selection, choose a full suite and its children redundantly, or turn a test ID into proof of execution. Run `python3 core/scripts/verification.py sync <PROJECT> <ID>`; map a behavior row to `automatic` only when the selected assertions cover its **whole** expected behavior. Otherwise leave it manual/unavailable for later assessment. Do not change product meaning to fit available tests.
3. Where an existing safe test seam allows it, add or strengthen focused executable assertions for missing objective behavior. Such code/test edits return to the normal Build/Repair scope, review and task commit rules; Test does not silently widen production code, invent a dependency, or run destructive setup merely to obtain a green result. For device/instrumented checks, first confirm device, account, installed build and restoration capability under the Android profile. A build, screenshot or successful setup command is not a behavior assertion.
4. Run `python3 core/scripts/verification.py run <PROJECT> <ID>` against the final applicable code state and retain the generated `quality-report.json`, `verification.json`/view, test output or XML references and exact exit codes. A failure must remain failed; investigate it through Repair, then rerun affected checks. An unavailable environment stays unavailable. Reuse a current result only with its original tested revision and an explicit relevance check; do not relabel it as freshly run.

## Coverage classification before execution/revision (0.13.3)

Describe two separate facts in the existing row `coverage`/actual/evidence text and report, without adding a new registry:

- Execution method: automatic assertions (JVM/device/CI), Agent runtime observation, user observation, static inspection or unavailable.
- Delivery evidence channel: selected passed quality gate; current reviewed device execution receipt; external/runtime observation; or static reasoning with its limits.

A device test with executable assertions is automatic even when run outside the daily gates. Legacy row `mode: manual` and revision `manual_coverage` identify a non-gate assessment route; they do not mean a human executed the test. Do not call all non-gate rows “manual tests” or turn static review into runtime observation. Conversely, a device screenshot or successful instrumentation setup without behavior assertions is not an automatic behavior test.

Before submitting an immutable revision draft, compare its planned `test_ids` with applicable reviewed gate commands and their explicit IDs. New draft `test_ids` designate intended gate-backed checks; put non-gate device IDs, actual observations and their target criteria in the existing report/coverage explanation, not that array merely because they have a TEST name. Planned gates may still need to be configured/executed; an ID match is not proof of execution. A device check belongs in this array if it really will run as a selected applicable gate. Missing resources mean unavailable, never a new gate invented solely to satisfy the array. See revision-workflow.md.

## Asynchronous absence/removal assertions (0.13.3)

When an assertion says an event never occurred or an object was removed, distinguish a real negative outcome from the trigger never running, delayed arrival, the wrong object, skipped execution or observing too early. Inspect the affected test, not every unrelated test.

For removal, establish the exact object's arrival/presence through a positive observation or independently bound event trace, then observe the required removal. Use a bounded wait and the behavior's required timing window; wait timeout is failure/unavailable, not absence proof. For “must not appear,” confirm the triggering action/input and observer are active and monitor the relevant specified interval; do not demand an object appear when the requirement forbids it. A fixed sleep alone does not establish these premises. Do not change product timing to make a test pass or infer permanent absence from a short window.

Where feasible, try a focused counterexample: disable removal while preserving arrival, suppress the trigger, or break the observer. A meaningful test rejects those cases. Use an isolated fixture or existing safe seam, not an unapproved production edit/device action. Mutation need not be a new always-on gate; if infeasible, document the examined counterexample and remaining uncertainty. Skipped/zero-executed cases and assumed waits are not passes. Return only an affected gap to Build/Repair, preserve genuine prior results and rerun affected checks; no unrelated whole-matrix retry.

## Handoff to Verify

The two existing artifacts are the handoff, not a new canonical JSON: project-level `quality-report.json` contains selected commands, exit codes, time and tested revision; feature-level `verification.json` contains each claim's execution mapping, coverage explanation, results and gaps. Pass their exact paths and current Git/worktree identity plus a concise list of uncovered claims. Original test files, output and source remain inspectable by reference; a narrative summary cannot replace them.

Test reports what ran and what its assertions observed. The existing `verification.py run` mechanically records `passed` for a mapped automatic row when its gate succeeds; that field is **not** a final semantic approval. Test must not decide that the entire requirement, historical fix, UI outcome or feature is delivered, mark `complete`, approve a waiver, or sign the focused claim review. Ordinary Verify must read the cited assertions and compare each full claim with actual evidence, including a counterexample; new v6 Deliver still requires its fresh-context claim review. If Verify finds a coverage overclaim, correct the mapping/result while retaining history and return only the affected objective gap to Test or Repair. Do not rerun unrelated passing checks solely to restate this handoff.

For the next real feature, measure Test preparation/execution time, Verify review time, duplicated reads, uncovered claims found after handoff, false blocks and test reruns. No claim of greater accuracy, lower Token cost or full automatic coverage follows from this instruction split alone.

For large/scoped starting inputs or a Test-to-Verify handoff, load `stage-inputs.md`. Preserve full linked claims and unresolved/shared authority; inspect original assertions and retained provenance as needed. View freshness is not a semantic verdict. Optional `stage-cost.md` measurement stays outside acceptance gates.
