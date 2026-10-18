# Verification checklist

Generated view; manual observation and automated checks are distinct.

## requirement:R-1:1:5418d1630003

Mode: manual
Expected: abc becomes ABC
Status: stale

Manual applicability (original observation unchanged; no new execution):
```json
{
  "state": "stale",
  "event_id": "86a8d4d832b4be6ba0157e7bdb09e59025d968fb3ffc49f1fef2267a44643964",
  "verdict": "affected",
  "original": {
    "item_id": "requirement:R-1:1:5418d1630003",
    "history_index": 0,
    "result_hash": "16ed1fc68e459f8f6d2054fc40dc7e0eca836e95055105cd57a85f406a05c841",
    "tested_revision": "d10545de5b6ed49d28f0a666201111b96e3314ce"
  },
  "review_ref": ".agent-workflow/features/FEAT-001/verification.json#manual_scope_reviews/86a8d4d832b4be6ba0157e7bdb09e59025d968fb3ffc49f1fef2267a44643964",
  "observed_at": null,
  "original_registered_at": "2026-10-18T06:23:31.528836+00:00",
  "reviewed_at": "2026-10-18T06:28:48.451912+00:00",
  "reviewed_revision": "6c74cf52a8b6e3ae1c377917fc68afe2f9df20ae",
  "reason": "scope inputs changed or claim not supported/adopted"
}
```

Latest recorded evidence (not necessarily current):
```json
{
  "status": "passed",
  "digest": "a7d1970e887d63a4cb2fbac08e4a91743fef4b811d025efda011bcc462c1c096",
  "tested_revision": "d10545de5b6ed49d28f0a666201111b96e3314ce",
  "actual": "Original actual output: {\"conversion\": \"ABC\", \"currency\": \"GBP\"}",
  "evidence": "evidence/origin.json",
  "method": "manual",
  "at": "2026-10-18T06:23:31.528836+00:00",
  "evidence_digest": "6e0eebcb38173f496b7070fadc3d23c555ca4bce94cb2ba6d603cb6376f33fa8"
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
  "event_id": "86a8d4d832b4be6ba0157e7bdb09e59025d968fb3ffc49f1fef2267a44643964",
  "verdict": "supported",
  "original": {
    "item_id": "requirement:R-2:1:052d62f8890f",
    "history_index": 0,
    "result_hash": "4d2ee88c44192e38684378ef4ae9df49f17043ff20175bc0913a90b4dac0cf60",
    "tested_revision": "d10545de5b6ed49d28f0a666201111b96e3314ce"
  },
  "review_ref": ".agent-workflow/features/FEAT-001/verification.json#manual_scope_reviews/86a8d4d832b4be6ba0157e7bdb09e59025d968fb3ffc49f1fef2267a44643964",
  "observed_at": null,
  "original_registered_at": "2026-10-18T06:23:32.132545+00:00",
  "reviewed_at": "2026-10-18T06:28:48.451912+00:00",
  "reviewed_revision": "6c74cf52a8b6e3ae1c377917fc68afe2f9df20ae",
  "reason": "reviewed applicability; no new execution"
}
```

Latest recorded evidence (not necessarily current):
```json
{
  "status": "passed",
  "digest": "a7d1970e887d63a4cb2fbac08e4a91743fef4b811d025efda011bcc462c1c096",
  "tested_revision": "d10545de5b6ed49d28f0a666201111b96e3314ce",
  "actual": "Original actual output: {\"conversion\": \"ABC\", \"currency\": \"GBP\"}",
  "evidence": "evidence/origin.json",
  "method": "manual",
  "at": "2026-10-18T06:23:32.132545+00:00",
  "evidence_digest": "f32fe0d7b305ba3d03e36a83b4f6638e571cbe807eaf50e94ce3c19d502be108"
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
