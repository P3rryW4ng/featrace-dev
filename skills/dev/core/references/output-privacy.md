# Exact-output privacy review

Read before sharing newly authored output, receipts, screenshots or staged additions. Inspect only the selected authorized files; do not recurse through history, credentials or unrelated project/device data. Read installed version from the actual marker, not an old document heading.

```
python3 core/scripts/output_privacy.py ROOT --file exact-relative-path [--file another] [--known-values ignored-private-file]
python3 core/scripts/output_privacy.py GIT_ROOT --staged --file exact-staged-path [--known-values ignored-private-file]
```

The checker is unchanged: complete UTF-8 streaming, exact selected file mode or index inserted/replaced lines, final identity recheck, no mutation. It reports target number/line/column/kind, not raw values/paths/context. Known-value shape is `{"values":[{"kind":"account_identifier","value":"actual already-known value"}]}`; allowed kinds also include credential/device_identifier/contact. Keep this optional64KiB input private and ignored; never put values in command arguments or a permanent registry. Do not fetch accounts solely to populate markers.

Exit0/no_matches means no pattern matched in this inspected text, not a privacy certificate or permission to publish. Exit1/review_needed requires inspecting exact positions privately; code-like candidates may be false positives. Exit2/unavailable means incomplete/invalid/changed/binary/unsafe/over-budget input and cannot count as clean. Position output is bounded100/target but the remaining bytes are still validated. Images/audio require their own actual review.

Limits:256MiB per file/blob/diff stream,16MiB logical source line. Complete LF-delimited groups preserve cross-group known values, JSON escapes, Unicode columns and missing final LF. Git diff disables external diff/text conversion, checks only added/replaced index lines and rechecks index/HEAD/content identity; removed/equal history and unstaged edits are not newly disclosed additions. Empty new files/mode-only changes have no new text. Stream/read/process/encoding/identity failure refuses; subprocesses are reaped. Git's own memory/runtime is not guaranteed constant.

Stage only authorized paths, then batch-check them once before commit; this adds no test rerun, hook or whole-project scan. Ignored local task logs are not automatically committed. Correct only authorized newly generated disclosure, preserve meaning and exact provenance, and recheck affected content. Do not manually repair frozen hashes, rewrite history, mass-redact old ledgers or pretend a pending-output correction removes committed disclosure. Separate approval is needed for any historical privacy correction. Report only locations/counts/action/limits without leaking the value.
