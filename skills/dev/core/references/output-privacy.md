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

Before local delivery-record commit, batch-check only exact selected staged paths with --staged after staging, following delivery-commit.md. It scans inserted/replaced index lines, excludes removed/equal history and does not confuse unstaged edits with staged content. It neither stages nor commits. No new Git hooks/CI, full-project scan or quality-gate rerun is needed for this check. Large/binary outputs remain unavailable; do not silently skip them or extend this into source-history cleanup.

When a newly authored return contains a private value, correct only that authorized generated text/copy and preserve factual meaning and original private provenance. Recheck the corrected candidate and the normal input freshness before applying; a previously frozen review cannot be silently relabelled. Do not auto-edit existing raw evidence, immutable proposals or historical results, reset tested_revision, rewrite Git history or erase prior facts. Already committed disclosure is a separately scoped investigation, not a reason to mass-edit evidence here. Screenshots still need visual inspection before sharing. Keep the final user summary short: locations/counts, action and remaining uncertainty, without the values or a blanket “safe” claim.
