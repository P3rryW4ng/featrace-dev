# RESUME-001 — Formatting changes, approved original PRD

All product rules below are confirmed for this synthetic exercise. Module: formatting.

R-1 Preview: preview_label(text) returns the first 8 Python Unicode characters of text. Strings of at most 8 characters are returned unchanged. Empty string returns empty. No mutation or I/O. receipt_id(text) must keep its existing first-12-character behavior; it must not share a changed preview limit.

R-2 Status: status_label(text) strips leading/trailing whitespace and uppercases the remaining text using Python str.upper(). Empty or whitespace-only input returns empty. This rule does not change preview or receipt formatting.

Tests must assert meaningful boundaries and preserved receipt behavior. Python standard library only; no new dependencies or unrelated refactoring. Technical implementation choices are delegated to the Agent; product behavior above is fixed.
