# Round 3 assessment — STORE-001 post-delivery regression repair

Invocation: the installed `dev` Skill via the native Skill tool, `next --feature STORE-001`. One Agent, no subagents, no push.
Project: `/private/tmp/featrace-storeflow-0534-8306iq4r/project`.

## Actual route

`next` resolved STORE-001 ("Member discount with preserved checkout contracts"). Its recorded status was `complete`, with 36 stale verification rows. The observed behavior differs from confirmed behavior, so the route was **Repair (fix) → Verify (check) → Deliver**. Requirement and Scope were not re-entered, because the requirement meaning did not change.

1. Repair:
   - `record-fix.py` registered FIX-001 and moved the feature from complete to provisional.
   - `regression_review.py sync` found 0 candidates at that point.
   - Develop validation was **blocked** by a stale `storeflow` module dossier. I re-reviewed the dossier against the current regressed code, documenting the injected defect, and develop validation then passed.
   - Wrote a regression test and saw it fail (red), then made the one-line code fix and the full suite passed (green).
   - Committed the code as `50e53f8`, then re-reviewed the dossier again for the fixed code.
2. Verify:
   - `verify-inputs.py`, then `verification.py sync`. I extended the coverage notes of the R-CHECKOUT:5 and B-7 rows to cite the new test.
   - `verification.py run`: 32 automatic rows passed.
   - Recorded the 4 manual rows as Agent technical inspection.
   - Set FIX-001 to `verified`.
   - Check validation first failed on stale regression and task reviews (see Failures). After recovery: `validate-feature --stage check` FEATURE_VALID, and `audit-delivery` DELIVERY_EVIDENCE_CURRENT.
3. Deliver:
   - Updated `delivery-report.md`, keeping the original v2 delivery as a historical section.
   - Committed the records as `3264783`.
   - `revise.py verify --code-revision 3264783`: REVISION_VERIFY baseline v2. This is a second v2 delivery entry; the original 1468777 entry is kept.
   - Did a separate full Read of the saved report and compared it with the current records.
   - Then, in a separate operation, set `status: complete`, rendered the views, and re-ran check and audit (both passed). Committed as `0bfd351`.

## Root cause

Fixture commit `723a914` added `self.inventory.reserve(lines)` inside the cached-receipt branch of `Checkout.place_order` (`src/storeflow/checkout.py`), before `return self.receipts[request_id]`. A repeated request ID therefore runs inventory reservation on the repeated lines:
- If the stock doesn't fit, it raises `insufficient stock`.
- If it fits, it decrements stock again while still returning the cached receipt.

This contradicts confirmed R-CHECKOUT AC4/AC5 in baseline v2 (unchanged from v1). It is a deliberately injected post-delivery regression, not a defect that escaped the original v2 delivery: v2 was verified at 1468777 without that line.

## Fix record

`fixes.json` FIX-001:
- `kind: implementation_defect`, `status: verified`.
- `requirement_ids` R-CHECKOUT, `task_ids` T-2.
- It records expected, actual, reproduction, root cause and resolution, the changed paths, and the red/green evidence.
- `tested_revision` 50e53f8. `regression_test_ids`: `tests/test_member_checkout.py::MemberCheckoutTests` and `tests/test_existing.py::ExistingTests`.

Other records:
- No change to requirements meaning, the PRD, CHG-001, D-001 or task wording.
- The historical regression review has 1 candidate, STORE-001:FIX-001, with a `retest` disposition and a passed result bound to the current review digest.

## Tests

- **Before the fix (723a914):** Ran 31, **failures=2, errors=2**, the same as reported:
  - errors: `test_repeat_is_cached` and `test_repeat_returns_original_receipt_despite_different_input`;
  - failures: `test_decline_unchanged_then_retry_succeeds_once` and `test_repeat_member_receipt_not_replaced_by_non_member_repeat`.
- **New test** `MemberCheckoutTests.test_repeat_with_available_stock_has_no_effects`: covers repeats that fit in stock, member and non-member, and checks a full snapshot of stock, charges, charge_count and receipts. It failed before the fix and passed after.
- **After the fix:** `python3 -m unittest discover -s tests -v`: **Ran 32, OK**. This came from `verification.py run` (gate `unit`, 03:15:26Z on 50e53f8), and I re-ran it after the final status change: still 32 OK.
- `src/` at 50e53f8 is byte-identical to the originally delivered 1468777. No existing assertion was weakened.

## Gates

| Gate | Result |
|---|---|
| validate-feature --stage develop | Initially ERROR (stale module context); FEATURE_VALID after the dossier re-review (one warning for the then-unresolved fix) |
| verification.json | 36/36 passed at digest 78cf5c98… (32 automatic, 4 manual via Agent technical inspection, not user confirmation) |
| validate-feature --stage check | Initially 2 errors (stale reviews); FEATURE_VALID after recovery, and again after the status change |
| audit-delivery | DELIVERY_EVIDENCE_CURRENT |
| revise.py verify | REVISION_VERIFY baseline v2 at 3264783 |
| Module dossier / task semantic review / regression review | current / current (unchanged digest 250367f8…) / 1 retest, passed |

## Is delivery completion still justified?

Yes, for baseline v2 with FIX-001 repaired:
- All requirements are confirmed and all 4 tasks are done.
- The only fix is verified; there are no pending decisions or clarifications.
- API/Figma are not_applicable with reasons.
- All verification rows are current and passed.
- The delivery report was saved, fully read back and compared before the status change.

Limits:
- The 4 manual rows rest on Agent inspection, not an external observer.
- The report's conclusion sentence still describes the registration and status update as "remaining". I did not edit it afterwards, because `revise.py verify` recorded the report's hash; the registration and status are recorded in `requirements.json`.
- The PRD and prd-v1/prd-v2 files are unchanged, which I checked with git (`sources/` is gitignored; `verify-inputs` hashes match the recorded ones).

## Failures and recovery

1. **Develop gate blocked:** the `storeflow` module dossier was stale because 723a914 changed `checkout.py`. Recovered by re-reviewing it against the actual code before editing, then again after the fix.
2. **Check gate, regression review stale:** the verified FIX-001 became a new candidate. Recovered with a `retest` disposition and a result.
3. **Check gate, task semantic review stale (my own mistake):** I had appended FIX-001 evidence to T-2 `test_evidence_history`, a field included in the semantic digest. My first revert left an empty `test_evidence_history: []` field, which still changed the digest. Recovered by `git checkout` of `tasks.json`, which gave a byte-exact restore and no change in digest. I did not fabricate a semantic review.
4. Minor: a `cat -A` command is not supported on macOS; I re-ran it without the flag.

## Commits (local only)

- `50e53f8`: code fix and test.
- `3264783`: FIX-001, verification, regression review, dossier and delivery report.
- `0bfd351`: feature status complete.

Scratch was used only in the ignored `.agent-workflow/scratch/STORE-001/attempt-3/` (dossier candidate JSON).

## Elapsed time

From `date +%s` at start (1790738003, 11:13:23 CST) to the last commit (1790738305, 11:18:25 CST): **302 s ≈ 5 min 2 s**. Writing this assessment adds about 1 minute.
