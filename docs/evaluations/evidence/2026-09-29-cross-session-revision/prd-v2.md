# RESUME-001 — Approved product revision, v2

This is an approved requirement change replacing only R-1's preview limit from 8 to 6 Python Unicode characters. preview_label(text) returns the first 6 characters, with short and empty strings unchanged. A length-7 input must now be truncated, even though v1 returned it unchanged. Replace the previous 8-character acceptance criterion; do not treat this as a code defect against v1.

Preserve receipt_id(text)'s existing first-12-character behavior. R-2 status_label(text) is unchanged: strip leading/trailing whitespace, then Python str.upper(); whitespace-only input returns empty. Other original constraints stay unchanged. Preserve the original PRD and historical v1 results, but do not claim those results verify this new requirement. This revision is approved by the product owner in this synthetic exercise; no further product choice is pending.
