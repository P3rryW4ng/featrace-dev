# Project workflow compatibility (0.11.2)

Load before the first substantive project operation in a conversation, after switching project/worktree, or when applicable configuration changes or a hook rejects an operation. Help, mode-only activation and read-only status do not trigger this inventory. This is an Agent review, not a host configuration switch or automatic conflict detector.

## Inspect only applicable configuration

Read the project's rule entrypoints and relevant imports, the target path's scoped rules, and the configured hooks governing the intended operation. List project-local workflow entrypoints by name/description before opening their details; inspect a competing workflow only when it is selected, mandated, has relevant active state, or governs a hook. Do not recursively enumerate nested worktrees, dependency trees or historical changes. Do not dump user settings, environment variables, permission lists or secrets; inspect only relevant setting keys and hook references. User-level settings need inspection only when the project inspection cannot explain a concrete conflict.

Classify what you actually read:

- Project standards: architecture, coding, UI, source authority and collaboration constraints. Keep them applicable regardless of the chosen delivery workflow; load specialist rules only for their target scope.
- Workflow ownership: another router's requirement/task/verification/archive records and transition rules. Installed or discoverable does not mean selected or active. An explicit FeatraceDev request identifies the requested router, but does not silently cancel a conflicting mandatory project process or someone else's active change.
- Execution constraints: build authorization, write scope, tool/commit hooks and environment limitations. Skill visibility does not disable injected rules or hooks. Inspect a hook's selection and path logic before attributing its rejection to the current feature; another active change may be controlling it.

## Reconcile before the affected action

If there is no concrete conflict, continue without a workflow-choice questionnaire. Use FeatraceDev's canonical feature records for the work it owns and keep compatible project specialists available. Do not run a second router merely because it exists or mirror every phase into its records.

If an applicable mandatory process competes for ownership, or a hook blocks the requested operation, identify the exact rule/hook path, actual active record and operation it affects. Ask only for the unresolved ownership or policy decision; continue authorized independent read-only investigation. A collaborator's active change is not permission to advance, archive or rewrite it. Do not evade a rejection using a different writing tool, disabling hooks, forcing phase state or editing host configuration. A local workflow selection alone cannot resolve an enforced hook conflict.

For build/test/commit permissions, use existing session authorization for the same scope. Ask only where a specific project rule or actual permission boundary still requires it; explain the source and requested operation. Workflow selection is not a blanket authorization for every command. Once permitted, resume the original stage rather than restarting project setup or repeating current tests.

Default compatibility handling does not install/uninstall competing skills, write skillOverrides, alter CLAUDE.md/AGENTS.md/settings/hooks, or create/modify another workflow's records. If the user explicitly requests a configuration change, first inspect the supported host/project contract and propose the smallest scoped change; do not assume a key mentioned in chat is valid. Preserve unrelated configuration and collaborators' state.

## Recoverable summary without another state machine

On authorized scan/setup, summarize reviewed compatibility facts in the existing baseline conventions.md and coverage.md through the normal draft/publish route: source paths/sections, applicable scope, chosen owner, execution constraints and unresolved conflicts. Register relevant project-local rule/hook files in evidence-files.json when relied on; exclude personal settings and secrets. This records observed policy, not a permanent user permission or persistent session mode.

Outside scan, reuse current notes and inspect the live applicable configuration; do not refresh the baseline or run builds solely for compatibility. Hold any new observations in the stage handoff until an authorized baseline/module review can persist them. Missing notes are not a universal development blocker. Recheck changed or newly applicable configuration and unavailable sources; stale notes cannot override current rules. Do not make every feature stale merely because an unrelated workflow was installed.

Pass specialists only the constraints applicable to their assigned paths, tools and permitted outputs. Report the chosen owner and any material conflict in a concise update, not a full installed-skill inventory. Agent review cannot guarantee detection of dynamically injected or remote configuration; unexplained tool rejection stays a concrete blocker.
