# Round 2 assessment — RESUME-001

## Actual route

`/dev next --feature RESUME-001` via the native Skill tool (personal `dev` Skill), serial, single Agent.
Route: Requirement/revise (approved prd-v2) → Scope → Build (serial) → Verify → Deliver.

## Recovered facts (from project records and Git only)

- HEAD was `5179ad2`, worktree clean. Baseline v1 (8-char preview limit) confirmed; no decisions; no revisions.
- T-1 (R-1, 8 chars) done at `b7cfbe9`; unit gate 13/13 at 2026-09-29T10:25:33Z. T-2 (R-2 status_label) planned; `status_label` returned text unchanged; R-2 rows not run.
- Feature status provisional; verification: 11 passed, 4 not run. Module formatting owner; API/Figma not_applicable.
- No round1 assessment or prior conversation was used.

## Changes

Requirement:
- D-001 (approved requirement_change) recorded from the product-owner approval in `inputs/prd-v2.md` plus the user's message.
- CHG-001 proposed with prd-v2 as preserved source (`sources/revisions/87a25e88….md`) and applied → baseline v2. It changes R-1 title, statement and acceptance criteria to 6 characters. Length 7 is now truncated. Receipt 12 and R-2 are unchanged.
- Intake: the old v1 aspects are kept with `superseded_by: CHG-001`. CHG-001.json is registered as source SRC-02/U-5/S-7. Full PRD review re-recorded. `sources/prd-original.md` is untouched.

Scope:
- impact.json: behaviors B-1..B-4 rewritten for v2 and R-2. `tests/test_status.py` added to allowed paths. `base_revision` is still 199b3b7.
- T-1 reopened. Its v1 revision and evidence are kept as `prior_*` fields. Task semantic review re-recorded.
- Regression sync found 0 candidates. Module dossier refreshed at 40ace5f.

Build (commit `40ace5f`):
- `PREVIEW_LIMIT = 6` and `status_label = text.strip().upper()`.
- Rewrote `tests/test_preview.py` for boundaries 5/6/7, Unicode and receipt independence.
- New `tests/test_status.py`. `tests/test_legacy.py` is unchanged.

Records commit `6bdcb04` is documentation only.

## Evidence

- Red run first: 20 tests, 10 failures. Then green: 20/20.
- `verification.py run` unit gate (`python3 -m unittest discover -s tests -v`) at 40ace5f, 2026-09-29T10:31:11Z: Ran 20, OK.
- In-process mutation check caught every mutant: limit 8, limit 7, strip-only, upper-only, ASCII-only upper.
- 16/16 verification rows passed: 11 automatic, 1 gate, and 4 manual rows recorded as Agent technical inspection.
- `validate-feature.py --stage check` returned FEATURE_VALID. `audit-delivery.py` returned DELIVERY_EVIDENCE_CURRENT, and again after the records commit.
- Delivery report `.agent-workflow/features/RESUME-001/delivery-report.md` was written, then fully read in a separate step and compared with current records. After that, `revise.py verify` registered the baseline v2 delivery at 40ace5f, and the feature status was set to complete.
- Final status: baseline confirmed=2, verified=2; tasks 2/2; verification passed=16.

## Limits

- There was no human or product-owner observation of v2 behavior. Manual rows are Agent inspection, not user confirmation.
- Mutation checks were ad hoc and are not persisted as a gate.
- The validators check structure and freshness, not semantic truth.
- Some files are git-ignored by the project's `.agent-workflow/.gitignore`, so they exist only locally and are not in any commit:
  - `project-baseline/quality-gates.json` (updated test_ids to include the status tests)
  - the preserved source copies under `sources/`
- The delivery report's conclusion is worded conditionally (written before the read and registration). Its hash is bound by `revise.py verify`, so it was not edited afterward.
- A transient proposal JSON was briefly written to `/tmp` and then deleted.
- v1 results are kept as history and are not claimed as v2 evidence. No push, PR or archive.
