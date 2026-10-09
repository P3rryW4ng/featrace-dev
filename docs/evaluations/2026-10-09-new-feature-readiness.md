# 0.5.44 安装版新需求入口隔离复核（2026-10-09）

目的：验证 Agent 是否在真实调用安装版 `/dev` 时，只追问创建新需求所缺的产品编号或 PRD，随后自行调查模块职责；不把合成演练当作真实需求收益。

安装版：`/Users/mac/.claude/skills/dev`，版本 0.5.44；安装标记、源码及安装目录的 78 个运行文件哈希一致。三个场景使用新建的 `/private/tmp/featrace-new-feature-0544` 和 `/private/tmp/featrace-new-feature-full-0544` Git 夹具，Claude Code 原生 `claude -p` 分别调用。没有使用业务项目或旧会话记录。

| 场景 | 输入与实际结果 | 写入及边界 |
|---|---|---|
| 编号、PRD 都缺 | 回复 `新需求准备 · 编号：待提供 · PRD：待提供 · 模块：待调查`，只询问两项；不要求模块名 | 无 `.agent-workflow`，无需求创建；约 12.8 秒，CLI 计费估值 USD 0.212 |
| 已有可读 PRD，只缺编号 | 回复 `编号：待提供 · PRD：requirement.md（可读取）· 模块：待调查`，只询问产品编号 | 无 `.agent-workflow`，原 PRD 未改；约 14.7 秒，CLI 计费估值 USD 0.232 |
| 编号与 PRD 齐全 | 输入 `DEMO-544` + `prd.md`；Agent 创建并选中草稿，原始 PRD 字节另存；按 `src/chat/receipt.py` 对 `src/wallet/payment.py` 的导入，推荐 wallet=owner、chat=host，并提出确有歧义的重复提交语义问题 | draft 校验 `FEATURE_VALID`（有 S-3 等待决 warning）；`requirements.json` 中 `module_scope.status=pending`，没有业务代码、构建或提交。约 110 秒，CLI 计费估值 USD 0.872 |

第三个夹具只含两份 Python 文件和 PRD，没有项目构建或规则文件。Agent 没有为凑模块目录把 PRD 冒充构建依据，候选目录留在 `.agent-workflow/modules/drafts/index.candidate.json`；正式目录无法登记，模块职责只停留在有代码依据的推荐，没有升级为已确认 Scope。它另提出添加项目规则文件的工程问题；这是该极简夹具的边界，不是产品选择，也未证明在真实项目可零额外提问。

本次只改 Agent 指令与文档，未改 Python 脚本；未重跑全量 unittest。已运行 `git diff --check` 和安装哈希核对。三条原生回复证明入口提示与初步模块调查可用，不证明 PRD 解读、正式 Scope、开发或交付正确，也未测自然会话、已有需求切换、长会话和成本收益。
