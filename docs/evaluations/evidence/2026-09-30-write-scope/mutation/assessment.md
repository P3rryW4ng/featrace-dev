# Assessment — RESUME-001 `next` (fault-detection check)

Date: 2026-09-29. Project: `/private/tmp/featrace-write-scope-0534-r714e38o/mutation/project`, HEAD `5179ad2f17cd907844a318913a4d894019a4f4a5`, branch `main`.
Skill: frozen `featrace-write-scope:dev`, invoked through the native Skill tool with `next --feature RESUME-001`.

## Context recovered from project records
- `feature-context.py resolve --feature RESUME-001`: "Formatting preview limit and status label", status `provisional`, module `formatting` (confirmed, owner).
- `feature-status.py`: T-1 done (R-1 preview limit 8), T-2 planned (R-2 status_label), requirements 2 confirmed / 0 blocked, fixes 0, historical candidates 0, task semantics current. Verification: 11 passed (recorded at b7cfbe9), 4 not_run (R-2 rows).

## Route and blocker
- Route announced: `next` → Build T-2 (R-2 `status_label`) is the next workflow step.
- **Blocker:** the user did not authorize changes to original code, tests, requirements or acceptance evidence, so I stopped Build T-2 before any business-code edit. No Scope/Build/Verify/Deliver records were changed and no completion was recorded.
- Work done instead: the fault-detection check the user authorized (Verify-side, isolated copies).

## Actions and writes
1. Read Skill references: SKILL.md, orchestration.md, workflow.md, next-workflow.md, write-scope.md, feature-selection.md.
2. Ran read-only helpers `feature-context.py resolve` and `feature-status.py`, and read the feature records, `src/formatting.py` and `tests/*.py`.
3. **Project write:** appended one local rule, `/scratch/`, to `.agent-workflow/.gitignore` after the managed block (the block itself is unchanged), as write-scope.md requires. This is the only tracked-file change (`git diff --stat`: 1 insertion). It is not committed.
4. **Project write (ignored scratch):** created `.agent-workflow/scratch/RESUME-001/mutation-y674VT/` with `mktemp` under an explicit parent. `git check-ignore` confirmed it is ignored by the new rule. Contents:
   - `original-run.log`: suite run on the original tree.
   - `m1-preview-limit-12/{src,tests,fault.diff,run.log}`
   - `m2-receipt-shares-preview-limit/{src,tests,fault.diff,run.log}`
   Tests in both copies were compared with `diff -r` against the original `tests/` and were identical. No assertion was changed or weakened.
5. This assessment file, outside the project (authorized).

Nothing was deleted. The faulty copies and their logs are kept in place.

## Tests (command: `python3 -m unittest discover -s tests -v`)
| Tree | Fault | Result |
|---|---|---|
| Original (HEAD 5179ad2) | none | 13 ran, OK, RC=0 (run twice: before and after the copies) |
| m1 | `PREVIEW_LIMIT = 8` → `12` | FAILED (failures=4), RC=1: `test_longer_than_eight_keeps_first_eight`, `test_nine_characters_drops_last`, `test_counts_python_unicode_characters`, `test_receipt_still_twelve_while_preview_is_eight` |
| m2 | `receipt_id` slices `[:PREVIEW_LIMIT]` instead of `[:RECEIPT_LIMIT]` | FAILED (failures=4), RC=1: `test_legacy.test_receipt_stays_twelve`, `test_receipt_still_twelve_while_preview_is_eight`, `test_receipt_keeps_value_between_preview_and_receipt_limits`, `test_receipt_does_not_follow_preview_limit` |

The copies were run with cwd = copy root and `PYTHONDONTWRITEBYTECODE=1`. The tracebacks point at the copy paths, and the failures appear only in the copies, which shows the faulty `src` was the code imported.

Discrepancy with recorded evidence: R-1 AC7 manual evidence says "receipt-uses-preview-limit mutant fails 3 tests". I observed 4 failures for m2. The extra one is the legacy `test_receipt_stays_twelve`, so the earlier count may have covered only `test_preview.py`, or the earlier mutant was different. The preview-stays-12 count (4) matches. I did not edit the recorded evidence.

## Proof limits
- Only two hand-seeded single-point faults were tested. This is not a mutation-score or coverage claim. Other faults were not tried, such as limit 7/9, off-by-one slicing, `RECEIPT_LIMIT` changes, or `receipt_id` hard-coding 8.
- m1 is caught only through inputs longer than 8 characters. The ≤8 tests (7, 8, empty) pass under limit 12 by design, so they add nothing to detecting this fault.
- `test_no_io` patches only `builtins.open`/`print`. It does not prove there is no other I/O. The no-mutation test is trivial for immutable `str`.
- Results hold for the local `python3` on this darwin host, at HEAD 5179ad2 only. They say nothing about callers outside the project.
- These runs are exploratory scratch evidence. They are not canonical verification, acceptance or delivery evidence, and nothing was written to `verification.json`.
- The ignore rule and scratch are local; being ignored is not a sharing approval.

## Not done
- No T-2/R-2 implementation, no check/validate run for delivery, no record rendering, no commit/push/archive/delivery, no network/MCP/browser, no subagents. The Skill installation, settings and permissions were not modified.

## Next eligible action
Authorize Build T-2 (`/dev next implement T-2 --feature RESUME-001`, or `develop RESUME-001`). Optionally decide whether to keep or revert the `/scratch/` ignore line and the scratch attempt directory.
