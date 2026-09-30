# Assessment — RESUME-001 controlled requirement revision (PRD v2)

Date: 2026-09-29. Skill: `featrace-write-scope:dev`, called through the native Skill tool with `next --feature RESUME-001`.
Project: `/private/tmp/featrace-write-scope-0534-r714e38o/revision/project` (HEAD `5179ad2`, branch main).

## Route
Requirement/revise, then a Scope refresh (tasks, impact, regression and verification list). I stopped before Build as instructed. I did not edit business code or test code, and I ran no tests.

## Facts recovered from project records
- Baseline v1 was confirmed with R-1 = preview limit 8 and R-2 = status_label strip plus upper. The feature status was provisional.
- T-1 (8-character preview) was done at `b7cfbe9`. The unit gate passed 13/13 there. T-2 (R-2) was still planned.
- There were no decisions, no revisions and no pending proposals. The verified baseline version was 0.
- The v2 input `inputs/prd-v2.md` has sha256 `87a25e88…8a82`. It replaces only R-1's limit, 8 → 6, and says a length-7 input must be truncated. It keeps receipt_id at 12 and leaves R-2 unchanged. The product owner approved it, as the user stated.

## Actions taken (all inside the project)
1. `.agent-workflow/.gitignore`: added a local `/scratch/` rule after the managed block. The managed block is unchanged.
   - Scratch folder: `.agent-workflow/scratch/RESUME-001/revise-v2-attempt1/`. Git ignores it (checked with `git check-ignore`).
   - The proposal input `CHG-proposal.json` is kept there.
2. `decisions.json`: added **D-001**, status approved.
   - Chosen value: a 6-character limit, with ≤6 unchanged, empty unchanged and length-7 truncated.
   - It is classified as a requirement_change, not a v1 defect.
   - Preserved behaviour is listed: receipt_id 12, R-2 unchanged, stdlib only, no mutation or I/O.
3. `revise.py propose --source inputs/prd-v2.md` created **CHG-001**. This patches three R-1 fields:
   - title
   - statement
   - acceptance_criteria (AC0, AC1, AC5 and AC6 changed; AC2–AC4 unchanged)
   The helper stored the v2 bytes, content-addressed, at `sources/revisions/87a25e88….md`. The `sources/**` folder stays git-ignored under the existing source-sharing policy.
4. `revise.py apply --revision CHG-001` succeeded, so the confirmed baseline is now **v2**. Verified is still 0 and nothing is pending.
5. Reading records (`spec/prd-intake.json`):
   - Registered SRC-02 (the v2 copy) and SRC-03 (`revisions/CHG-001.json`), with units U-5 to U-7.
   - Marked the old aspects `superseded_by: CHG-001`, keeping their original target text: S-2 statement, AC0 and AC1; S-3 AC5; S-6 R-1 AC6.
   - Added new items: S-7 (the v2 limit), S-8 (preserved receipt behaviour and unchanged R-2), S-9 (the new AC6 text from CHG-001), and S-10 (excluded as background).
   - `requirements.json` now carries the matching sources, source_item_ids and prd_paths. `sources/prd-original.md` is unchanged (sha256 `57fac7d3…`).
6. Recorded a full PRD review with `review-prd.py --stage develop`.
7. T-1 reopened (status → planned), with its title and description updated for the 6-character limit and the 5/6/7 boundaries.
   - I removed the old `implementation_revision` and `test_evidence` fields from the task. Their content is now summarised in `history_note`, labelled as proof for v1 only.
   - The v1 result history itself is still kept in `verification.json`.
   - Ran `task_review.py sync`, then `review` for T-1 against R-1.
8. `impact.json`:
   - Updated B-1 to the 6-character limit and adjusted B-2's wording. Both are now planned.
   - Corrected the shared_state evidence, which wrongly said "both 12".
   - base_revision stays `199b3b7`, the current delivery cycle.
9. `regression_review.py sync`: 0 candidates.
10. `verification.py sync`:
    - Rows whose meaning changed got new IDs and are `not_run`.
    - Rows that were passed under v1 are now marked `stale` (R-1 AC2–AC4, B-3, and the unit gate). 6 retired rows keep their old history.
    - No v1 pass is counted as v2 evidence.
11. Regenerated the Markdown views with `render-workspace.py`.

## Checks run (structural checks only; no tests)
- `validate-feature.py --stage develop` → `FEATURE_VALID`, with the warning "baseline v2 is confirmed but delivery has not been verified".
- `feature-status`: tasks done 0/2, baseline confirmed=2 and verified=0, verification not_run=10 and stale=5, no blockers.
- `git diff --quiet HEAD -- src tests` shows `src/` and `tests/` are untouched.

## Not done / limits
- No business-code or test-code edits. `src/formatting.py` still has `PREVIEW_LIMIT = 8`, and `tests/test_preview.py` still asserts the 8-character behaviour. Both will conflict with v2 until the next turn.
- No tests were run. v1's 13/13 at `b7cfbe9` is historical evidence only and does not verify v2.
- No commit, push, archive or delivery. The feature stays provisional.
- The v2 R-1 rows are currently mode=manual with no gate mapping. They need to be mapped to the new tests once those tests exist.
- The validators only check structure. The semantic reviews are attributed Agent reviews, not independent verification.
- Nothing was written outside the project, apart from this assessment file.

## Next step (separate turn)
Develop T-1 for v2: set the limit to 6 and replace the preview boundary tests with 5, 6 and 7 characters. T-2 (R-2) is still planned. After that, map the verification rows, then run check and bind the result to baseline v2.
