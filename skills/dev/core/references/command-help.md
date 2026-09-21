# Command help

This is display guidance, not a request to execute examples. `/dev help` shows the five groups below, one short explanation and one example per command, plus help itself. `/dev help <command>` shows only that command's syntax from SKILL.md, when to use it, required/optional parameters, one example and the relevant distinction below. Keep explanations brief, in the user's language; use `$dev` for Codex and `/dev` for Claude. Unknown topics: state not supported and show available names; do not execute a guessed command. Do not require project access or feature selection for help.

## Overview (Chinese examples; localize when needed)

### 日常入口

| 命令 | 功能 | 示例 |
|---|---|---|
| mode | 当前会话进入开发模式，后续描述默认按 next 处理 | `/dev` |
| off | 退出当前会话的开发模式 | `dev off` |
| next | 读取当前进度，用自然语言自动选择并执行下一条现有流程 | `/dev next 我拿到了新的设计图片，路径是 ./assets/` |

### 需求准备

| 命令 | 功能 | 示例 |
|---|---|---|
| scan | 建立全局背景，或按模块核对相关实现 | `/dev scan --module wallet` |
| prd | 保留需求资料并创建需求、任务和验收记录 | `/dev prd ./prd.md --feature FEAT-001` |
| api | 补充接口资料并核对影响 | `/dev api ./api.yaml --feature FEAT-001` |
| figma | 补充设计资料并核对交互与视觉要求 | `/dev figma <设计链接或导出文件> --feature FEAT-001` |

### 开发处理

| 命令 | 功能 | 示例 |
|---|---|---|
| develop | 按已确认需求开发并维护证据 | `/dev develop FEAT-001` |
| clarify | 记录疑问或提议，调查后澄清 | `/dev clarify FEAT-001 返回时是否保留输入？` |
| fix | 登记实际异常，调查、修复并验证 | `/dev fix FEAT-001 返回后输入被清空` |
| revise | 记录并应用有确认依据的需求修订 | `/dev revise FEAT-001 增加草稿保存要求` |

### 检查交付

| 命令 | 功能 | 示例 |
|---|---|---|
| check | 生成验证列表、执行自动检查并列出剩余人工验收项 | `/dev check FEAT-001` |
| status | 只读查看进度、阻塞与下一步 | `/dev status FEAT-001` |

### 需求管理

| 命令 | 功能 | 示例 |
|---|---|---|
| list | 列出需求，可筛选模块或归档历史 | `/dev list --all --module wallet` |
| use | 选择本会话当前需求 | `/dev use FEAT-001` |
| classify | 设置需求所属模块标签 | `/dev classify FEAT-001 --module wallet` |
| archive | 将已完成且有验收依据的需求原地归档 | `/dev archive FEAT-001` |
| restore | 恢复已归档需求，保留原有历史 | `/dev restore FEAT-001` |

`/dev help` 查看总览；`/dev help next` 查看统一入口；`/dev help fix` 查看单个精确命令。选择需求后，同会话同项目的功能命令可省略 ID；新建 prd 仍必须明确 `--feature`，新会话不猜当前需求。

## Detail notes (show only the requested command)

- mode/off: empty `/dev` activates current-session delivery mode; `dev off` or `/dev off` exits. While active, plain delivery descriptions default to next and bare action words are accepted. It does not persist across sessions/projects or write a mode file. Claude Code `/status` remains built in; use plain `status` or `/dev status` for feature status.
- help: optional command name; no arguments shows overview. It does not run the described action.
- next: optional natural-language description and optional `--feature ID`; requires a selected or explicit existing feature. It reads status, announces and executes the applicable existing route. Questions about progress/problems stay read-only unless fresh verification is explicitly requested; plain continuation may execute one unambiguous authorized step. Images are classified by role: expected/replacement visuals use figma, failure screenshots use fix. New feature creation stays with prd; ambiguous product authority gets one focused clarification.
- scan: first project use or requested refresh. Plain scan refreshes project background; optional repeated --module labels select scoped dossiers plus declared dependencies/callers. Unknown modules require catalog investigation. No exhaustive understanding guarantee; existing current notes can be reused.
- prd: required file and `--feature ID`; optional repeated `--source file` for additional documents/HTML. One source suffices. Creates a new feature and refuses an existing ID; use revise for changed confirmed meaning, not another prd overwriting the same feature.
- api: required file/link; optional `--feature ID` when already selected. Supplementary API evidence is preserved through the single source-registration helper before reconciliation, not creation of a new feature. Remote retrieval needs an available connector or supplied export.
- figma: required link/export; optional `--feature ID` when already selected. Supplementary design evidence is preserved through the single source-registration helper before reconciliation; no automatic connector installation or assumption that every URL is readable.
- develop: optional positional ID after selection; starts/continues implementation. Includes relevant impact investigation and validation, not just record generation. Unresolved product choices need clarification.
- clarify: optional positional ID and required question/proposal. Use when expected behavior is unclear; confirmation and implementation are separate. It does not automatically authorize code edits. An observed failure belongs in fix; a confirmed change to requirement meaning uses revise.
- fix: optional positional ID and required observed problem. Preserve expected/actual behavior and investigate cause. Pure code defects keep requirement meaning unchanged; a requirement change discovered during investigation follows revise with approval evidence.
- revise: optional positional ID, required change description, optional repeated `--source file`. Use for corrections/additions to confirmed requirement meaning. Later text is not automatically authoritative; resolve approval and version conflicts before applying. Confirmation does not mean implementation or acceptance is complete.
- check: optional positional ID after selection. Generates acceptance rows, runs selected mapped checks and lists remaining manual work; may execute builds/tests. Builds do not automatically pass UI acceptance. A structural pass alone is not delivery completion. status only reports existing state.
- status: optional positional ID after selection. Read-only summary, not a fresh build/test or proof of completion.
- list: no ID; optional `--archived` for archive history or `--all` for both active/history, optional `--module label`. Default is active features. Lists without changing selection.
- use: required ID. Changes only this conversation's selection for this project, not Git branch or business status. New/uncertain context requires selection again.
- classify: optional positional ID; repeated `--module label` replaces labels, `--clear-modules` removes them. Labels help lookup, not automatic code classification or current-behavior authority.
- archive: optional positional ID; first runs preflight, preserves an existing report or creates a review-required draft from recorded evidence, and reports module/source/Git gaps. Only completed features with reviewed delivery evidence can be archived. Hides from default list, preserves files and history; not deletion or compression.
- restore: optional positional ID; returns archived feature to active list without erasing evidence. It does not itself rerun tests or invalidate/renew historical acceptance. Further code work follows normal rules.

Maintain this overview whenever commands or parameter semantics change. The main command table and per-workflow references remain authoritative; this help does not add new execution semantics.
