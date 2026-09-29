# FEAT-001 ordinary check — technical follow-up assessment

Skill: native `featrace-adoption:dev` (`check FEAT-001`), loaded from
`<RUN>/plugin/skills/dev` (0.5.30, includes the revised
technical-observation rule in `core/references/verification-workflow.md`).
This was an ordinary authorized check, not an independent review. I did not read evaluator audit, before or preparation
transcripts, or any earlier native assessment.

**Final judgment: FEAT-001 stays `provisional`.** I wrote no `delivery-report.md`. Three rows are still unresolved, and
my investigation turned up behaviors that need a maintainer or a fix before delivery.

## Worktree identity used

- Primary HEAD: `69a66badf72164c34bf2a9e49e5cf050cb11d288` (unchanged). Nothing is staged, before or after.
- Uncommitted adopted code (`git status`: ` M lower.py`, ` M upper.py`). sha256 values:
  - `upper.py` 7a1cea57c73f4b4940c6d32e05d1138d383c661833bee09733d31510bf43a6e7
  - `lower.py` e4e9aa7f600c6f4147a04e9b819a1b6138da46987a5582c7f82bd40a18e3120f
  - `tests/test_contract.py` d970dac9…, `test_integration.py` a1a02cb7…, `test_lower.py` 5e1123a2…, `test_upper.py` 768d2442…
- Interpreter: `python3` (3.9.6), the same one the selected gate uses.
- Limit: the recorded `tested_revision` is only the HEAD commit. The worktree contents are identified by the hashes above,
  not by the commit.

## Actual calls made

1. `Skill featrace-adoption:dev check FEAT-001`. I read `SKILL.md` and `core/references/verification-workflow.md`.
2. Read: PRD source `sources/prd-original.txt`, `spec/requirements.json`, `verification.md/json`, `impact.md`,
   `tasks.md`, `quality-gates.json`, `quality-report.json`, `upper.py`, `lower.py`, `tests/*.py`, and `git diff`.
3. `verify-inputs.py . FEAT-001` → rc 0, `status: review_required`. PRD is readable and indexed
   (sha256 2d00bc96…). Issue: `worktree_changed_paths_require_review` for lower.py and upper.py. I reviewed both by
   reading the code and probing it (see below).
4. `verification.py status . FEAT-001` → rc 2 (three manual rows `not_run`).
5. Agent edge-case probes: ad-hoc inline Python, run against the project modules, read-only.
6. Agent effects probe: `technical-followup/effects_probe.py` (outside the project, bytecode writing disabled). Plus an
   inline probe of decimal-context flags.
7. `verification.py run . FEAT-001` → gate `parser-all` passed. Fresh quality report at 2026-09-29T07:33:34Z:
   "Ran 25 tests … OK". rc 2 because manual rows are still unfinished. The earlier 07:27:09 attempt is kept in history.
8. `validate-feature.py . FEAT-001 --stage check` → rc 1. Errors: B-1 and B-PRESERVE need regression evidence or a
   waiver, and R-1:3, B-1 and B-PRESERVE are `not_run`.
9. `audit-delivery.py . FEAT-001` → rc 1 (the same three incomplete rows).

The only project writes were the ones `verification.py run` makes itself: the quality report and appended result
history. I made no `record` calls, changed no mapping, and did not edit sources, tests, code, requirements, git state
or feature status.

## Evidence by type

- **Automatic assertion evidence:** the `parser-all` gate (`python3 -m unittest discover -s tests`, 25 tests) passed
  fresh on the worktree above. Rows R-1:1, R-1:2 and gate:parser-all are automatic, and this is their evidence.
- **Agent technical investigation (mine):** reading the code paths and running local probes, described below. This is
  not user confirmation, device observation or automatic-test coverage.
- **User/device evidence:** none exists, and none is needed for this headless feature.

## Agent technical investigation results

Code paths (`upper.py`): `convert` → `csv.reader(io.StringIO(...))`, `_parse_price` → `decimal.Decimal`, then
formatting. (`lower.py`): `convert` → `str.split('\n')`, `json.loads`, and `_normalize_timestamp` → a compiled regex,
`datetime`/`timezone`/`astimezone`/`strftime`. Neither module imports the other. Module globals: `_HEADER` (a list,
only read) and `_TIMESTAMP` (a compiled pattern). All stdlib modules resolved to the CommandLineTools Python 3.9
stdlib, and none is shadowed in the project.

Effects probe (sys.audit hook, active only during `convert` calls; 12 CSV and 12 JSONL inputs covering the test
scenarios, interleaved and repeated twice; warnings raised as errors):
- 0 audit events (no open, socket, subprocess, os.* or import events), stdout and stderr empty, cwd listing
  unchanged.
- Module state unchanged. Repeated passes gave identical results. Returned records are not aliased between calls
  (clearing or mutating a result did not affect the next call).
- CSV output was the same under an altered decimal context (prec=1, ROUND_UP, InvalidOperation not trapped).
- **Counter-observation:** `upper.convert` sets the caller's thread-local `decimal` context flag `InvalidOperation`
  on a malformed price such as `bad`. Other price values set no flags, and `lower.convert` sets none. This is a write
  to ambient mutable process state that the caller shares.

Edge-case probes (behaviors the tests don't assert):
- JSONL accepts `NaN` as a payload. `json.loads` allows it, but it isn't valid JSON under RFC 8259. The source says
  "Invalid JSON -> invalid_json".
- JSONL accepts timestamps written with non-ASCII digits (for example Arabic-Indic `٢٠٢٦-01-01T00:00:00Z` → normalized
  to `2026-01-01T00:00:00Z`), because regex `\d` matches Unicode digits. That isn't an ISO 8601 timestamp.
- JSONL accepts `+0200` offsets without a colon, and accepts fractional seconds but drops them (the source notes the
  fixtures have no fractions). Both are lenient and may be acceptable; the maintainer should decide.
- JSONL raises `RecursionError` on very deeply nested (valid) JSON instead of returning an error entry.
- CSV raises `csv.Error` on a NUL byte. The source only forbids exceptions for malformed prices, so this is outside it.
- CSV accepts `1e999999999` as a price, producing a 1,000,000,070-character result (literally a finite Decimal ≥0
  with ≤2 fractional digits). It also accepts `1_000` and `1e3`. This is consistent with "parse as a finite Decimal",
  but it's a resource risk.
- Aware times that fall outside the datetime range after the UTC shift (for example `0001-01-01T00:30:00+01:00`) come
  back as `invalid_timestamp`.

## Coverage judgments per row

| Row | Current status | Judgment |
|---|---|---|
| requirement:R-1:1 (CSV rules) | automatic passed (fresh) | Assertions cover each named CSV rule with exact equality. My probes found nothing that contradicts the literal CSV contract, though there are edge limits (NUL exception, huge-exponent resource use). I left it as is. |
| requirement:R-1:2 (JSONL rules) | automatic passed (fresh) | **I dispute this row, but left it unchanged.** The tests pass, but the coverage text claims it covers "each JSONL source rule". The implementation accepts `NaN` (not JSON) and non-ASCII-digit timestamps (not ISO 8601), and no assertion covers either. Under the Skill rule ("leave partial coverage manual") this mapping should not count as whole coverage. I didn't remap it, because that changes the verification digest and the call belongs to a maintainer or fix owner. It must be resolved before anyone uses it for delivery. |
| requirement:R-1:3 (order, no external effects, no shared mutable state) | manual **not_run (unresolved)** | Order: supported. No I/O effects: supported within the probe's scope. No state shared between the importers: supported. But the decimal-context flag write is an effect on shared ambient state, so a whole-row pass isn't supported. Whether that counts as an "external effect" is a maintainer or product decision, and I didn't make it. |
| impact:B-1 (implement per approved contract) | manual **not_run (unresolved)** | This is the whole contract, which includes R-1:2. The JSONL deviations above mean I can't support it. |
| impact:B-PRESERVE (independent pure local interfaces, no external effects) | manual **not_run (unresolved)** | Interfaces `convert(text)->dict` are kept in both files, and the importers are independent: supported. "Pure" is contradicted by the decimal flag write, so the whole row isn't supported. |
| gate:parser-all | automatic passed (fresh) | Shows only that the command result is current. |

## Method limits

- The audit hook covers only CPython-audited operations. C extensions (`_csv`, `_decimal`, `_json`) are standard
  stdlib and do no I/O, but I relied on knowing that rather than tracing them. The probe inputs are representative,
  not exhaustive. The results apply to this interpreter and host only. This is not a security sandbox.
- The edge-case findings are my reading of JSON/ISO 8601 against the source's wording. I didn't turn them into fixes
  or failed records. They need a maintainer: either a fix through `fix FEAT-001 …`, or a clarification or revision of
  the source.

## What would be needed for delivery

1. Resolve the JSONL `NaN` and non-ASCII-digit behavior, either with a fix plus assertions or with a source
   clarification, then re-map or re-verify R-1:2.
2. Decide whether the decimal `InvalidOperation` flag write is allowed under "no external effects / pure". Then R-1:3
   and B-PRESERVE can be recorded with Agent technical-inspection evidence, or the code can be fixed (for example by
   parsing inside `decimal.localcontext()`).
3. Record B-1 after item 1 is done, then rerun `validate-feature --stage check` and `audit-delivery`.
