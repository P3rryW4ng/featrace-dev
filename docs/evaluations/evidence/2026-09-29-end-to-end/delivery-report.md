# Delivery report — E2E-0531 本地查询快照 (local query snapshot)

Report written 2026-09-29 (after test run; see test time below). Workflow: FeatraceDev 0.5.31, route Requirement → Scope → Build (serial) → Verify → Deliver.

## Delivered revision

- Base Git HEAD: `aa4eab00f5f85fa103b7b94345a7c071a6d05a2d` (not committed; delivery is an uncommitted worktree).
- Changed paths (all within impact `allowed_paths`; no excluded changes), SHA-256 at test time:
  - `src/catalog/query.py` fc0fb11aeea028ce468c43d0dc8853c631e6452a4892b62a7632edb64bf2364a (modified: +`product_snapshot`)
  - `src/audit/summary.py` 9f1813a930d1f1cbac23973f3a340a88c27d12945ef069069b877c2798bb85ee (modified: +`event_snapshot`)
  - `tests/test_product_snapshot.py` b41ab5dff8956bd0b203ab5c9553d6d3f75832c8e747264478e2d520e4aa1b61 (new)
  - `tests/test_event_snapshot.py` b5364b22accc33075385e59c9df413067c922fd5e282d1dcc409efbbaf41e276 (new)
  - `tests/test_preserved_behaviour.py` eb821a44f3dd95a8da957d83a0eba830cc631649fa78735b87670d65bc383967 (new)
- Unchanged and verified: `src/shared/formatting.py` (blob bc5e3e41 = HEAD), `tests/test_legacy.py`.
- Impact digest at check: 4654c9e84b24f2cedd945899847f1dd4a4229c40b74a71974b0e5d2c757263f5.

## Sources

- `sources/prd-original.md` sha256 321e4272…c98d45, byte-identical to the supplied input PRD; fully inventoried (U-1..U-8, S-1..S-14; S-14 excluded as acceptance-method statement). Full attributed PRD review recorded.
- API: not_applicable (local function extension, no backend). Figma: not_applicable (no UI; assertion-verifiable).

## Scope

Capability `local-query-snapshot` (user confirmed): catalog = owner (product snapshot), audit = owner (event snapshot), shared = provider (unchanged 12-char receipt formatter). Module dossiers catalog/audit/shared reviewed before and refreshed after edits (current). Historical regression review: 0 candidates (no prior verified fixes in the project). Task semantic review recorded for T-1..T-3. Build strategy: serial (two independent slices, each a single small stdlib function; worktree-pair overhead outweighed benefit).

## Requirements and tasks

| Requirement | Outcome | Task |
|---|---|---|
| R-1 product_snapshot shape/order/no dedup | delivered | T-1 |
| R-2 ordered product validation, first error, decimal context untouched | delivered | T-1 |
| R-3 validate-then-filter, invalid always reported | delivered | T-1 |
| R-4 {id, label=name[:8], price 2 decimals} | delivered | T-1 |
| R-5 event_snapshot shape/order/counts | delivered | T-2 |
| R-6 ordered event validation, strict timestamp | delivered | T-2 |
| R-7 inclusive optional window, out-of-window not errors | delivered | T-2 |
| R-8 dedup after validation/window | delivered | T-2 |
| R-9 receipt_for keeps 12 chars | preserved | T-3 |
| R-10 all_product_ids / legacy_summary unchanged | preserved | T-3 |
| R-11 pure, non-mutating, deterministic; missing=invalid, extras ignored | delivered | T-1, T-2 |

All tasks done. Decisions: none (no conflicts or pending product choices). Fixes: none recorded.

## Checks

- Command (README): `python3 -m unittest discover -s tests -v`, run via `verification.py run` → project check runner. Tested at 2026-09-29T08:37:28Z on base HEAD aa4eab0 + the diff above: **35 tests, OK** (4 legacy + 17 product + 12 event + 2 preserved).
- Verification list: 35/35 rows passed. 33 automatic rows mapped to gate `unittest` with per-row assertion coverage. 2 manual rows passed by **Agent technical inspection** (not user confirmation):
  - R-9:1: `git diff -- src/shared/` empty, blob hash equals HEAD; receipt assertion passed in the gate run.
  - B-3: AST/grep inspection of both changed modules found no I/O calls and no module-level mutable state (only imports, compiled regexes, an int constant). Non-mutation, repeatability and result isolation are asserted by tests.
- `validate-feature.py --stage check`: FEATURE_VALID. `audit-delivery.py`: DELIVERY_EVIDENCE_CURRENT. `verify-inputs.py`: only the expected review of the worktree changes (done above).

## Technical interpretations (within the PRD's authorisation of technical choices)

- Price formatting uses string arithmetic (strip leading zeros, pad/truncate the fraction to 2 digits). The fraction never exceeds 2 digits after validation, so there is no rounding, and the decimal module is never used.
- "Valid calendar instant" is checked by building a `datetime`. Consequently year 0000 and second 60 (leap second) are rejected. The PRD does not mention either case.
- Test IDs are recorded as `tests.<module>.<Class>.<method>`. The discover run prints them without the `tests.` prefix; both refer to the same methods.

## Limits

- The code is not committed, and nothing was pushed or archived (per instruction). The delivered identity is base HEAD plus the file hashes above.
- Root `.gitignore` ignores `.agent-workflow/`, so the workflow records are not shareable through Git as-is. setup-workflow-git reported this, and it was left unchanged pending project policy.
- The checks are unit assertions plus Agent inspection. No independent reviewer was used. Input types outside the PRD contract (for example, non-dict items) are untested by design.

## Conclusion

All requirements, tasks and verification rows are supported by current evidence for the worktree above. Delivery is complete locally, with the code uncommitted.
