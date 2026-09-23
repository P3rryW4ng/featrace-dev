# Feature Delivery Skill

把 PRD 转换为可追溯的需求、开发任务、代码修改和验证记录，帮助 Claude Code 或 Codex 在持续迭代中保留需求依据、决策和历史修复。

当前源码版本 **0.5.17**，提供通用工作流、Android 适配和 Generic 适配。一个用户入口在内部按 Requirement、Scope、Build、Verify、Repair、Deliver 六阶段加载规则；当前仍由同一 Agent 执行。Android 项目可从 Gradle 获得待人工确认的模块与依赖候选；iOS、Web 和后端项目可以使用通用流程，但暂时没有专属扫描适配器。

> Skill 能减少遗漏和上下文漂移，但不会自动证明 PRD 理解、依赖关系或最终实现完全正确。Agent 仍需读取实际资料、代码和验证结果。

## 安装

需要 Python 3.9+、Git，以及 Claude Code 或 Codex。Android 项目还需要其自身要求的 JDK 和 Android SDK。

```bash
git clone https://github.com/P3rryW4ng/feature-delivery-skill.git
cd feature-delivery-skill
python3 scripts/install.py
```

默认同时安装到当前用户的 Claude Code 和 Codex Skill 目录。也可以只安装一个：

```bash
python3 scripts/install.py --agent claude
# 或
python3 scripts/install.py --agent codex
```

安装完成后，请打开一个新的 Agent 会话。

## 会话开发模式

在需要开发的业务项目中打开 Claude Code，然后输入：

```text
/dev
```

这会让当前会话进入 Feature Delivery 开发模式。之后可以直接使用自然语言或裸命令，不必每次重复输入 `/dev`：

```text
scan
prd ./需求文档.md --feature OGFR-1234
继续开发当前需求
我拿到了新的设计图片，路径是 ./design/
status
check
```

退出当前会话的开发模式：

```text
dev off
```

会话模式有三个边界：

- 只对当前会话和当前项目有效；
- 新会话或切换项目后需要重新进入；
- 不会向业务项目写入永久的会话开关或修改个人规则。

Codex 使用 `$dev` 调用 Skill，例如 `$dev scan`、`$dev status`。在支持连续上下文的当前任务中，也可以先输入 `$dev`，再继续描述开发工作。

## 最小工作流

第一次在项目中使用：

```text
/dev
scan
prd ./prd.md --feature OGFR-1234
继续开发
check
status
```

各步骤的含义：

1. `scan`：了解项目、构建配置和模块边界；Android 项目会生成待确认的 Gradle 模块候选。
2. `prd`：保存需求来源，使用产品已经分配的需求编号创建工作区。
3. `继续开发`：Agent 根据当前状态进入澄清、拆解、编码、修复或验证流程。
4. `check`：执行已经选择的自动检查，并列出仍需人工确认的项目。
5. `status`：只读查看当前进度、阻塞和下一步。

已有需求可以先选择，再继续工作：

```text
list
use OGFR-1234
继续开发
```

成功创建 PRD 后，该需求会自动成为当前需求。同一会话、同一项目内，后续命令通常可以省略需求 ID。

## 日常只需记住

| 命令 | 用途 |
|---|---|
| `prd <文件> --feature <产品编号>` | 创建新需求 |
| `next <描述>` 或直接描述工作 | 让 Agent 根据当前状态选择下一流程 |
| `status` | 查看进度和阻塞，不重新运行构建 |
| `help` / `help <命令>` | 查看命令和使用时机 |
| `dev off` | 退出会话开发模式 |

不知道该用哪个命令时，优先输入：

```text
help
```

## 精确命令

精确命令适合明确指定处理方式，或者在重要步骤中减少自然语言歧义。

| 场景 | Claude Code | Codex |
|---|---|---|
| 扫描项目 | `/dev scan` | `$dev scan` |
| 创建需求 | `/dev prd ./prd.md --feature OGFR-1234` | `$dev prd ./prd.md --feature OGFR-1234` |
| 继续当前需求 | `/dev next 继续开发` | `$dev next 继续开发` |
| 查看进度 | `/dev status` | `$dev status` |
| 查看需求列表 | `/dev list` | `$dev list` |
| 切换需求 | `/dev use OGFR-1234` | `$dev use OGFR-1234` |
| 补充 API | `/dev api ./api.yaml --feature OGFR-1234` | `$dev api ./api.yaml --feature OGFR-1234` |
| 补充设计 | `/dev figma <链接或导出文件> --feature OGFR-1234` | `$dev figma <链接或导出文件> --feature OGFR-1234` |
| 澄清需求 | `/dev clarify OGFR-1234 <疑问>` | `$dev clarify OGFR-1234 <疑问>` |
| 修订需求 | `/dev revise OGFR-1234 <修订说明>` | `$dev revise OGFR-1234 <修订说明>` |
| 记录并修复偏差 | `/dev fix OGFR-1234 <实际问题>` | `$dev fix OGFR-1234 <实际问题>` |
| 确认能力与模块职责 | `/dev classify OGFR-1234` | `$dev classify OGFR-1234` |
| 开发 | `/dev develop OGFR-1234` | `$dev develop OGFR-1234` |
| 检查与验收 | `/dev check OGFR-1234` | `$dev check OGFR-1234` |
| 归档／恢复 | `/dev archive OGFR-1234` / `/dev restore OGFR-1234` | `$dev archive OGFR-1234` / `$dev restore OGFR-1234` |

### 什么时候用 clarify、revise 或 fix

- `clarify`：需求存在疑问，需要调查或请产品确认；确认不代表已经实现。
- `revise`：已经确认要修改或补充需求含义；保留原 PRD 和修订历史。
- `fix`：已经观察到实现效果与预期不符；先记录实际现象，再判断是代码缺陷、需求遗漏还是需求变化。

普通说明不一定需要专门命令；会影响需求、实现或验收结论的内容应当留下记录。

## PRD 和补充资料

一个需求可以只有文档、只有 HTML 交互稿，也可以由多份资料共同组成：

```text
/dev prd ./产品需求.md --feature OGFR-1234 --source ./prototype.html
```

后续拿到 API 或设计资料时，不需要重建需求：

```text
/dev api ./api.yaml --feature OGFR-1234
/dev figma ./figma-export.md --feature OGFR-1234
```

来源存在冲突时，Skill 会保留冲突并要求确认，不会因为文件更新时间更晚就自动覆盖已经确认的需求。

## 业务能力和代码模块

业务能力不必强行归入一个代码模块。例如“红包”可以由钱包模块负责业务规则，同时由聊天模块负责展示。Agent 会推荐相关模块及 `owner`、`host`、`provider`、`consumer` 或 `shared` 职责，并在有歧义时请用户确认。

Android scan 生成的 Gradle 关系只是候选：

- 不会自动成为正式模块目录；
- 不代表业务归属；
- 不代表完整运行时调用图；
- 动态 Gradle、导航、反射和外部服务仍需人工调查。

## 项目中会生成什么

业务项目会创建 `.agent-workflow/`，用于保存需求、任务、决策、追溯、修复、验证和模块记录。它与 Skill 源码仓库分开。

通常适合团队共享：

- 当前需求、任务、决策和追溯关系；
- 已审阅的模块说明；
- 可共享的交付报告和修复结论。

通常只保留本机：

- 原始 PRD、日志或含敏感信息的来源；
- 扫描草稿和历史备份；
- 本机质量命令选择及临时运行结果。

首次使用时，Agent 可以配置 `.agent-workflow/.gitignore`。上传前仍应按业务仓库权限检查具体内容；Skill 不会自动提交、推送或上传项目资料。

## 更新

进入已经克隆的 Skill 仓库：

```bash
git pull --ff-only
python3 scripts/install.py --agent claude --update
```

Codex 用户把 `claude` 换成 `codex`；两个工具都更新则使用 `both`。更新后打开新会话，旧会话可能仍使用已经加载的旧规则。

## 卸载

```bash
python3 scripts/install.py --agent claude --uninstall
```

安装器会把旧副本移到 `~/.feature-delivery/backups/`，不会直接永久删除。若安装目录没有本工具的安装标记，或内容被本地修改，安装器会拒绝覆盖。

## 常见问题

### Claude Code 提示 `Unknown skill: dev`

1. 确认执行过 `python3 scripts/install.py --agent claude`；
2. 确认安装输出没有冲突错误；
3. 关闭旧会话并打开新会话；
4. 检查 `~/.claude/skills/dev/` 是否存在。

### 更新后行为还是旧版本

`git pull` 只更新源码仓库，还需要再次运行安装器的 `--update`。Agent 通常在会话开始时加载 Skill，因此还需要新开会话。

### 不知道下一步做什么

进入会话模式后直接输入：

```text
status
```

或：

```text
继续当前需求，并告诉我现在的阻塞和下一步
```

### 构建通过是否代表需求完成

不代表。UI、真机、账号、开关和跨页面流程可能仍需人工验收。`check` 会区分自动检查和剩余人工项目；证据不足时需求应保持 provisional。

### 能否保证每次扫描都不遗漏

不能。扫描和候选图用于缩小调查范围，动态依赖、未登记调用、运行时行为和外部系统仍可能需要扩大调查。

## 使用文档

- [完整使用与迭代指南](docs/usage.md)
- [版本变更记录](CHANGELOG.md)
- [模块与能力范围说明](skills/dev/core/references/module-context.md)
- [Git 协作和来源共享规则](skills/dev/core/references/git-sharing.md)

## 项目维护者

以下文档用于维护 Skill 自身，不是普通使用的必读内容。保留在仓库中是为了让其他机器、账号和 Agent 能准确接续开发，避免依赖单次会话记忆。

- [产品方向基线](PRODUCT.md)
- [项目维护总览与交接](MAINTAINER.md)
- [开发路线图与阶段计划](ROADMAP.md)
- [架构与产品决策](docs/decisions/architecture.md)
- [验证与评估记录](docs/validation.md)

仓库当前尚未选择开源许可证。公开分发或再发布前，请由仓库所有者明确许可范围。
