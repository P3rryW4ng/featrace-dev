# Review outputs, receipts and reports: bounded privacy checks

Load when new review output, a receipt or delivery report can repeat private identifiers/credentials from already authorized evidence, or before sharing those new records. This targets GAP-35: a reviewer can leak an account value even when the original archive was redacted. It is not another acceptance stage, a privacy certificate, or authorization to inspect unrelated accounts/configuration.

If reporting the installed package version, read the installed .feature-delivery-install.json version field (or report it unknown if unavailable). Reference-document version headings are historical rule provenance, not the installed package version.

Check newly authored artifacts before displaying/importing them into canonical history. Do not dump their bodies or the private known-value file to terminal/chat just to inspect them. Use only selected files within the authorized project or external review output root. Never recurse through all sources/history, fetch credential stores, query a device or connector solely to populate markers, or invent which values are sensitive. When already-known identifiers/tokens matter, keep only necessary exact strings in an authorized private ignored scratch file, not CLI arguments, a second permanent registry or committed configuration. An external non-Git review root must likewise be explicitly authorized/private; ignore status cannot be checked there.

The read-only helper returns target number (the order of --file), line, character column and candidate kind; it omits file paths, raw values, matched context and value hashes. Known values support literal and JSON-escaped text; labeled identifiers, bearer strings and a limited set of credential/key patterns give candidates, not proof of sensitivity. Unknown unlabeled or differently encoded values and image/audio contents need actual bounded human/Agent review. It does not identify all PII/secrets.

```text
python3 core/scripts/output_privacy.py <AUTHORIZED-ROOT> --file <review.json> --file <report.md> [--known-values <ignored-relative-file>]
python3 core/scripts/output_privacy.py <PROJECT-GIT-ROOT> --staged --file <exact-record-path> [--known-values <ignored-relative-file>]
```

Private input shape: `{"values":[{"kind":"account_identifier","value":"<actual already-known value>"}]}`. Kinds: account_identifier, credential, device_identifier, contact. The helper checks ignore status in Git projects; it reads this input without echoing it. Do not put actual values in command arguments or user-facing messages.

- Exit 0 / no_matches: no matching value/pattern in the inspected text scope, not approval to publish or to mark complete.
- Exit 1 / review_needed: inspect the cited positions privately. Hold the affected import/sharing/commit until the candidate is resolved; unrelated coding/testing can continue. Never repeat the matching value, even shortened, in the explanation.
- Exit 2 / unavailable: invalid/unreadable/unsafe/binary/changed/oversized input or partial failure; never treat it as clean. Reports are bounded to 100 positions per target, with truncation explicit. The checker writes/redacts nothing, returns no exception message containing an input value, and rechecks the examined bytes before returning; host confinement still depends on actual permissions.

Before local delivery-record commit, batch-check only exact selected staged paths with --staged after staging, following delivery-commit.md. It scans inserted/replaced index lines, excludes removed/equal history and does not confuse unstaged edits with staged content. It neither stages nor commits. No new Git hooks/CI, full-project scan or quality-gate rerun is needed for this check. Large UTF-8 text is streamed rather than rejected solely for exceeding 16 MiB. Limits remain explicit: each file/blob/diff stream is at most 256 MiB and each logical source line at most 16 MiB; invalid encoding, binary input, resource-limit excess and incomplete reads remain unavailable. Do not skip them or extend this into source-history cleanup.

When a newly authored return contains a private value, correct only that authorized generated text/copy and preserve factual meaning and original private provenance. Recheck the corrected candidate and the normal input freshness before applying; a previously frozen review cannot be silently relabelled. Do not auto-edit existing raw evidence, immutable proposals or historical results, reset tested_revision, rewrite Git history or erase prior facts. Already committed disclosure is a separately scoped investigation, not a reason to mass-edit evidence here. Screenshots still need visual inspection before sharing. Keep the final user summary short: locations/counts, action and remaining uncertainty, without the values or a blanket “safe” claim.


## Confirmed repeated identifiers in pending records

Separate genuine new disclosure, a helper copy, moved historical prose, and false positives. A code comparison such as `email == currentEmail` can be a labeled-value candidate; resolve it by inspecting the exact position, not by disabling the check. A clean scanner result is never mandatory proof when an inspected candidate has a documented nonprivate explanation.

For redundant uncommitted carry copies use evidence-carry.md's minimize-copies helper, not manual receipt-hash edits. It cannot remove private identifiers already in original observations or newly authored reviewer prose.

If the user specifically authorizes privacy correction of identified historical descriptive fields, preserve a private ignored original and its hash first. Limit replacements to the confirmed identifier at those exact field paths, using a stable neutral device label whose private mapping is not committed. Preserve the observation's time, mode, result, tested identity, limits and authority. Record the affected paths, counts, original/corrected file hashes and reason in a shareable correction note without copying the value. Never infer authorization to sweep other features or rewrite Git history. A result/receipt/source digest binding is not an unbound description: use its supported correction path or stop that field; do not manually repair hashes. Revalidate affected links, regenerate views and refresh current final review/report/delivery bindings before committing. No business test rerun follows solely from this descriptive correction. Historical raw evidence and immutable requirement proposals remain outside this exception.

This permission-scoped correction is an exception to preserving historical prose byte-for-byte, not to preserving historical facts. Already committed originals remain in Git history; pending-output redaction does not remove that prior disclosure. Keep that limitation explicit.


## Large text and staged records

The scanner consumes bounded groups of complete LF-delimited lines, carrying enough suffix for known values (including their JSON-escaped forms) across groups. Existing candidate patterns keep their meaning. UTF-8 characters and Unicode separators are not patch delimiters. A missing final LF is not manufactured as matching content. A new empty file or mode-only change has no inserted text and is not an unavailable diff. Position output stays limited to 100 per target, but the rest of the input is still read and validated; truncating findings never certifies an unread tail.

Staged inspection reads immutable index/HEAD blobs and a streamed Git diff with external diff and text conversion disabled. It checks only added/replaced lines, not removed or equal historical content and not unstaged edits. Final re-reading compares content digests plus index/HEAD identity; summaries replace retained raw copies, not the full-input comparison. Read, Git-process, encoding or identity failure yields unavailable. Scanner-managed Git processes are reaped after early refusal. This does not promise constant memory or runtime for Git's own diff implementation.

No business artifact is compressed, rewritten, split or redacted to make it fit. Known-value files retain their 64 KiB limit and ignored-input requirement. The same CLI, exit statuses, position-only reporting and privacy-review authority apply; no new project preparation or acceptance migration is required. If a selected file still exceeds a resource limit, report it explicitly rather than claiming a partial clean scan.
