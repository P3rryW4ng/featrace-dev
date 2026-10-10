# Natural-language continuation (`next`)

`/dev next [description] [--feature ID]` is the normal continuation entry after a feature exists. In active session delivery mode, ordinary delivery messages are treated as this entry without requiring the `/dev next` prefix. It reduces command recall; it does not replace the underlying workflow contracts or create a second state machine. Apply `orchestration.md` to choose the professional stage and its minimal reference set.

## Resolve context first

First distinguish a clear request to create a new feature from continuation of an existing one. A new-feature request uses the readiness check in `feature-selection.md` even when an older feature is selected: missing product ID or accessible PRD source is asked once before writes; with both present, route to the existing `prd` flow. Do not ask the user to choose an existing feature or provide an internal module name merely because no current selection exists.

For existing-feature work, resolve the selected feature using `feature-selection.md`, reread its records and run the read-only status summary. `--feature ID` overrides only this invocation. If no reliable selection or explicit ID exists, list available features and ask the user to choose; never guess from recency or a sole directory. New-feature creation still uses the underlying `/dev prd ... --feature ID` action, even when the user describes it in ordinary language.

State the selected route in one short line, including stages when useful, for example `Route: Requirement/figma → Scope → Build (new design assets for the current feature)`, then perform only the eligible portion rather than merely recommending its command. Underlying actions write their normal records and the stage handoff uses those records; `next` creates no separate routing file.

## Route by the role of the input

Use the user's meaning and current records, not isolated keywords:

| Input/state | Route |
|---|---|
| New design reference, replacement image, icon, screenshot of expected appearance, Figma node/export | `figma`; register accessible local evidence as `design`, reconcile affected requirements/tasks, then continue an explicitly requested development step |
| API contract, schema, response example or backend field evidence | `api`; register as `api` and reconcile before code |
| Observed behavior differs from expected behavior | `fix`; keep the observation even when cause is unknown |
| Expected behavior is unclear, alternatives need a product choice, or existing/new behavior may conflict | `clarify` |
| Confirmed correction/addition changes requirement meaning | `revise`; a newer message alone is not approval |
| Requirements are eligible and the user asks to implement or continue | `develop`; after the final task is done, continue through ordinary Verify and eligible Deliver without another prompt |
| User asks to validate/accept the implementation | `check`; continue to Deliver when all evidence supports closure, unless the request is explicitly check-only or read-only |
| Feature is already `complete` and the question is whether a later merge affects that accepted delivery | `post-merge-review.md`: inventory the exact diff, investigate each changed path and report historical delivery versus merged-revision scope separately; do not reopen or run full check merely because HEAD moved |
| User explicitly requests delivery/closure | Deliver under `verification-workflow.md`: save the feature-local report, wait for a separate full read to return, then compare evidence before a separate complete mutation; continue Verify first if applicable evidence is not current |
| User asks what remains or whether it is done | Read `status` and existing evidence only; do not run check, builds, validation or audit unless fresh verification was explicitly requested. If complete, report that no required delivery step remains and offer archive as optional history management |
| User gives no description or explicitly says continue | Inspect `status`; execute the unambiguous authorized next stage, including the Verify → Deliver continuation after development. Otherwise report the blocker or focused choice |

An image is not automatically design evidence: a screenshot showing an actual failure belongs to `fix`; an expected visual or replacement asset belongs to `figma`; an image whose role is unclear requires one concise clarification before it is registered. A product explanation without a requested change may need no write. Multiple supplied items may form one route chain, such as `figma → reconcile → develop`; run required intermediate validation and report the chain.

## Ambiguity and safety

Inspect sources, decisions and current behavior before asking the user to classify the command. If two routes remain plausible, ask only when the distinction changes product authority or the record type. Preserve supplied evidence while waiting; do not call a defect a requirement change or treat a design export as product approval.

Do not use `next` to bypass restore, PRD review, impact, module, verification or check gates. Archived work must be restored before mutation. After source or semantic changes, follow the normal fresh review and develop validation order. Finish by reporting what route ran, records/code changed, remaining blocker and one recommended next action; do not make the user reconstruct a list of commands.

## Explicit independent review

When the user explicitly asks for independent review, route to Verify using `independent-verify.md`. It is an opt-in read-only pilot. Do not invoke it automatically on plain next/check or a progress question, and do not silently replace fresh-context review with the current Agent.

When next reaches an authorized eligible develop step, load `build-strategy.md` and choose serial or two workers from current Scope evidence and expected benefit. The user need not type --parallel. Task count or “continue” alone does not justify concurrency; --serial/no-subagents is respected. Only an eligible pair loads `parallel-build.md`; status-only and planning-only requests never dispatch.

At each completed Build task boundary, the router loads `task-commit.md` and makes a scoped local commit after focused checks, unless the request or project policy prohibits committing or the task cannot be isolated safely. Do not wait for every task or final feature acceptance merely to save a completed slice. A local commit is not a request to push and does not imply `complete`.

When this was the last active task, continue automatically into ordinary Verify and then eligible Deliver under `verification-workflow.md`. If a gate fails, manual acceptance is missing, a product decision is unresolved, or final evidence is stale, keep `provisional`, preserve results and tell the user the smallest concrete input/action needed. When that input arrives, resume the unfinished verification/closure chain instead of asking for a new `check` or `complete` command. If no task is currently running, an authorized `next` may resume this same pending chain; a question about status remains read-only.
