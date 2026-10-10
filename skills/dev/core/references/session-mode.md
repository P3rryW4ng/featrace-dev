# Session delivery mode

Invoking `/dev` with no arguments activates delivery mode for the current Claude Code conversation and project. This is conversational state, not a file, repository setting, daemon, or host-level mode. It ends when the user says `dev off` or asks to exit delivery mode, when the project changes, or when the conversation ends. Never claim it persists into a new session or another project.

## Visible mode indicator

While this mode is active, start **every user-facing reply** (including read-only answers, progress updates, and questions) with one compact line: `FeatraceDev ON · 项目：<project>`. Localize the label to the user's language. Do not put the selected feature ID, title or `未选择` in this recurring indicator. If the project cannot be established reliably, say `待确认` instead of guessing. Keep the selected feature internally for routing; an explicit `--feature ID` for one command does not silently replace it, and never infer a selection from the only feature on disk. Before feature mutation, still identify and validate the actual target under `feature-selection.md`. This line is an Agent reply convention, not a persistent host status indicator or proof that the Skill remains loaded after a context reset.

An empty `/dev` is safe to repeat as a mode check: if already active for the same project, keep any reliable selection internally, display only the mode/project indicator and brief command guidance, and return without running `next`, scanning, listing features, creating records, or changing files. Do not summarize whether a feature is selected in this mode-check reply. If activation state is uncertain, treat the explicit `/dev` as a fresh activation for the current project; do not claim that an earlier mode survived. To inspect the selected feature and its progress, use plain `status` or `/dev status`; `list` shows available features. No separate mode file is needed.

## Activation

On activation:

1. Identify and display the current project.
2. Preserve an already reliable feature selection internally. Do not list features, display the selected feature, or announce that none is selected merely because mode was activated. If none exists, do not guess; `status`/`list` can show available features when requested, and `use ID` or `prd <path> --feature ID` can establish a selection.
3. State briefly that ordinary feature-delivery messages now default to `next`, and that bare command words are accepted in this conversation.
4. Do not scan, create records, or start development merely because the mode was activated.

If `/dev` includes free text that is not a recognized command, activate the mode and treat the text as `next` in the same turn when a feature is selected. If it clearly describes a new feature, use the readiness check in `feature-selection.md`: route to `prd` when its ID and accessible PRD source are present, or ask only for the missing prerequisites. Do not silently reinterpret an ordinary continuation as a new feature.

## While active

For later user messages in the same conversation and project:

- Treat ordinary feature-delivery descriptions as `next <description>` and follow `next-workflow.md`.
- Accept a bare recognized action at the start of the message (`prd`, `next`, `status`, `check`, `fix`, `clarify`, `revise`, `develop`, `api`, `figma`, `list`, `use`, `classify`, `archive`, `restore`, `scan`, `help`) as the corresponding dev action without requiring the `/dev` prefix.
- For a clearly new feature, including a bare incomplete `prd` request, use `feature-selection.md` before requiring an existing selection. A missing ID or PRD source produces the short readiness line and a focused question, not an inferred ID or a premature project write.
- Keep command parsing narrow. A normal sentence that merely contains one of those words remains natural-language input for `next`.
- Do not hijack unrelated conversation. Answer general questions normally unless they affect the selected delivery work.
- Continue to identify and validate project/feature identity before mutations under `feature-selection.md`; report the target in the action's own context, not in every mode indicator. Session mode never supplies a missing feature selection and never weakens an underlying gate.

Claude Code already owns slash commands such as `/status`; do not instruct the user to replace them. In delivery mode, use plain `status` for feature status, or the explicit `/dev status` form.

## Exit and limitations

`dev off`, `/dev off`, or an unambiguous request to exit disables the conversational default immediately and performs no workflow mutation. Report the exit in one line.

For that exit reply, display `FeatraceDev OFF` rather than an `ON` indicator. If the project changes, end the old project's mode and say it is off; the user can enter `/dev` again in the new project. After exit, do not display an `ON` line on ordinary replies or imply that the mode is still active.

The mode relies on Claude retaining and applying conversation context. It cannot guarantee activation after a new session, context reset, or host behavior that does not load the Skill. Cross-session always-on behavior would require project-level `CLAUDE.md` or `.claude/rules` installation and is intentionally outside this portable Skill because it would modify the user's project configuration.
