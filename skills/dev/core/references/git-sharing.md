# Git sharing contract

## Two repositories

The Skill repository tracks runtime sources, installer, synthetic tests, version/changelog and maintenance docs together. Never copy a real project's `.agent-workflow`, sources or personal installation into it. The Skill repository's root ignore of `.agent-workflow/` is intentional; never replace it with the business-project policy.

A business repository may share reviewed current baselines and feature records with its authorized collaborators. At first use or when adopting this policy, run `python3 core/scripts/setup-workflow-git.py <PROJECT>`. It appends the bundled block to `.agent-workflow/.gitignore`, preserving existing rules. It never stages, untracks, commits or pushes. It reports conflicting parent ignores and already tracked ignored paths. Resolve those using project policy and existing user authorization; do not blindly remove a repository-wide exclusion or use `git add -f` on the whole workspace.

| Business-project content | Default |
|---|---|
| `.agent-workflow/.gitignore`, shareable `config.yaml` | Track after review |
| Current inventory, architecture, conventions, examples, coverage and evidence registry | Track after review; use project-relative evidence paths |
| `quality-candidates.json` | Track shareable templates and rationale |
| Feature requirements/intake (including module labels and archive history), tasks, decisions, traceability, fixes.json/fixes.md, generated review views and curated delivery conclusions | Track together after content review |
| `fingerprint.json`, selected `quality-gates.json`, raw `quality-report.json` | Ignore: machine/revision-specific state and raw execution output |
| Draft, managed/manual scan backups, lock, recovery and scratch directories | Ignore; local recovery only |
| `features/*/sources/**` original PRD/API/design artifacts | Ignore by default until repository access and sharing permission are established |

Ignored sources are not automatically harmless when summarized: intake quotes, specifications, paths and reports can expose the same content. Review all proposed changes against repository access, not merely file extensions. The ignore template is hygiene, not a secret scanner or access-control mechanism. It preserves custom rules; effective behavior must be checked with Git.

For approved source sharing, append an exact exception after the managed block, e.g. `!/features/FEAT-001/sources/prd-original.md`. For nested sources also unignore the required intermediate directories. If sources are shared elsewhere, collaborators must obtain the same bytes through that authorized channel and restore the recorded relative paths. Missing sources cannot be relabeled not_applicable merely to pass validation; stop dependent review/development until restored. Full portable source version/authority management is still deferred.

## Fresh clone / another machine

1. Read existing feature records and baseline notes; never initialize over them or replace reviewed notes with placeholders.
2. Run setup and `project.py verify <PROJECT>`. A missing ignored fingerprint means local validation is needed, not that shared analysis disappeared.
3. Use `scan-prepare`, inspect current manifests, root rules, registered evidence and local diff against the shared notes; retain valid notes and update only verified changes/gaps in the draft. Do not claim an incremental scan: there is no old local fingerprint to compare on first clone.
4. Review evidence availability and coverage. `scan-publish` establishes the local fingerprint; then `verify` and `validate-gates`. Missing ignored quality selection is initialized empty. Select commands for this machine and task before check; never infer previous checks passed here.
5. Missing original sources or stale PRD review must be resolved independently of baseline validity. Run the appropriate feature validation before continuing development.

Fingerprint includes Git HEAD; after a commit it may become stale even when shared notes remain valid. Review actual changes before refresh; do not repeatedly commit fingerprint updates. Existing tracked ignored files remain tracked: review exact paths with the user/project authorization before removing them from the index while preserving local copies. Ignore rules do not erase Git history. Never rewrite history or publish changes as a side effect of setup.
