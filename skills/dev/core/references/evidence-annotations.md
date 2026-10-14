# Bounded evidence-index, annotation and archive addition review (0.12.2)

Use for correcting an explicit evidence index/annotation, or adding backed-up original artifacts, while the selected reviewed carry results are current. Already-stale carried rows are listed as excluded and never revived by this path; they remain separate Verify work. Do not automatically exclude Markdown, README files or any directory from freshness. A file role is an explicit scope declaration reviewed against the actual patch, not an extension-based permission.

An index can narrow an overstated description to match already-recorded evidence limits, correct navigation or clarify test-package versus app-package build wording. It cannot add a missing observation, silently change a claim, convert a truncated hash into full equality or rewrite raw commands/outputs. If the correction exposes insufficient original coverage or identity, stop and return the affected row for ordinary Verify. Whole carried claims must remain supported.

## Freeze before editing

Declare the exact text files, including a new separate annotation if needed:

```json
[{"path": "evidence/README.md", "role": "index"},
 {"path": "evidence/provenance-notes.md", "role": "annotation"}]
```

```text
python3 core/scripts/evidence_annotations.py capture <PROJECT> <ID> --metadata <metadata.json>
```

Save stdout in authorized ignored scratch. This freezes the current plan, complete carried parent claims, original result identities, code and all source/evidence hashes, plus before text. If already stale, use the ordinary carry investigation; do not restore a convenient old snapshot to manufacture eligibility.

Edit only the declared index/annotation. Keep original transcript bytes. For a truncated command/output excerpt or ambiguous test-package build heading, add a clearly linked separate note describing the known limit and exact artifact/line; do not repair the original OUT block or invent omitted output. Command/output transcript markers are rejected as index text, but marker detection does not prove a file is metadata: the reviewer must inspect its actual role.

```text
python3 core/scripts/evidence_annotations.py review-inputs <PROJECT> <ID> --snapshot <snapshot.json>
```

The helper rejects edits/deletions of undeclared or existing raw artifacts, code, source, decision, requirement, impact, traceability or result changes. Explicit new archives can use the addition path below in the same capture/review. It returns the exact before/after text and every current carried row. Dispatch one fresh read-only context with these inputs, original artifacts as needed and this reference; give no suggested verdict. Review the bounded patch and shared classification once, then account for each row. Do not repeat the previous whole-project investigation or create one Agent per row solely to correct an index.

The review JSON requires matching `input_digest`, `status: supported`, `independent_context: true`, actual `reviewer`, and nonempty `classification_evidence`, `raw_evidence_unchanged`, `claim_meaning_unchanged`, `counterexample`; `items` must cover the input's exact row IDs once each, with `item_id`, `status: supported` and a concrete `evidence` explanation. A changed/unknown claim rejects this metadata-only path. The fresh-context flag records dispatch intent, not a sandbox or proof of semantic correctness.

```text
python3 core/scripts/evidence_annotations.py apply <PROJECT> <ID> --snapshot <snapshot.json> --review <review.json>
```

Application rechecks inputs, saves one shared bound patch review in existing `verification.json` and appends small `annotation_amend` retained receipts to the covered rows. Original history and tested revisions remain; current reviewed revision is separate. Entry wording is constrained to metadata review, never a new execution. It runs no gates, no device actions and no completion mutation. Normal quality/claim/completion conditions still apply. Any later evidence edit becomes stale again until legitimately handled; this is a reviewed correction, not permanent hash exclusion. Old installations must be updated before reading new receipt forms.

## Add existing originals without a full repeated carry (0.12.2)

This repairs the archive/carry integration gap: device execution requires durable provenance, yet adding that provenance used to stale every unrelated carry. Do not switch to reference-only freshness, blanket-ignore new files or retroactively declare raw output an index. Existing evidence remains hashed; an explicit supported review advances only current unaffected rows to the new archive inventory.

First preserve actual original logs/transcript/APK files in authorized Git-ignored project-local `.agent-workflow/scratch/`. Keep unredacted originals private there. Never recreate missing output, infer a full hash from a prefix or rename a recording revision as the tested source. Declare only needed new archive destinations, not the entire scratch directory or large APK binaries merely because they exist:

```json
[{"path": "evidence/provenance/fix003-original-run.txt",
  "origin_path": ".agent-workflow/scratch/OGFR-7700/raw-backup-fix003-347237f6/fix003/test9-run.txt",
  "transformation": "verbatim",
  "purpose": "Persist the already executed device run; not a new test"},
 {"path": "evidence/provenance/fix003-build-install-excerpt.jsonl",
  "origin_path": ".agent-workflow/scratch/OGFR-7700/raw-backup-fix003-347237f6/transcript-0747-0801Z.jsonl",
  "transformation": "redacted_extract",
  "purpose": "Persist exact relevant build/install/commit lines with identifiers redacted"}]
```

`verbatim` requires identical bytes; `redacted_extract` requires the reviewer to compare the original and final file, cite selected ranges, redaction substitutions, omitted parts and preserved evidence boundaries. Neither a digest nor supported prose alone proves that redaction/extraction is faithful. Generated indexes/manifests are annotation metadata, not original logs. Preserve original output time and observation identity. Raw scratch contents are not embedded in snapshots; the reviewer reads only needed originals within authorized resources.

Before any evidence edit/addition:

```text
python3 core/scripts/evidence_annotations.py capture <PROJECT> <ID> --metadata <metadata.json> --additions <additions.json>
```

Either option can be omitted if that scope is empty. Save the snapshot in ignored scratch. Copy or extract/redact only the declared new files; existing raw file bytes must stay unchanged. Apply declared metadata corrections in that same bounded patch. Then obtain `review-inputs` as above and dispatch one fresh read-only reviewer with the snapshot/current review inputs, declared original paths, final artifact paths and complete carried claims. Inspect the additions and patch, reuse unchanged prior applicability findings; do not repeat every previous project exploration. Archive authenticity and claim relevance are separate judgments.

For a capture with additions, review output includes `archive_assessment` with exactly one entry per new path:

```json
{"path": "evidence/provenance/fix003-original-run.txt", "status": "supported",
 "provenance": "Exact backed-up origin and time/identity inspected; describe known limits",
 "transformation_evidence": "Compared actual original/final ranges and bytes or named redactions",
 "relevance_evidence": "Which claims this additional evidence concerns, including any contradiction"}
```

The overall review may be `status: reviewed`; each existing row's verdict can be `supported`, `affected`, `partial` or `unknown`, with concrete evidence. Full coverage of the frozen eligible row list is required. The helper appends retained receipts only for supported rows. Other rows keep their prior history and remain stale under the changed evidence inventory; the return prints retained/unresolved counts. `claim_meaning_unchanged` explains supported claims and any unresolved exception, never claims all passed if some did not. Bad/unavailable archive provenance or unsupported transformation rejects the whole application. Partial row acceptance is not completion approval: run the normal validation/audit and route only the remaining gaps to Verify.

Application rechecks backup hashes, all declared final files, original evidence inventory, code, authority and plan before save. New archive paths must not already exist at capture; undeclared additions, original mutation, symlinks, unsafe/nonignored origins and stale returns are refused. The receipt preserves original tested revision and uses archive/index review wording, not rerun wording. New device execution receipts can be registered afterward from these durable artifacts. Metadata-only old receipts and inputs remain readable; update the installation before writing new archive receipts.

A provenance limit is not automatically a failed behavior test. For example, a complete package comparison at 15:52 and a prefix comparison at 15:59 must be reported separately; absence of a recorded reinstall is continuity evidence with stated limits, not another full hash execution. Do not demand proof excluding every hypothetical IDE action; evaluate accessible build/worktree/install evidence and investigate a concrete contradiction or unexplained identity. If still insufficient, obtain targeted evidence, not a fictional pass or unrelated whole-matrix rerun.
