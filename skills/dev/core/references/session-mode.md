# Session delivery mode

Invoking `/dev` with no arguments activates delivery mode for the current Claude Code conversation and project. This is conversational state, not a file, repository setting, daemon, or host-level mode. It ends when the user says `dev off` or asks to exit delivery mode, when the project changes, or when the conversation ends. Never claim it persists into a new session or another project.

## Activation

On activation:

1. Identify and display the current project.
2. Preserve an already reliable feature selection. If none exists, do not guess: show the active feature list or explain that the user can enter `use ID` or create one with `prd <path> --feature ID`.
3. State briefly that ordinary feature-delivery messages now default to `next`, and that bare command words are accepted in this conversation.
4. Do not scan, create records, or start development merely because the mode was activated.

If `/dev` includes free text that is not a recognized command, activate the mode and treat the text as `next` in the same turn when a feature is selected. If it clearly describes a new feature and includes the required PRD source and explicit feature ID, route to `prd`; otherwise do not infer a new feature.

## While active

For later user messages in the same conversation and project:

- Treat ordinary feature-delivery descriptions as `next <description>` and follow `next-workflow.md`.
- Accept a bare recognized action at the start of the message (`prd`, `next`, `status`, `check`, `fix`, `clarify`, `revise`, `develop`, `api`, `figma`, `list`, `use`, `classify`, `archive`, `restore`, `scan`, `help`) as the corresponding dev action without requiring the `/dev` prefix.
- Keep command parsing narrow. A normal sentence that merely contains one of those words remains natural-language input for `next`.
- Do not hijack unrelated conversation. Answer general questions normally unless they affect the selected delivery work.
- Continue to display and validate project/feature identity before mutations. Session mode never supplies a missing feature selection and never weakens an underlying gate.

Claude Code already owns slash commands such as `/status`; do not instruct the user to replace them. In delivery mode, use plain `status` for feature status, or the explicit `/dev status` form.

## Exit and limitations

`dev off`, `/dev off`, or an unambiguous request to exit disables the conversational default immediately and performs no workflow mutation. Report the exit in one line.

The mode relies on Claude retaining and applying conversation context. It cannot guarantee activation after a new session, context reset, or host behavior that does not load the Skill. Cross-session always-on behavior would require project-level `CLAUDE.md` or `.claude/rules` installation and is intentionally outside this portable Skill because it would modify the user's project configuration.
