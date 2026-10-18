# Verification checklist

Generated view; manual observation and automated checks are distinct.

## requirement:R-1:1:5418d1630003

Mode: manual
Expected: abc becomes ABC
Status: retained

Manual applicability (original observation unchanged; no new execution):
```json
{
  "state": "current",
  "event_id": "e49825f1912d3c46789cfd2d5de341f045760d6aa3f3866f6eb33eb6738a8cce",
  "verdict": "supported",
  "original": {
    "item_id": "requirement:R-1:1:5418d1630003",
    "history_index": 0,
    "result_hash": "856b4f367bd74f4611e15b3b145c3fe0ae35d7716dfa1d5abbc72691d62be4b4",
    "tested_revision": "5bd8195027408348901e7941af1280af12b18028"
  },
  "review_ref": ".agent-workflow/features/FEAT-001/verification.json#manual_scope_reviews/e49825f1912d3c46789cfd2d5de341f045760d6aa3f3866f6eb33eb6738a8cce",
  "observed_at": null,
  "original_registered_at": "2026-10-18T06:23:28.391493+00:00",
  "reviewed_at": "2026-10-18T06:27:56.576881+00:00",
  "reviewed_revision": "0e2116c95656b99641fb8ba3cf2246f4d4cb5983",
  "reason": "reviewed applicability; no new execution"
}
```

Latest recorded evidence (not necessarily current):
```json
{
  "status": "passed",
  "digest": "1c6b3eaedcb8392289d2674098d46c1b15e998c81e9cbe19b7213049342a4239",
  "tested_revision": "5bd8195027408348901e7941af1280af12b18028",
  "actual": "Original actual output: {\"conversion\": \"ABC\", \"currency\": \"GBP\"}",
  "evidence": "evidence/origin.json",
  "method": "manual",
  "at": "2026-10-18T06:23:28.391493+00:00",
  "evidence_digest": "778dd9d4f5c902be15de622245fe308760b8dbf67fe8d52b54b02c8e86b9d271"
}
```

## requirement:R-2:1:052d62f8890f

Mode: manual
Expected: default currency is GBP
Status: retained

Manual applicability (original observation unchanged; no new execution):
```json
{
  "state": "current",
  "event_id": "e49825f1912d3c46789cfd2d5de341f045760d6aa3f3866f6eb33eb6738a8cce",
  "verdict": "supported",
  "original": {
    "item_id": "requirement:R-2:1:052d62f8890f",
    "history_index": 0,
    "result_hash": "3ff46b285cc6903ea076bd1c1c1e4c6da19a758dad93f0822f6e6e636b967689",
    "tested_revision": "5bd8195027408348901e7941af1280af12b18028"
  },
  "review_ref": ".agent-workflow/features/FEAT-001/verification.json#manual_scope_reviews/e49825f1912d3c46789cfd2d5de341f045760d6aa3f3866f6eb33eb6738a8cce",
  "observed_at": null,
  "original_registered_at": "2026-10-18T06:23:28.975169+00:00",
  "reviewed_at": "2026-10-18T06:27:56.576881+00:00",
  "reviewed_revision": "0e2116c95656b99641fb8ba3cf2246f4d4cb5983",
  "reason": "reviewed applicability; no new execution"
}
```

Latest recorded evidence (not necessarily current):
```json
{
  "status": "passed",
  "digest": "1c6b3eaedcb8392289d2674098d46c1b15e998c81e9cbe19b7213049342a4239",
  "tested_revision": "5bd8195027408348901e7941af1280af12b18028",
  "actual": "Original actual output: {\"conversion\": \"ABC\", \"currency\": \"GBP\"}",
  "evidence": "evidence/origin.json",
  "method": "manual",
  "at": "2026-10-18T06:23:28.975169+00:00",
  "evidence_digest": "2a731eb0824ab76c128e1766284509b0efd09af80ed0489ed9af8a8130066bbf"
}
```

## impact:B-1:e6e32d4c2286

Mode: manual
Expected: Convert input
Status: not_run

## impact:B-2:3c91ed1e9cb5

Mode: manual
Expected: Keep shared state
Status: not_run

## gate:unit:ae58977f2f47

Mode: automatic
Expected: Command succeeds: unit
Status: not_run
