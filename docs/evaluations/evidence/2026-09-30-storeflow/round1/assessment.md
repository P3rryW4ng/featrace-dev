# STORE-001 round 1 — assessment (partial milestone: R-PREVIEW only)

Project: `/private/tmp/featrace-storeflow-0534-8306iq4r/project`
Skill: installed `dev` Skill at `/Users/mac/.claude/skills/dev`, run through the native Skill tool with `prd …/prd-v1.md --feature STORE-001`.
Result: **provisional / partial**. Only T-1 (R-PREVIEW) is implemented. No Verify (`check`) or Deliver stage was run, and nothing is claimed as delivered.

## Observed route

1. **Entry and selection.** `feature-context.py list` returned no features. The user supplied the ID STORE-001, and no feature directory existed yet.
2. **Requirement stage.**
   - Ran `setup-workflow-git.py`, which created `.agent-workflow/.gitignore`.
   - Ran `init-feature.sh STORE-001 prd-v1.md`. The copied source `sources/prd-original.md` is byte-identical to `prd-v1.md` (checked with `cmp`).
   - Built the intake: 7 reading units (U-1..U-7) and 17 source items (S-1..S-17). S-1, S-3 and S-17 are excluded as title, approval provenance and delegation background. All other items map to aspects with verified exact `target_text`.
   - Wrote 4 confirmed requirements: R-PREVIEW, R-CHECKOUT, R-ATOMIC, R-PRESERVE.
   - Set API and Figma to `not_applicable`, citing PRD line 12.
   - Recorded the PRD semantic review with `review-prd.py` (full review, not draft). No decisions were needed and no product question was asked.
3. **Scope stage.**
   - Created a module catalog with one module, `storeflow` (roots `src/storeflow` and `tests`).
   - Ran `module_context.py plan`, then `review` of a dossier using the digest captured by plan, then `graph`.
   - Ran `feature_scope.py suggest`, then `set`: capability `member-discount`, with `storeflow` as owner.
   - Wrote tasks T-1..T-4 with allowed paths and dependencies (T-2 depends on T-1; T-3 on T-2; T-4 on T-2 and T-3).
   - Wrote `impact.json`: base 93bc254, six mechanisms, behaviors B-1..B-5, and `allowed_paths` limited to the T-1 slice.
   - `regression_review.py sync` found 0 candidates, since there are no historical verified fixes.
   - `task_review.py sync` and `review` covered all four tasks.
   - `validate-feature.py --stage develop` returned `FEATURE_VALID`.
4. **Build stage: serial, T-1 only.**
   - Serial because the user chose it, and T-2 and T-3 depend on T-1 through the shared pricing policy and the same `place_order` code.
   - Wrote the tests first. The red run had 9 errors (`TypeError: unexpected keyword 'member'`) while the 7 existing tests passed.
   - Then implemented the change; the green run passed all 16 tests.
   - After the edit, refreshed the module dossier (plan went stale, then review made it current again). Re-rendered, and develop validation was valid.
5. **Stopped at the requested partial milestone.** T-2, T-3 and T-4 are planned but not implemented. The feature's `status` is `provisional`, with a `status_note`.

## Implementation (T-1)

- `src/storeflow/pricing.py`:
  - Added `member_discount(subtotal_cents) = min(subtotal*10//100, 2000)`.
  - Added `quote(lines, member=False)`, which returns the existing three keys with total = subtotal − discount.
  - `calculate_total` is unchanged and still gross.
  - `quote` is where T-2 is planned to reuse the preview policy, so checkout charges exactly the preview result.
- `src/storeflow/storefront.py`: `preview(lines, member=False)` now returns `quote(lines, member)`. Omitting `member` or passing False gives the previous result.
- Not touched: `prd-v1.md`, `README.md`, `tests/test_existing.py`, `checkout.py`, `catalog.py`, `inventory.py`, `payments.py`, `receipts.py` and `legacy_export.py`. Checked with `git diff 93bc254 --stat`, which was empty for the listed files.

## Checks actually run

These are Python 3.9.6 runs of `python3 -m unittest discover -s tests -v` from the project root, plus the validators.

- **Before implementation:** Ran 16; 9 errors, all in the new tests; the 7 ExistingTests passed.
- **After implementation, working tree:** Ran 16, OK. The `impact.py` digest was `f7ba9baf…1708` both before and after the run.
- **After commit `a7db78b`:** Ran 16, OK. `validate-feature.py --stage develop` returned `FEATURE_VALID`.
- **Mutation checks,** each on a copy in project scratch (since deleted):
  - Removing the cap: FAILED (2 failures).
  - `round()` instead of floor: FAILED (1 failure).
  - Always applying the discount: FAILED (3 failures).

What the new assertions cover (read from `tests/test_member_preview.py`; each asserts exact dicts or values):

- Default, `member=False` keyword and positional False: undiscounted dicts `{10000,0,10000}` and `{30000,0,30000}`.
- `member=True`, 2 books: `{10000,1000,9000}`.
- Floor: 1 pen gives discount 50. A temporary odd price of 1999 gives `{1999,199,1800}`, and the catalog is restored in `finally`.
- Cap: 20000 and 30000 both give discount 2000. 19500 gives 1950, just under the cap.
- The key set is exactly the three keys, total = subtotal − discount, and all values are ints.
- An empty preview is all zero, for both member False and True.
- ValueError, for member False and True, on: an unknown SKU, qty 0, −1, `True` and `1.0`, and a valid line mixed with a bad one.
- Repeated SKU lines are summed: `book×1 + book×1` with member gives `{10000,1000,9000}`, and `pen 1 + pen 2` without member gives 1500.
- `PreserveWithPreviewTests`: for lines whose member discount is 2000, `calculate_total` is 35000 and `export_subtotal` is `{gross_cents:35000}`.

Coverage limits:

- Nothing yet tests member checkout, idempotency with member or invalid repeats, atomicity, or repeated-SKU stock.
- The existing checkout tests only prove that the default checkout path still passes unchanged.
- The `member` parameter is not type-validated. The PRD says only that it is a boolean, and non-bool values fall back to truthiness; this is not tested.

**Validator caveat:** I ran `validate-feature.py --stage check` as a read-only probe, and it returned `FEATURE_VALID` even though 3 of the 4 tasks are `planned`. That validator checks structure, not completion. It is **not** evidence of verification or delivery eligibility. No `verification.json` or quality-gate selection (project baseline) was created, because `check` was deliberately not run.

## Actual writes

All writes are inside the project, plus this file.

- **Committed locally (`a7db78b`, no push):**
  - `.agent-workflow/.gitignore`: the bundled managed block, plus `/scratch/` appended after it.
  - `.agent-workflow/modules/`: `index.json`/`.md`, `storeflow.json`/`.md`, `graph.json`/`.md`.
  - `.agent-workflow/features/STORE-001/`:
    - `spec/requirements.json`, `spec/prd-intake.json`, `spec/spec.md`, `spec/prd-analysis.md`
    - `tasks.json`/`.md`, `task-review.json`/`.md`
    - `impact.json`/`.md`, `regression-review.json`/`.md`
    - `traceability.json`/`.md`, `decisions.json`/`.md` (empty), `fixes.json`/`.md` (empty)
  - `src/storeflow/pricing.py`, `src/storeflow/storefront.py`, `tests/test_member_preview.py`.
- **Ignored and not committed:**
  - `.agent-workflow/features/STORE-001/sources/prd-original.md` (the source-sharing default).
  - `.agent-workflow/scratch/STORE-001/attempt-1/`, which holds `build_records.py` (generator for the requirement and intake records), `storeflow-dossier.json` and `scope.json`. The `mut/` mutation copies were deleted after use.
- **Outside the project:** only `/private/tmp/featrace-storeflow-0534-8306iq4r/round1/assessment.md`.

No global settings, installed Skill files, network, other repositories or sibling attempts were read or written.

## Blockers and remaining work

There is no product blocker. The remaining work is authorized but deliberately paused:

- **T-2 (R-CHECKOUT):**
  - Add `place_order(request_id, lines, member=False)` and charge `quote(lines, member)["total_cents"]`.
  - Return a cached receipt before any validation, even when the later lines or member flag differ or are invalid.
  - Keep `Receipt`/`export_receipt` unchanged.
  - Before editing, expand `impact.json` `allowed_paths` to `checkout.py` and `tests/test_member_checkout.py`.
- **T-3 (R-ATOMIC):**
  - The current code is not atomic. `Inventory.reserve` mutates line by line, so a stock failure partway through leaves earlier lines reserved. A payment decline after reserving leaves stock reduced. Repeated SKUs are checked per line rather than combined.
  - Plan: validate lines and aggregated stock before any mutation, release reserved stock on `PaymentDeclined`, never cache a failed attempt, and allow a retry to succeed once.
  - Needs impact expansion to `inventory.py`.
- **T-4 (R-PRESERVE):** a feature-wide preservation regression across member checkout: gross legacy export, receipt amounts never rewritten, and prices, receipt IDs and the ledger contract unchanged.
- **Before delivery:**
  - After T-2, T-3 and T-4: re-sync the task, impact and history reviews and refresh the dossier.
  - Then run the full Verify (`check`): project baseline and quality-gate selection, `verification.json`, and fresh check evidence.
  - Only after that, Deliver.

## Elapsed time

About 6 minutes by the shell clock: `date +%s` read 1790735074 at start and 1790735433 at commit, so 359 s. Writing this assessment took a little longer.
