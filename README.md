# Feature Delivery Skill

**让变化的需求，成为可验证的软件交付。**

Feature Delivery 帮助 Coding Agent 在已有代码库中处理需求、调查影响、开发、修复和验收。它把原始资料、已确认的需求、开发任务、历史修复和测试证据连起来，让下一次改动有据可查，也让“完成”有明确的验证范围。

适用于 Claude Code 和 Codex；目前提供通用工作流及 Android 适配。本仓库源码正在验证 **0.5.19 候选版**；已发布版本以 Git 记录和本机安装版本为准。

> 当前是开发者参与的交付工具。它会提醒缺失的决策与证据，但不能保证自动理解所有 PRD、发现所有代码依赖，或替代真机与主观体验验收。

## 安装

需要 Python 3.9+、Git，以及 Claude Code 或 Codex。Android 项目还需项目本身要求的 JDK 和 Android SDK。

```bash
git clone https://github.com/P3rryW4ng/feature-delivery-skill.git
cd feature-delivery-skill
python3 scripts/install.py
```

默认安装到当前用户的 Claude Code 和 Codex。只安装一个工具时使用 `--agent claude` 或 `--agent codex`。安装后打开**新会话**，使 Agent 加载新版本。

## 从这里开始

在业务项目中打开 Claude Code，输入一次 `/dev` 进入当前会话的开发模式。之后直接说要做什么，不必反复输入 `/dev next`：

```text
/dev
scan
prd ./需求文档.md --feature OGFR-1234
继续开发当前需求
我补充了新的设计稿，请核对影响
status
```

`OGFR-1234` 应是产品或项目已经分配的编号；Skill 不会自行编造。首次使用项目时运行 `scan`，让 Agent 了解构建方式和模块候选。创建需求后，该需求会成为当前会话、当前项目的选中需求。

在 Codex 中用 `$dev` 调用，例如 `$dev scan` 和 `$dev prd ./需求文档.md --feature OGFR-1234`。Claude Code 会话中的开发模式可用 `dev off` 退出；新会话或切换项目后需要重新进入。该模式不会向业务项目写入永久开关，也不保证跨会话保留。

### 日常只需记住这些

| 输入 | 什么时候用 |
|---|---|
| `prd <文件> --feature <产品编号>` | 创建新需求，登记原始资料 |
| 直接描述工作，或 `next <描述>` | 让 Agent 根据当前需求状态选择下一步 |
| `status` | 查看已有进度、阻塞和下一步；不重跑构建 |
| `list` / `use <产品编号>` | 查找并切换需求 |
| `check` | 执行所选检查，列出仍需人工验收的项目 |
| `help` / `help <命令>` | 查看全部精确命令及使用时机 |
| `dev off` | 退出 Claude Code 当前会话的开发模式 |

不确定命令时，直接说明情况，例如“返回按钮没有按确认的行为工作”“这份 PRD 改了开关规则”“我拿到了新的交互稿”。Agent 应分别调查故障、处理需求修订或补充来源；影响产品含义的选择仍需你确认。

## 它怎样帮助交付

1. **理解变化**：保留原始 PRD、设计、API 或 HTML 交互稿；把澄清、修订和已确认需求分开记录。单份资料或多份资料都可以开始。
2. **调查影响**：定位相关模块、调用关系和应保持不变的行为，并提示可能需要重测的历史修复。Android Gradle 关系只作为待确认候选，不冒充完整调用图。
3. **开发与验证**：把需求关联到任务和代码，运行实际选定的检查，分清自动测试、人工目视及真机结果。失败和过期证据不会自动变成通过。
4. **接续与回看**：业务项目的 `.agent-workflow/` 保存当前需求、决策、修复与交付记录；换会话或换开发者时可从记录继续，而不是依赖聊天记忆。

一个需求可以跨模块。例如红包规则在钱包模块，红包展示在聊天模块；Skill 会提出候选职责和证据，而不会因为功能名称就自动认定唯一归属。

内部流程目前分为 Requirement、Scope、Build、Verify、Repair、Deliver 六个按需加载的阶段，**仍由同一个 Agent 执行**。阶段名称是工作边界，不是六个要记住的新命令，也不表示已经具备独立 Agent 的自动交付能力。

## 补充资料与修复

创建需求时可以同时提供文档和交互稿：

```text
prd ./产品需求.md --feature OGFR-1234 --source ./prototype.html
```

后续补充 API 或设计资料，不必重建需求：

```text
api ./api.yaml
figma ./设计导出.md
```

需要明确指定处理方式时，可以使用 `clarify`（调查疑问）、`revise`（修订已确认需求）或 `fix`（记录效果偏差并调查修复）。来源更新时间更晚，不会自动覆盖已经确认的需求；修复中的代码缺陷也不会被自动改写成 PRD 变更。完整参数和其他命令见[使用与迭代指南](docs/usage.md)。

## 项目记录与共享

Skill 源码仓库与业务项目的 `.agent-workflow/` 是两处不同位置。当前需求、任务、决策、追溯及已审阅的模块说明通常可以按团队规则共享；原始 PRD、日志、扫描草稿及本机质量命令可能含敏感或环境相关信息，应逐项检查。Skill 不会因初始化而自动提交、推送或上传业务资料。更多说明见 [Git 协作规则](skills/dev/core/references/git-sharing.md)。

## 更新与卸载

在已克隆的 Skill 仓库中：

```bash
git pull --ff-only
python3 scripts/install.py --agent both --update
```

更新后打开新会话。只更新一个工具时，把 `both` 改为 `claude` 或 `codex`。卸载使用 `python3 scripts/install.py --agent both --uninstall`；安装器将旧副本放入 `~/.feature-delivery/backups/`。若安装目录不属于本工具或曾被本地修改，安装器会拒绝覆盖。

若 Claude Code 提示 `Unknown skill: dev`，请确认已安装到 `~/.claude/skills/dev/`，并打开新会话。Codex 入口为 `$dev`。

## 更多信息

- [完整使用与迭代指南](docs/usage.md)
- [版本变更记录](CHANGELOG.md)
- [项目维护者入口](MAINTAINER.md)

仓库当前尚未选择开源许可证。公开分发或再发布前，请由仓库所有者明确许可范围。
