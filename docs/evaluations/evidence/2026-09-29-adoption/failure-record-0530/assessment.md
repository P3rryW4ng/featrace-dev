# FEAT-001 — failure-record follow-up (verification-record continuation)

Skill: native `featrace-adoption:dev` `check FEAT-001`, loaded from
`<RUN>/plugin/skills/dev` (0.5.30). I read `SKILL.md`
and `core/references/verification-workflow.md`, and followed its technical-observation and failure rules.
This continues ordinary verification-record maintenance. It is not an independent review.
Inputs I used: `technical-followup/assessment.md` and `effects_probe.py`, treated only as leads. I re-confirmed every
fact I relied on against the current code with small repros. I did not read evaluator before, audit or preparation
transcripts (`before.json`, `stream.jsonl`, `*-maintainer.txt`, `audited.json`).

**Final judgment: FEAT-001 remains `provisional`.** Four verification rows are now recorded as actual technical
failures. Delivery is blocked, and no delivery report was written.

## Worktree identity

- HEAD `69a66badf72164c34bf2a9e49e5cf050cb11d288`, unchanged. Nothing is staged, before or after.
- Uncommitted changes: ` M lower.py`, ` M upper.py`. The sha256 values match the prior assessment and were the same
  before and after this session:
  upper.py `7a1cea57…a6e7`, lower.py `e4e9aa7f…120f`, test_contract `d970dac9…`, test_integration `a1a02cb7…`,
  test_lower `5e1123a2…`, test_upper `768d2442…`.
- Interpreter: `python3` 3.9.6.
- PRD `sources/prd-original.txt` sha256 `2d00bc96…`, indexed and readable.
- Limit: `tested_revision` records only the commit. The worktree contents are identified by the hashes above.

## Actions, in order (serialized, one mutation at a time)

1. Read: PRD, `upper.py`, `lower.py`, `verification.json`, `verification.py` (to see how it treats mapping and history).
2. `verify-inputs.py . FEAT-001` → rc 0, `review_required` (`worktree_changed_paths_require_review`: lower.py,
   upper.py). Both files were reviewed through code reading and the repros below.
3. Bounded repro (inline Python, project root, `PYTHONDONTWRITEBYTECODE=1`, read-only):
   - `lower.convert('{"id":"a","timestamp":"2026-01-01T00:00:00Z","payload":NaN}')` → record with payload `nan`, no
     error. `Infinity` behaves the same way (→ `inf`).
   - A timestamp with Arabic-Indic digits, `٢٠٢٦-01-01T00:00:00Z`, is accepted and normalized to `2026-01-01T00:00:00Z`.
   - After `decimal.getcontext().clear_flags()`, `upper.convert('sku,name,price\na,A,bad\n')` returns the correct
     `invalid_price` error, but it leaves `InvalidOperation=True` in the caller's decimal context flags. A valid price
     sets no flags, and `lower.convert` sets none.
4. `grep` of tests: no JSONL NaN/Infinity, non-ASCII-digit or decimal-context assertion exists. The NaN and Infinity
   tests found are CSV-price tests only.
5. **Coverage correction:** `requirement:R-1:2` changed from automatic (`parser-all`) to manual, with gates=[] and
   coverage="". I edited the row's editable mapping fields with one atomic file replacement. Its 2 prior automatic
   pass results are kept in history. Reason: the coverage text claimed "each JSONL source rule", but step 3 shows
   JSONL rule violations that no test asserts. Partial coverage must stay manual.
6. Fresh selected check: `verification.py run . FEAT-001` → `parser-all: passed` (25 tests, fresh quality report).
   rc 2 because manual rows were unfinished. New digest: `4b89d049502b85c13122c3df237f2cd5e3a51351048c1da8097aa507e4a82ed9`.
7. `verification.py record … --status failed` against that digest and full HEAD, one row at a time:
   R-1:2, R-1:3, B-1, B-PRESERVE. Each call returned rc 0.
8. `verification.py status` → rc 2. `validate-feature.py --stage check` → rc 1. `audit-delivery.py` → rc 1.

The only project writes were `verification.json`, and these via helpers: the regenerated `verification.md`, the
quality report written by `run`, and the appended histories. No code, tests, sources, requirements, decisions,
impact, feature status, git index or HEAD changed. No waivers, passes, user observations or product decisions were
recorded.

## Resulting row states (digest 4b89d049…)

| Row | Mode | State | History entries | Basis |
|---|---|---|---|---|
| requirement:R-1:1 (CSV) | automatic | passed | 3 | Fresh `parser-all`. Coverage left as is: the prior CSV findings (NUL → `csv.Error`, huge exponent) are outside or consistent with the literal source, and I did not investigate further. |
| requirement:R-1:2 (JSONL) | manual (withdrawn from automatic) | **failed** | 3 (2 old automatic passes + 1 failed) | Accepts NaN/Infinity (expected `invalid_json`, since these aren't JSON under RFC 8259), and accepts non-ASCII-digit timestamps (expected `invalid_timestamp`). Causes: `json.loads` defaults, and regex `\d` matching Unicode digits. |
| requirement:R-1:3 (order, no external effects, no shared mutable state) | manual | **failed** | 1 | Order holds and the importers share no state. `upper.convert` writes the caller's thread-local decimal `InvalidOperation` flag. |
| impact:B-1 (full approved contract) | manual | **failed** | 1 | Follows from the R-1:2 counterexamples. The CSV part passes. |
| impact:B-PRESERVE (independent pure local interfaces, no external effects) | manual | **failed** | 1 | The interfaces and independence hold. "Pure" is contradicted by the decimal flag write. |
| gate:parser-all | automatic | passed | 3 | Current command result only. |

`retired`: 0. Every earlier attempt is still in history.

## Evidence method and limits

- Method: Agent technical inspection (reading the call paths in `upper.py` and `lower.py`) plus small in-process
  repros on the identified worktree, with the fresh `parser-all` gate as supporting context. This is not user
  confirmation, device observation or automatic-test coverage, and each record's evidence says so.
- Limits: one interpreter and host, and a handful of representative inputs. I ran no edge-case sweep, huge inputs,
  stdlib/C-extension tracing, workers or builds.
- Interpretation disclosed in the R-1:3 record: I treated a write to caller-visible, thread-shared mutable state as an
  external side effect in the ordinary technical sense. If the owner considers decimal flags out of scope, that is a
  clarify/revise question. The observed write itself is a fact.
- The NaN and Unicode-digit failures rest on the standard meanings of "JSON" and "ISO 8601" as the source uses them.

## Concrete blockers to delivery (not repaired here)

1. JSONL: reject NaN/Infinity as `invalid_json` and require ASCII digits in timestamps, add assertions, then re-verify
   R-1:2 and B-1. This needs `fix FEAT-001 …`, or a source clarification if the owner intends otherwise.
2. CSV: stop the decimal context flag leaking (for example by parsing inside `decimal.localcontext()`), or get an
   owner clarification. Then re-verify R-1:3 and B-PRESERVE.
3. `validate-feature --stage check` also still reports that B-1 and B-PRESERVE need regression evidence or a waiver.
4. After any fix: `verification.py run`, re-record the manual rows at the new digest, then `validate-feature --stage
   check` and `audit-delivery`.
