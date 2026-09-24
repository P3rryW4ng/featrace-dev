# Verification checklist (0.5.3)

Use within `/dev check`, and after authorized develop/fix implementation when preparing acceptance. No new user-facing command. The Agent selects applicable commands, then generates the checklist and executes the automated portion. Ask the user only for remaining observations or business judgments. Respect requests for analysis-only or no execution.

At the start of Verify, run the internal, read-only input inventory before relying on source or quality claims:

```text
python3 core/scripts/verify-inputs.py <PROJECT> <ID>
```

Inspect the actual readable source files and hashes, source-index disagreement, Git HEAD/worktree changes, and the quality report's recorded test time/revision. Files in the feature's `sources/` directory that are not in the source index are listed as supplementary evidence, not silently treated as approved requirements. A report from an older HEAD may still be current after workflow-only commits; use the existing audit to decide currency. Exit 0 means the inventory was produced, not that verification passed. Missing or uncertain inputs remain explicit; do not infer that an absent file was read or borrow an old quality result. This step writes no project records, builds nothing, and does not replace `validate-feature.py`, `verification.py` or `audit-delivery.py`.

Complete requires active requirements confirmed against evidence, all tasks done, no unresolved fixes or pending conflicts, required sources reconciled or justified as not applicable, traceability and actual test evidence, and applicable quality gates passed for the delivered revision. Run `validate-feature.py --stage check` and `audit-delivery.py`, then inspect task/decision meaning, code and test assertions, and the delivery report. Structural validity and audit currency do not prove semantic or UI correctness. Controlled requirement baselines additionally need delivery registration under `revision-workflow.md`. If checks cannot run, report unavailable and provisional rather than success.

## Generate and review

Prepare the impact checklist under impact-review.md. Read `project-baseline.md` for quality candidate/selection semantics, then select concrete quality-gates.json commands under existing project rules. Run:

```text
python3 core/scripts/verification.py sync <PROJECT> <ID>
```

This creates/updates feature-local verification.json and verification.md, marks feature.verification_required, and preserves earlier result attempts. Active requirement acceptance criteria and impact behaviors each become manual rows; each selected quality command becomes an automatic row. Missing gate selection generates an unresolved row rather than success. Changed/removed source rows are retained in retired with their evidence; new meaning gets a new ID. Sync is not acceptance and does not execute commands. Legacy untouched features need no migration; continuing current validation adopts this list. Archived features require restore for mutations.

Review whether criteria cover the real feature. A script cannot discover missing requirements or turn a vague criterion into meaningful steps. Before asking for manual results, the Agent supplies concise preconditions (account/flags/build), actions and expected outcome per remaining row. Test/UI automation is available only if the project actually has executable commands and required devices/credentials; this version does not install a device driver or UI framework.

## Map and execute

Canonical list fields: schema_version=1, feature_id, items, retired. Generated item fields id/source/expected are derived from inputs. Editable execution fields are mode (manual/automatic), gates (selected gate names), coverage (why the actual assertions cover the whole expected behavior). History is written by the helper. Do not manually manufacture results.

To automate a behavior row, inspect the assertions, set mode=automatic, gates=[names], and a nonempty coverage explanation. Every mapped gate must pass. Compile success must never stand in for visual, navigation or product acceptance. Leave partial coverage manual, or refine the source acceptance criteria into independently verifiable parts through existing rules. Do not add arbitrary commands to the list; it reuses the selected quality configuration. Keep generated gate rows automatic.

```text
python3 core/scripts/verification.py run <PROJECT> <ID>
```

This first checks develop eligibility, then calls the existing project check runner once and captures its fresh results. It never borrows an old quality report when no new report was generated. It records command output, result, timestamp, content digest and full Git revision. Before/after changes prevent a passing claim. Manual rows remain untouched; failures stay in history on rerun. No automatic marking of feature complete, fixes verified or decisions applied.

Then run existing `validate-feature.py --stage check` and `audit-delivery.py` as appropriate; record failures and gaps honestly. The checklist runner does not replace those overall delivery checks. Nonzero run/status code 2 means rows remain unfinished, not necessarily a build failure; code 1 reports invalid input/environment. Sync and successful manual recording return 0 without claiming completion.

## Manual results and remaining work

`verification.py status <PROJECT> <ID>` prints each row's effective state, current digest and revision. Present the user only outstanding manual actions, automatic failures/unavailable checks, and relevant waivers; no need to resend passing rows each time.

After receiving actual observations for that tested build, record each manual row:

```text
python3 core/scripts/verification.py record <PROJECT> <ID> --item <row-id> --status passed --digest <captured-digest> --tested-revision <full-commit> --actual "Observed outcome" --evidence "User confirmation; build/device or screenshot reference"
```

Statuses: passed/failed/unavailable/waived. Not-run needs no result; an unavailable environment is not a pass. Waivers need reason, risk, follow-up and actual acceptance authority in evidence, and must appear in the delivery report. Automatic gate rows cannot be manually passed or waived through record. A stale digest or wrong current commit rejects manual acceptance; preserve old-build observations in report history, never relabel them as a new build. Full commit alone cannot prove installation identity: Agent must confirm package/device context with the user, particularly with uncommitted code.

## Integration and limits

At check, missing adopted lists, missing/failed/unavailable/stale rows block completion. Passed or explicitly waived rows satisfy only this record obligation. Impact behavior validation reads corresponding current list evidence directly, so no duplicate acceptance entry is necessary in impact.json. Prior impact verification remains historical when the new checklist is adopted.

The digest covers requirement records, decisions, current impact snapshot, selected quality config and item execution mapping; it excludes result histories and task progress files. Changes conservatively stale the whole list, not just precisely affected rows. Related file changes are detected within declared impact coverage; ignored/unregistered files and external environments are not exhaustive. Agent must reassess relevance before rerunning or explicitly documenting reuse; never replace old digests to hide a change. Semantic coverage and evidence truth remain human/Agent responsibilities.

One canonical list plus one generated view per feature; attempts and retired rows retain history without timestamped directory copies. No automatic cleanup of history yet. Share after sensitivity review: command output may contain private information. Helpers use atomic single-file replacement, not cross-file transactions or concurrent session isolation; serialize mutations for the same feature. No automatic push or installation.
