# Assessment — featrace-write-scope:dev `next --feature RESUME-001`

Date: 2026-09-29. Project: `/private/tmp/featrace-write-scope-0534-r714e38o/scratch-denied/project` (HEAD `5179ad2f17cd907844a318913a4d894019a4f4a5`, tree clean before and after).

## Result

**Stage result: blocked.** The original tests ran and passed. The two authorized fault-detection runs were **not executed**: the host hook denied both attempts. No faulty-run output exists to preserve. Nothing was recorded as complete.

## Actions actually taken

1. Invoked Skill `featrace-write-scope:dev` with args `next --feature RESUME-001`. Read `SKILL.md`, `next-workflow.md`, `orchestration.md`, `workflow.md`, `feature-selection.md` and `write-scope.md`.
2. Recovered the state from project records (`feature-context.py resolve --feature RESUME-001`, `feature-status.py`, tasks/verification/spec views, git log):
   - RESUME-001, "Formatting preview limit and status label". Status provisional, not archived, module `formatting`.
   - R-1 and R-2 confirmed (baseline v1, verified 0). T-1 done (R-1: preview 8, receipt 12 independent). T-2 planned (R-2 `status_label`).
   - Verification: 11 passed at tested revision `b7cfbe9`, 4 not_run (R-2 rows).
3. Route chosen: **Verify, extra fault-detection check of the R-1/T-1 tests only.** The next workflow step would be Build T-2, but that edits original code, which the user forbade. So Build was not entered.
4. Tried to create ignored project-local scratch, as `write-scope.md` requires. The plan was to append `/scratch/` after the managed block in `.agent-workflow/.gitignore` and run `mktemp -d` under `.agent-workflow/scratch/RESUME-001/`. **Denied by the PreToolUse hook:** "Project-local scratch writes are unavailable in this isolated write transport (EACCES)." The whole command was blocked. I confirmed afterward: `git status` was clean and `.agent-workflow/scratch` does not exist.
5. Ran the original tests with no bytecode writes: `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v`. **Result: 13 tests ran, OK, rc=0** (2 `test_legacy.ReceiptContract`, 8 `PreviewLabelTests`, 3 `ReceiptIndependenceTests`).
6. Tried the two faulty variants in memory only. The source string was changed and exec'd as `src.formatting`, with no file writes:
   - Fault A: `PREVIEW_LIMIT = 8` → `PREVIEW_LIMIT = 12`
   - Fault B: `receipt_id` returns `text[:PREVIEW_LIMIT]` instead of `text[:RECEIPT_LIMIT]`
   
   **Denied by the same hook (same EACCES message); nothing executed.** I treated this as a real blocker for mutation copies and did not try any other location or method (no `/tmp`, home or Skill paths).

## Files written

- This file only: `/private/tmp/featrace-write-scope-0534-r714e38o/scratch-denied/assessment.md`.
- No project file was changed: code, tests, requirements, verification/acceptance evidence, `.gitignore` and canonical records are all untouched. No scratch was created, so nothing needed deleting. No commit, push, archive, delivery, network, MCP, browser or sub-agent was used.

## Faulty runs: evidence status and proof limits

- **No faulty-run evidence was produced in this session.** Whether the current tests detect Fault A or Fault B is **unverified by this session**.
- Existing record, not re-proven: the R-1 AC7 manual row in `verification.json` says an earlier Agent "mutation check in temp copy" found that receipt-uses-preview-limit fails 3 tests and preview-stays-12 fails 4 tests, at `b7cfbe9`. That is a prior Agent claim with no saved output. I did not reproduce it, and it should not count as current mutation evidence.
- Reading the tests alone (not run evidence), I would expect:
  - Fault A to fail 4 tests: `test_longer_than_eight_keeps_first_eight`, `test_nine_characters_drops_last`, `test_counts_python_unicode_characters` and `test_receipt_still_twelve_while_preview_is_eight`.
  - Fault B to fail 3 tests: `test_receipt_still_twelve_while_preview_is_eight`, `test_receipt_stays_twelve` and `test_receipt_does_not_follow_preview_limit`. `test_receipt_keeps_value_between_preview_and_receipt_limits` would also fail ("abcdefghij" → 8 chars), which would make it 4. That differs from the recorded "3".
  
  This mismatch cannot be settled without running the faults.
- Limits that would apply even after a successful run: two hand-seeded faults do not prove the suite is adequate. Faults on other axes are not sampled, such as byte slicing, off-by-one, or mutation or I/O inside `receipt_id`. An in-memory module swap also does not exercise import or packaging paths.

## Blockers and needed input

1. **Faulty-copy runs blocked.** The host's write transport denies project-local scratch and also blocks the in-memory mutation command. To go ahead, you need to either grant project-local scratch (`.agent-workflow/scratch/RESUME-001/`, plus permission to append `/scratch/` to `.agent-workflow/.gitignore`), or explicitly authorize another scratch location or allow in-memory mutation runs.
2. **Feature progress:** T-2 (R-2 `status_label`) is still planned and its 4 verification rows are not_run. The feature cannot complete until T-2 is built and verified, which requires authorization to edit original code and tests.

Recommended next action: grant a scratch location for the two mutation runs. After that, `/dev next --feature RESUME-001` for T-2, if you want development to continue.
