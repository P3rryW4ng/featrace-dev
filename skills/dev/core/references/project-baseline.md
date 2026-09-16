# Project baseline

`project.py scan <PROJECT>` inventories build manifests and chooses android or generic. It creates architecture.md, conventions.md and examples.md only if absent, so agent-reviewed notes survive rescans. On any stale result review and refresh those notes before coding.

Fingerprint version 1 records Git HEAD plus manifest hashes and names. New/deleted/changed manifests and changed HEAD invalidate it. It is not a full source-tree hash and does not prove architecture review is current after uncommitted source edits; inspect the current diff separately.

quality-gates.json is executable configuration: {"gates":[{"name":"unit","command":["python3","-m","unittest","discover"],"cwd":".","timeout_seconds":600}]}. Commands run without a shell in the project. Read and review them against project evidence first. Every listed gate is required. Empty configuration reports unavailable. Reports are evidence of one run, not reusable proof after code changes.
