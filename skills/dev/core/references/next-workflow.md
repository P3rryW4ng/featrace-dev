# Natural-language continuation (`next`)

`/dev next [description] [--feature ID]` is the normal continuation entry after a feature exists. In active session delivery mode, ordinary delivery messages are treated as this entry without requiring the `/dev next` prefix. It reduces command recall; it does not replace the underlying workflow contracts or create a second state machine. Apply `orchestration.md` to choose the professional stage and its minimal reference set.

## Resolve context first

Resolve the selected feature using `feature-selection.md`, reread its records and run the read-only status summary. `--feature ID` overrides only this invocation. If no reliable selection or explicit ID exists, list available features and ask the user to choose; never guess from recency or a sole directory. A new feature still starts with `/dev prd ... --feature ID`.

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
| Requirements are eligible and the user asks to implement or continue | `develop` |
| User asks to validate/accept the implementation | `check` |
| User asks what remains or whether it is done | Read `status` and existing evidence only; do not run check, builds, validation or audit unless fresh verification was explicitly requested. If complete, report that no required delivery step remains and offer archive as optional history management |
| User gives no description or explicitly says continue | Inspect `status`; execute the single required next workflow step only when it is unambiguous and already authorized. Otherwise report the blocker or focused choice |

An image is not automatically design evidence: a screenshot showing an actual failure belongs to `fix`; an expected visual or replacement asset belongs to `figma`; an image whose role is unclear requires one concise clarification before it is registered. A product explanation without a requested change may need no write. Multiple supplied items may form one route chain, such as `figma → reconcile → develop`; run required intermediate validation and report the chain.

## Ambiguity and safety

Inspect sources, decisions and current behavior before asking the user to classify the command. If two routes remain plausible, ask only when the distinction changes product authority or the record type. Preserve supplied evidence while waiting; do not call a defect a requirement change or treat a design export as product approval.

Do not use `next` to bypass restore, PRD review, impact, module, verification or check gates. Archived work must be restored before mutation. After source or semantic changes, follow the normal fresh review and develop validation order. Finish by reporting what route ran, records/code changed, remaining blocker and one recommended next action; do not make the user reconstruct a list of commands.
