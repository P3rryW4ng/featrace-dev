# PRD analysis contract (intake v1; multi-source extension)

Read for `dev prd`, PRD revisions, and when API/Figma reconciliation changes requirement meaning. This standardizes the analysis process, not the author's document format. Never demand that the product author rewrite a PRD to our template.

For a new feature, after `feature-selection.md` confirms the user-supplied ID and that the target does not already exist, initialize with `bash core/scripts/init-feature.sh <ID> <PRIMARY-DOCUMENT-OR-HTML> <PROJECT> [--source <ADDITIONAL-FILE> ...]`. A single document or HTML file is sufficient. The initializer preserves source bytes and extension; a failed or interrupted import must be resumed without overwriting it. Read project `.agent-workflow/config.yaml` when present; otherwise copy `core/assets/config.yaml` as Agent guidance, not an executable policy engine. Use readers for Word/PDF before decomposing them and record any unreadable portions.

Registered evidence kinds are `document`, `html`, `design`, and `api`. Initial `/dev prd` files are inferred as document/HTML. For supplementary API or Figma material, first preserve the accessible export or an Agent-authored evidence manifest as a regular local file, then run `python3 core/scripts/register-source.py <PROJECT> <ID> <FILE> --kind api|design`. This single helper copies immutable evidence and synchronizes intake sources with `feature.prd_paths`; do not edit those indexes separately. If a link cannot be exported, the manifest must record its exact URL, relevant operation/node, version and access gaps without inventing content. Registration does not count as reading or semantic reconciliation.

## 1. Reading inventory

A feature may start with only a document, only HTML, or both, then receive API/design evidence. Initialize with one primary file and repeat `--source` for additional document/HTML files. `sources` registers every supplied part; no source kind is universally mandatory. Preserve all originals in sources/. A linked URL is only a reference until its content is accessible. If HTML depends on CSS, scripts, images or a server, verify those dependencies or record the resulting reading gap; a bare HTML file may not reproduce the interaction.

Preserve the original in sources/. Inventory meaningful sections, tables, figures, notes and referenced attachments as units. Group at a useful granularity; don't create an item for every sentence or formatting character. Record each unit's source path, exact locator, kind and reading status. For external links, retain a reference artifact in sources/ and mark pending/unreadable until actual content has been read; a saved URL is not its contents.

For HTML, inspect the rendered interaction when an authorized browser/runtime is available. Inventory page/state and each relevant action as units. Each HTML source needs interaction units, or an `interaction_scope` explanation when the supplied HTML is genuinely static. A read `kind: interaction` unit records `trigger`, `before`, `after`, `observation` and a locator to the control/state. `observation` states how and where it was reproduced; the script checks presence, not truth. Unavailable dynamic behavior remains pending/unreadable with reason and impact. Static markup, placeholders and example data alone do not prove runtime or business rules. When the same behavior appears in multiple sources, link source items and reconcile scope. A contradiction becomes a pending decision with both references; do not silently choose one.

Use available readers for Word/PDF and inspect relevant images and merged tables. If these are unavailable, record the reason and affected behavior; never treat an absent parser/OCR result as an empty specification. Extraction/OCR text is derived evidence and must link to original page/cell/image locations. Do not silently discard unreadable portions. `inventory_complete` means the Agent checked inventory coverage against the original, not that a parser succeeded.

## 2. Context-preserving items

Record original excerpts with unit IDs and surrounding context (section, role, scope, time period). Classify each as rule, example, suggestion, background or undecided. Preserve stable IDs on reanalysis; retain prior snapshots before edits. Do not promote an example or suggestion into a confirmed rule.

Do not merge similar statements unless actor, scope, trigger, conditions and outcomes agree. Connect exceptions, overrides and dependencies using related_ids and relationship aspects. Quote enough context to preserve pronouns, table headers, negations and units. Product rules may live in table notes or screenshots.

## 3. Working specification and coverage

requirements.json remains the product specification. prd-intake.json is an evidence index, not a second editable PRD. Each active requirement uses source_item_ids; inferred requirements link to motivating excerpts and state assumptions. Source items may map many-to-many to requirements.

For every mapped item, enumerate applicable aspects: behavior, condition, exception, limit, negation and relationship. Each aspect links to a specific requirement statement or acceptance_criteria index and copies its exact current target_text for stale mapping checks. Inspect role, boundary values, units, temporal scope, exclusions and precedence. Do not assume every kind applies, or fill absent values with inventions.

`disposition` is mapped, excluded or pending. Only background/examples/suggestions may be excluded, with a reason explaining why they impose no implementation obligation. Rules cannot be dismissed as background simply to pass a check. Material ambiguity stays pending; record impact/options in decisions. Routine reversible choices may become explicit inferred requirements under existing workflow rules.

Separate three things: unreadable material (reading gap), readable but unspecified behavior (unknown/assumption), and out-of-scope material (not_applicable with rationale). None substitutes for another. Do not demand Figma or an API solely to fill a checklist.

## 4. Semantic review

Revisit the original, rather than rereading only your generated spec. Check original → items → requirements for omissions, and requirements → evidence for invented behavior. Check condition/exception/precedence relationships, not merely IDs. Keep PRD-intended acceptance distinct from inferred checks; use an inferred requirement for additional behavior instead of appending ungrounded criteria to a confirmed rule.

Mark aspects verified only after checking their meaning. Log discrepancies and fix records first. A user's approved change may supersede original behavior, but must have a decision reference and explanation in review notes; don't pretend the old excerpt agrees.

After the actual review, record attribution:

```text
python3 core/scripts/review-prd.py <PROJECT> <FEATURE-ID> --reviewer agent --notes "Checked roles, limits, exceptions and reverse coverage against original; findings and resolution references: ..."
# If unresolved source items or unreadable units remain, record a partial review instead:
python3 core/scripts/review-prd.py <PROJECT> <FEATURE-ID> --stage draft --reviewer agent --notes "Reviewed accessible content; unresolved: S-3 pending; U-2 unreadable; next evidence needed: ..."
```

This command validates record structure and records a digest. It does not read or approve meaning on your behalf. Never run it merely to suppress a stale-review error. Source bytes, intake mappings or requirement semantics changing requires a new review. Task assignment/progress alone does not.

Run validate-feature.py --stage develop afterwards. Draft allows pending extraction with warnings; develop/check require complete inventory, resolved gaps, bidirectional coverage and a current attributed review. Current gates are feature-wide: do not claim unaffected-task automatic eligibility. Creating inventory from guessed material to satisfy a gate is prohibited.

## Record format

New init registers supplied sources in spec/prd-intake.json and leaves units/items empty. Legacy intake without a sources array remains readable. Example (replace all content with actual evidence):

```json
{
  "version": 1,
  "feature_id": "FEAT-001",
  "inventory_complete": true,
  "sources": [{"id":"SRC-01","path":"sources/prd-original.md","kind":"document"}],
  "units": [{"id":"U-1","source":"sources/prd-original.md","locator":"§2 paragraph 1","kind":"text","status":"read"}],
  "items": [{
    "id":"S-1","unit_id":"U-1",
    "quote":"仅首次登录展示引导。",
    "context":"登录流程；首次指账号首次登录，而非每次启动。",
    "kind":"rule","related_ids":[],"disposition":"mapped",
    "aspects":[{"kind":"condition","text":"仅账号首次登录",
      "requirement_id":"R-1","field":"statement",
      "target_text":"账号首次登录时展示引导，后续登录不展示。","review":"verified"}]
  }],
  "review":{"reviewer":"","notes":"","digest":""}
}
```

Context must be sourced: the clarification in this example is valid only if supported elsewhere; otherwise leave “首次”的具体口径 unknown. Add source_item_ids: ["S-1"] to R-1. For a reading gap add reason and impact to its unit; for excluded items add reason. All items require quote, context, related_ids and aspects (possibly empty for pending/excluded content).

render-workspace.py also generates spec/prd-analysis.md, including unresolved gaps and source mappings. Do not edit this generated view.

## Compatibility and limits

Existing 0.3 workspaces can still be rendered/viewed; draft warns if intake is absent, but develop/check stop until evidence is reconstructed and reviewed. Create the empty template using the Python `new_intake` helper or copy core/assets/prd-intake.json and set feature_id; never rerun init-feature on an existing feature. No business source or existing decision is overwritten automatically.

The validator requires a reading unit for every registered part, an interaction inventory or static-scope explanation for HTML, and checks observed interaction fields, but cannot discover omitted controls, validate browser observation, or detect semantic conflicts on its own. The validator cannot prove inventory completeness, excerpt fidelity, OCR correctness, kind classification or semantic equivalence. Digests detect local review invalidation, not full source version history. General source version/impact automation remains a later milestone. Full requirement/decision state-schema enforcement remains unfinished.

A `--stage draft` entry records what was actually read and preserves pending items/gaps with warnings. It does not turn a pending item into mapped, repair missing source material, or permit develop/check. Once gaps are resolved, reread the affected source and register a full review without `--stage draft`; a draft review digest is never treated as full review even when content happens to be complete. Older review records without a stage keep their previous compatibility.


## Confirmed revisions (0.5.0)

For a version-controlled feature read [revision-workflow.md](revision-workflow.md) before changing meaning. Original text stays unchanged. Applied, hash-matching revisions/CHG-*.json may be registered as document evidence in addition to sources/. A replaced aspect keeps its old text/target_text and declares superseded_by plus supersession_reason; the validator matches its prior target against the applied change. Register current non-superseded evidence for each active requirement and perform a new full review. Pending revisions cannot serve as confirmed evidence; the revision's timestamp alone gives no authority.
