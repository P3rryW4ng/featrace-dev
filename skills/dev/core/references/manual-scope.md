# Batch applicability of existing manual observations

Use inside authorized Verify when this feature explicitly opted into `manual_scope_contract: 1`. This is an extension of existing carry, not another Skill, stage, device driver or permission to run checks. Installation does not prepare projects. Legacy manual records retain their current rules until explicit feature preparation.

## Meaning and stopping conditions

Preserve the original observation, tested revision, available actual observed time, package provenance and history. The original result `at` is registration time; expose it as `original_registered_at`. Keep `observed_at` null when no original explicit observation timestamp exists; use archived run evidence to investigate execution windows, never relabel registration as execution. Review whether that fact supports the complete current claim. New code/authority changes first require applicability investigation; stale does not by itself mean physical re-observation. Full parents, shared conditions, complete project changes, source/contract provenance and transitive dependencies remain visible. A path, comment, test-only edit or unchanged package is not automatic proof of independence.

Select only active manual requirement/impact rows whose latest recorded result is passed or a validated continuous retention of a passed fact. Never skip a later failed/unavailable/withdrawn/waived result. Interpretation adoption of unavailable originals and retired/new row matching remain on `evidence-adoption.md`; unsupported chains must remain unknown, not be converted. This batch path does not assemble separate observations into an unexecuted whole. True changes, missing original material, missing identity or unknown device-specific mechanisms require targeted evidence.

A batch fresh-context reviewer may inspect many claims with shared material. Each claim needs its own complete-claim/dependency/environment/counterexample judgment; no mandatory new Agent or human approval per row. The normal v6 final review of all current claims is still required. Independence fields attest to actual review; they are not cryptographic proof. Do not change reviewers to erase a negative on identical facts. New evidence/authority is needed before replacing an affected/unknown/partial finding with support.

## Explicit preparation and frozen batch

After authorization to enable this feature's format, run:

```text
python3 core/scripts/evidence_carry.py prepare-batch <PROJECT> <ID>
```

This prepares verification schema 5 without changing observations or executing commands. It does not enable automatic execution contract 2; legacy checks and mode-2 attempts remain separate. Older readers must reject schema 5. Keep old histories, annotations, adoption/correction events and check-attempt references. After opting in, merely downgrading the tool is not a safe data rollback; preserve data and stop unsupported operations rather than deleting fields.

Save a request array in authorized ignored scratch. Each request has `item_id` and, when needed, an explicit full `contract_revision` storing the exact original result. The default is the original tested commit, or a previously validated locator in this batch chain. Tested→record→current ancestry and the entire tested→record interval must preserve the business tree; do not pick a convenient later green. Then:

```text
python3 core/scripts/evidence_carry.py capture-batch <PROJECT> <ID> --requests <request.json>
```

Save stdout as the frozen snapshot in authorized scratch. It includes the complete current code/actual-input identity, canonical authority and source/evidence identities, original locators, immutable historical contract revisions and grouped change IDs. Original private actual/evidence prose is not duplicated into the event. Read the canonical/Git originals from these references when needed; hashes do not replace reading the claim or prove environmental equivalence.

Shared inputs are read once per operation rather than once per claim. Clean committed business inputs and actual-byte checks are required for capture; a read-only status on dirty/unknown inputs reports stale. Workspace execution locks/unfinished-process guards prevent certification during another runner's activity. This implementation requires POSIX workspace locking and does not coordinate other machines/worktrees or shared devices. Record-only commits do not change business identity; unregistered ignored/external inputs remain a completeness risk and necessary inputs must be declared.

## Reviewer response and adoption

Return `input_digest`, real `reviewer`, `independent_context: true`, `assessments`, `findings` and explicit `apply_ids`.

- `assessments` is keyed by every exact grouped change ID in the snapshot. Each supplies concrete shared difference `evidence`. It is not a blanket independence verdict across claims. A code key includes the original code revision; a record key includes the historical contract revision, so different origins cannot borrow an unrelated diff.
- Each target has one finding with `item_id`, `verdict` (`supported`, `affected`, `unknown`, `partial`), `assessment_refs` as a dictionary from every exact target change ID to its claim-specific `unaffected`/`affected`/`unknown` effect, investigated `dependencies`, and nonempty `claim_evidence`, `dependency_evidence`, `contract_evidence`, `environment_evidence`, `counterexample`.
- A supported finding also supplies `original_identity`: exact original `revision`, `worktree_verified: true`, explanation and archived `evidence_refs` available in snapshot sources/evidence. Static observations do not need an APK; UI/device observations need their actual package/environment proof. Inspect it, do not blindly set the field.
- When a snapshot target includes `contract_record`, a supported finding also supplies `contract_record` with that exact `revision`, original `tested_revision`, and concrete `explanation` of the original-result/contract provenance and unchanged tested-to-record business interval. This does not relabel the saved commit as the tested revision.
- `apply_ids` is a nonempty, explicit supported subset. All findings must be structurally complete. Unknown/affected/partial findings stay gaps; do not mark an entire batch passed. A supported finding must classify all its changes as unaffected with claim-specific rationale. The same shared change can affect one claim while being demonstrably unrelated to another.

```text
python3 core/scripts/evidence_carry.py apply-batch <PROJECT> <ID> --snapshot <snapshot.json> --review <review.json>
```

Application validates every target/review, rechecks moving inputs and the current plan under its nonblocking lock, then writes one shared event and row references atomically and renders once. Original history is untouched; scope support is displayed as retained applicability, never a new test. Negative/unadopted targets keep explicit stale references so readers cannot fall back to an earlier green. Identical application and recapture of the same current supported basis are idempotent. Partial writes, concurrent changes or save failures cannot overwrite another plan; preserve the failed attempt and investigate rather than rerunning devices automatically.

## Currentness and other workflows

Status, audit, stage/Verify inputs, report drafts and final claim review use one applicability resolver. A later real result clears the old pointer; a new failure cannot be covered by an old scope event. Changing a different row's mapping or result does not re-sign this row, while all new project/authority/source changes still require a fresh scope assessment. Known feature lifecycle and task-progress fields retain ordinary eligibility checks; free-text status notes, decisions, unknown fields and real requirements are not automatically ignored.

Descriptions/archived index corrections still use existing correction/annotation tools. Correction events relevant to this row invalidate its prior scope support for reassessment. Some existing single-row retention/annotation operations cannot replace a batch scope reference and explicitly refuse; use the batch path to reassess, never convert states to force compatibility. The whole evidence inventory remains conservatively monitored; an unrelated new archive may still require one batch assessment. This is not fully automatic local dependency tracking or incremental final review.

Actual new observations and FIX/TEST device receipts keep their own recording contracts. New automatic tests/code/config still invalidate automatic execution facts under `check-execution.md`; this scope review does not waive those checks. Required global decisions, unresolved behavior, missing tests or final review still prevent complete even when selected manual facts are retained. If review is more costly than a permitted targeted rerun, report that tradeoff and choose within existing authorization; no savings percentage is promised.
