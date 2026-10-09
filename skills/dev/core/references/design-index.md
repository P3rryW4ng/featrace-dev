# Figma page/state index

Use after registering design evidence with `register-source.py --kind design`. This is a *scoped navigation index*, not a transcription of the entire Figma file or a second product specification. `requirements.json` remains the requirement baseline; `spec/prd-intake.json` records what was actually read. Inventory relevant logical screens and their distinct states against the PRD and supplied Figma material. Record the reviewed scope and gaps; the validator can check the declared list, but cannot discover omitted remote frames or prove visual understanding.

Save `.agent-workflow/features/<ID>/design-index.json` with schema version 1. Each current design source registered in intake is `current`; retain old revisions as `superseded` with a reason, or mark an irrelevant source `excluded` with a reason. Every listed state has one stable logical screen ID, a state ID, a precise Figma URL containing file key and node ID, its registered source path and SHA-256, reading status and (once read) intake unit IDs. A screen may have many states. Read units cited by a state must have matching `figma_file_key` and normalized `figma_node_id` (`1:2`, not a free-text substring). `source_sha256` binds the *whole registered evidence file*, not the bytes of that individual Figma node.

```json
{
  "schema_version": 1,
  "feature_id": "FEAT-001",
  "scope": {"status": "reviewed", "evidence": "Compared relevant frames and states with R-1; inaccessible branches recorded below"},
  "sources": [{"path": "sources/design-part-02.json", "status": "current"}],
  "screens": [{
    "id": "SCREEN-1", "name": "Payment confirmation", "requirement_ids": ["R-1"],
    "states": [{
      "id": "STATE-1", "name": "Initial", "url": "https://www.figma.com/design/ABC123/Payment?node-id=1-2",
      "source": "sources/design-part-02.json", "source_sha256": "<sha256 of registered file>",
      "status": "read", "unit_ids": ["U-2"]
    }]
  }]
}
```

Use `indexed` for a known but unread state, `unavailable` plus `reason` and `impact` for an inaccessible one, and `excluded` plus `reason` for a verified out-of-scope state. Draft permits pending coverage; develop requires the index and reviewed scope; check requires every in-scope state read and linked to its exact intake unit, or explicitly excluded. Do not exclude an in-scope state just to pass check. New source bytes or a newly registered source require renewed reading, index reconciliation and PRD review before continuing.

When a designer supplies a changed screen, use `python3 core/scripts/design_index.py match <PROJECT> <ID> --url '<FIGMA-NODE-URL>' [--screen-name NAME] [--state-name NAME] [--source LOCAL-FILE]`. Exact file key + node ID identifies the indexed state; a description only narrows candidates. A screenshot without a node URL or a copied/recreated node with a new ID is **candidate-only**: compare visible content, neighboring states, requirement and task links, then ask the user to resolve remaining ambiguity before replacing a mapping. Never select the first candidate silently. If an exact node is found, `content_review_required` still means inspect the new design and reconcile its requirement effects. `evidence_bytes: different` only reports a whole-file byte difference; it does not prove a visual change. No automatic remote Figma polling or visual similarity matching is implemented.

Keep the original evidence immutable. Register the new export/manifest separately, retain the previous source disposition, and update only affected states and intake units after checking them. If the change alters confirmed behavior, use the revision/decision flow; otherwise record the design-only change and select proportionate verification. Run draft/develop/check validation at the appropriate boundary. Existing features without `design_index_required` remain readable; registering a new design source enables this index for that feature.
