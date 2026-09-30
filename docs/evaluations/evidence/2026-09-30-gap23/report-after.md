# STORE-001 delivery report — Member discount with preserved checkout contracts

Delivered requirement baseline: **v2** (CHG-001 applied from v1; decision D-001 approved). This is unchanged by the repair below.
Current tested code commit: `50e53f8f721ccc8929934e9ee270bfd27cc42ddf` (FIX-001 repair). Only `.agent-workflow/**` records were uncommitted when the tests ran. The repair's records are committed afterwards in a records-only commit, which is the HEAD passed to `revise.py verify`. The `src/` tree at 50e53f8 is byte-identical to the originally delivered commit 1468777 (`git diff 1468777 50e53f8 -- src` is empty). The only other code difference is one added test.
Report updated: 2026-09-30, after the test runs below. Test times are the recorded run times, not the writing time.
Closure checkpoint (2026-09-30T03:38Z, new session, HEAD `32647834111ce306ea143d86c336632e9fa36087`): HEAD differs from 50e53f8 only in `.agent-workflow/**` records (`git diff 50e53f8 HEAD -- src tests` is empty). Re-ran read-only checks without re-running tests: `verify-inputs.py` (only issue: quality-report revision differs from HEAD, explained by the records-only commit), `validate-feature.py --stage check` → FEATURE_VALID, `audit-delivery.py` → DELIVERY_EVIDENCE_CURRENT, and `verification.py status` → 36/36 rows passed (32 automatic, 4 manual via Agent technical inspection) at digest 78cf5c98…. Also re-inspected the FIX-001 diff and the current `Checkout.place_order`.

## Repair after v2 delivery — FIX-001 (current)

**Context.** This is a synthetic exercise. After v2 was delivered at 1468777, commit `723a914` ("test fixture: inject duplicate inventory regression") deliberately injected a regression. It is handled as a real Repair input. It is not a defect that escaped the original v2 delivery: the v2 delivery was verified at 1468777 without this line.

- **Observed at 723a914:** `python3 -m unittest discover -s tests` gave **Ran 31, failures=2, errors=2**.
  - Errors, `ValueError: insufficient stock` from `checkout.py:12` via `Inventory.reserve`: `ExistingTests.test_repeat_is_cached` and `MemberCheckoutTests.test_repeat_returns_original_receipt_despite_different_input`.
  - Failures, stock decremented again on a cached repeat: `AtomicCheckoutTests.test_decline_unchanged_then_retry_succeeds_once` (stock 0 != 1) and `MemberCheckoutTests.test_repeat_member_receipt_not_replaced_by_non_member_repeat` (stock 1 != 2).
- **Expected:** confirmed R-CHECKOUT AC4/AC5 (baseline v2, unchanged from v1). A repeated successful request ID returns the same original receipt, with no charge, no reservation and no replacement, even if the repeated input differs or is invalid.
- **Root cause:** `self.inventory.reserve(lines)` was added inside the cached-receipt branch of `Checkout.place_order`, before `return self.receipts[request_id]`.
- **Classification:** `implementation_defect`. Requirements, the PRD, CHG-001 and D-001 did not change, and no revision was needed.
- **Resolution (50e53f8):** removed that line. Added the regression test `MemberCheckoutTests.test_repeat_with_available_stock_has_no_effects`, which covers the silent symptom: repeats that fit in stock, member and non-member, with a full snapshot of stock, charges, charge_count and receipts. The new test failed before the code change (failures=1) and passed after.
- **Fix record:** `fixes.json` FIX-001, status `verified`, requirement R-CHECKOUT, task T-2. Regression tests: `tests/test_member_checkout.py::MemberCheckoutTests` and `tests/test_existing.py::ExistingTests`. Tested revision 50e53f8.
- **T-2 wording** already required "no further charge/reserve". Task meaning did not change, and the task semantic review is still current (digest 250367f8…).

### Current verification evidence (50e53f8)

- Quality gate `unit`: `python3 -m unittest discover -s tests -v` (Python 3.9.6). verification.py run at 2026-09-30T03:15:26Z on 50e53f8: **Ran 32 tests, OK**.
- verification.json: 36 rows, all **passed** at digest 78cf5c98…
  - 32 automatic rows: 31 behavior rows plus the gate row. The coverage notes for R-CHECKOUT:5 and B-7 now cite the new test.
  - 4 manual rows (R-PRESERVE:4/5/6, B-10): re-recorded as **Agent technical inspection**, not user confirmation. Evidence: an empty `src/` diff against 1468777; preserved files still byte-unchanged since base 93bc254; the import/I-O grep; and the passing unit gate.
- Historical regression review: 1 candidate (STORE-001:FIX-001). Disposition `retest`, with the planned checks above and a `passed` result bound to review digest da8e5f05….
- Module dossier `storeflow`: re-reviewed twice. First before the edit, describing the injected defect. Then after the fix at 50e53f8, with the corrected behavior; status current.
- `validate-feature.py --stage check`: **FEATURE_VALID**. `audit-delivery.py`: **DELIVERY_EVIDENCE_CURRENT**.

### Failures and recovery during this repair (preserved)

- The first develop validation was blocked by a stale module context (`storeflow`, caused by the 723a914 change). Recovered by re-reviewing the dossier against current code before editing.
- The first check validation reported stale historical-regression and task-semantic reviews:
  - The regression review was stale because of the new FIX-001 candidate. Recovered with a `retest` disposition.
  - The task review was stale because I had appended a line to T-2 `test_evidence_history`, a field included in the semantic digest. Recovered by restoring `tasks.json` byte-for-byte from git (task meaning never changed). FIX-001 holds the repair evidence instead.

## Original v2 delivery (historical, commit 1468777)

The following was the evidence for the v2 delivery before the injected regression. It is kept as history. The current evidence is above.

| Source | Role | Status |
|---|---|---|
| `sources/prd-original.md` (= `prd-v1.md`, sha256 85b384e3…) | Approved v1 PRD | Unchanged; 10% / 2000 values superseded only for the member-discount percent/cap |
| `prd-v2.md` → `sources/revisions/21f36dc2…md` (byte-identical) | Approved revision v2 (product owner approval stated in the file and confirmed by the user in the delivering session) | Registered as SRC-03 |
| `revisions/CHG-001.json` (sha256 179eca8c…) | Applied revision proposal, base v1 → v2 | Registered as SRC-02 |

API and Figma: not_applicable (PRD line 12: no GUI/API/Figma).

CHG-001 changed only R-PREVIEW `statement` and `acceptance_criteria[1]`: member discount = 15% of subtotal, floored to integer cents, capped at 1200 cents per order (was 10% / 2000). R-CHECKOUT charges the shared preview policy.

| Requirement | Tasks | Outcome |
|---|---|---|
| R-PREVIEW | T-1 | `pricing.MEMBER_DISCOUNT_PERCENT=15`, `MEMBER_DISCOUNT_CAP_CENTS=1200`; `storefront.preview(lines, member=False)` |
| R-CHECKOUT | T-2 | `Checkout.place_order(request_id, lines, member=False)` charges `pricing.quote(...)["total_cents"]`; the cached receipt is returned before any validation (restored by FIX-001) |
| R-ATOMIC | T-3 | Aggregated per-SKU stock pre-check before `Inventory.reserve`; stock released on any `ledger.charge` exception; receipt cached only on success |
| R-PRESERVE | T-1, T-4 | `calculate_total`/`export_subtotal` stay gross; catalog, receipts, payments, inventory, legacy_export and `tests/test_existing.py` are byte-unchanged since base 93bc254 |

All four tasks are done. D-001 approved (chosen B = v2).

Historical runs:
- verification.py run at 2026-09-30T03:08:38Z and project.py check at 2026-09-30T03:09:10Z, both on 1468777: Ran 31 tests, OK.
- Red run before implementation: 5 failures and 15 errors.
- Mutation probes (including "cache check after empty") failed the suite. An ad-hoc helper defect initially misreported two mutants; this was corrected.
- Earlier T-1 run: 16 tests OK on v1 values (historical v1 evidence only).

## Limits and residual risk

- `member` is not type-checked. Non-boolean truthy values behave like True. The PRD specifies a boolean input and no validation, so none was invented.
- `Inventory.reserve` is still non-atomic when called directly. Atomicity is guaranteed only through `Checkout.place_order`.
- The receipt cache is per `Checkout` instance and in memory only, as the README specifies. There is no persistence or concurrency protection.
- No CI or pinned Python version exists. Evidence comes from the local system python3 3.9.6.
- There is no GUI, API or device surface, so no manual UI acceptance applies.

## Conclusion

At this report checkpoint, the current requirement, task, decision, fix, source and verification evidence supports re-delivering baseline v2 with FIX-001 repaired. The code was tested at 50e53f8 and is unchanged at records-only HEAD 3264783. Formal completion is recorded after this report is reviewed, in `spec/requirements.json`: see `feature.status`, `feature.status_note` and `feature.baseline.deliveries`. The v2 delivery at 1468777 remains as a historical delivery entry. No push, PR or archive is part of this delivery.

No product, code or test items are unresolved. No subjective user acceptance was collected. None applies (no GUI, API or device surface), and none is claimed. The manual rows are Agent technical inspection only.
