# Feature Delivery Skill

把 PRD 转换为可追溯的需求、开发任务和验证记录，支持后补 API / Figma、冲突决策和持续迭代。

当前源码版本 **0.5.12**：通用工作流 + Android 适配 + Generic 适配。iOS/Web/后端可用通用流程，但没有专属自动化适配器。此工具由 Agent 执行需求理解和编码，脚本负责部分确定性检查；不能保证零遗漏或零 bug。

## 最快开始

需要 Python 3.9+、Git，以及已安装的 Claude Code 或 Codex。macOS/Linux 可运行全部脚本；Windows 建议 WSL。Android 构建另需项目所要求的 JDK/SDK。旧 Android 关键词扫描脚本还需要 rg。

```bash
git clone https://github.com/P3rryW4ng/feature-delivery-skill.git
cd feature-delivery-skill
python3 scripts/install.py
```

默认安装到当前用户的 Claude Code 和 Codex 技能目录。只用一个工具时：

```bash
python3 scripts/install.py --agent claude
# 或
python3 scripts/install.py --agent codex
```

私有仓库用户需要先获得访问权限；使用自己现有的 Git 认证。安装过程不联网、不修改 CLAUDE.md、不复制项目业务资料。复制安装后可以移动仓库目录，已安装 Skill 仍能工作。

在目标业务项目中打开 Agent 会话，输入：

| 场景 | Claude Code | Codex |
|---|---|---|
| 进入会话开发模式 | `/dev` | `$dev` |
| 继续当前需求 | `/dev next 我拿到了新的设计图片，路径是……` | `$dev next 我拿到了新的设计图片，路径是……` |
| 需求列表 | `/dev list` | `$dev list` |
| 查看归档 | `/dev list --archived` | `$dev list --archived` |
| 修订需求 | `/dev revise FEAT-001 修订描述 --source /路径/补充.md` | `$dev revise FEAT-001 修订描述 --source /路径/补充.md` |
| 归档／恢复 | `/dev archive FEAT-001` / `/dev restore FEAT-001` | `$dev archive FEAT-001` / `$dev restore FEAT-001` |
| 模块分类 | `/dev classify FEAT-001 --module wallet` | `$dev classify FEAT-001 --module wallet` |
| 切换需求 | `/dev use FEAT-001` | `$dev use FEAT-001` |
| 扫描项目 | `/dev scan` | `$dev scan` |
| 拆解 PRD | `/dev prd /路径/需求.md --feature FEAT-001` | `$dev prd /路径/需求.md --feature FEAT-001` |
| 开发 | `/dev develop FEAT-001` | `$dev develop FEAT-001` |
| 澄清与补充 | `/dev clarify FEAT-001 疑问或提议` | `$dev clarify FEAT-001 疑问或提议` |
| 修复偏差 | `/dev fix FEAT-001 问题描述` | `$dev fix FEAT-001 问题描述` |
| 查看进度 | `/dev status FEAT-001` | `$dev status FEAT-001` |
| 自测检查 | `/dev check FEAT-001` | `$dev check FEAT-001` |

成功创建 PRD 后自动选中该需求；或用 `use` 选择已有需求。同一会话、同一项目内，后续可省略 ID，例如 `/dev develop`、`/dev fix 问题描述`。新会话重新选择；显式 ID 仅覆盖本次调用。选择保存在 Agent 会话上下文，不写入共享文件。

日常只需优先记住三个入口：`prd` 创建新需求，`next` 继续当前需求，`status` 只读查看进度。`next` 会根据描述和当前记录自动进入补设计、补接口、澄清、修订、修复、开发或验收流程；现有精确命令仍可直接使用。Claude Code 中还可先输入一次 `/dev` 进入当前会话的开发模式；之后普通描述默认按 `next` 处理，也可直接输入 `prd …`、`status`、`check` 等裸命令。输入 `dev off` 退出；新会话或切换项目后需重新进入。

0.5.0 可按需启用需求基线修订：保留原 PRD，单独记录修订，通过确认与版本检查更新现有需求 JSON；确认版本与已验收版本分别显示。`--source` 可省略，已有需求不会批量迁移，模块索引与自动传播尚未实现。

归档保留原目录与历史证据，仅从默认活动列表隐藏；`/dev list --all --module wallet` 可按模块找历史。`/dev archive` 先做预检：已有报告不覆盖，缺报告时从现有记录生成带待审标记的草稿，并提示模块候选与 sources 的 Git 保存状态；审阅前不会正式归档。归档需完成状态与交付依据，继续修改前恢复。归档不压缩文件，也不代表模块现状已自动整理。

`clarify` 将影响需求或验收的疑问记入现有决策文件，先调查、再确认并同步；普通解释不强制登记。已观察到效果不符用 `fix`，两个入口可共享决策。普通对话留痕依赖 Skill 已加载和 Agent 识别，显式命令更可靠。

开发前和检查前会按已登记模块与代码路径查找当前及其他需求中的 verified FIX。同步只发现候选；明确要求只同步或列出时保持待判断。候选变化或移除后，旧结论留在只读历史中，但不再满足当前门禁。该机制不会自动重开旧问题，也不把候选列表宣称为完整依赖分析。

补接口：`/dev api /路径/api.yaml --feature FEAT-001`；补设计：`/dev figma <链接或导出文件> --feature FEAT-001`。Agent 会把可访问的本地证据一次登记到来源清单与需求路径，避免两处手工同步。Codex 替换开头为 `$dev`。这些输入发给 Agent，不是在终端运行的命令。在线资料需要已有连接器或可读取的导出文件。

Claude Code 的 `/dev` 来自标准个人 Skill 目录；Codex 用 `$dev` 显式选择 Skill。参见 [Claude 官方说明](https://code.claude.com/docs/en/skills) 和 [Codex 官方说明](https://learn.chatgpt.com/docs/build-skills)。首次安装后打开新会话；若仍未出现，检查安装输出中的目录和工具配置。

## 更新和卸载

先在终端进入你克隆的 `feature-delivery-skill` 仓库目录，再执行：

```bash
git pull --ff-only
python3 scripts/install.py --agent claude --update
```

Codex 用户将 `claude` 换成 `codex`；两个工具都使用则换成 `both`。`git pull` 只更新仓库，必须再运行安装脚本才会更新个人 Skill 副本。完成后打开新的 Agent 会话，避免旧会话继续沿用已加载的规则。

从 0.3 升级到 0.4 不会自动改写业务项目。已有需求继续开发前，请让 Agent 按新版 PRD 分析规范补齐读取清单、原文关联和实际复核；不要重新初始化已有需求。可直接说：“按新版 PRD 分析规范补齐 FEAT-001 的读取与覆盖记录，保留现有需求和决策，复核后再继续开发。”

如果提示本地修改或安装归属冲突，先备份并核对改动，不要强制覆盖。通过其他安装器或手动复制安装的用户，应使用原安装方式升级，或备份旧安装并移出发现目录后再运行本安装器；本脚本不会接管没有安装标记的目录。

卸载示例：

```bash
# 只卸载 Claude：
python3 scripts/install.py --agent claude --uninstall
```

更新/卸载会把本工具安装的旧副本移到 `~/.feature-delivery/backups/`，不永久删除。若目标是别人的同名 Skill、符号链接或已被本地修改，安装器拒绝覆盖。每个目标单独备份；安装多个目标不是跨目录事务，遇到系统错误可修复后重试。

## 扫描修正（0.4.1）

扫描需交叉核对模块事实、保留规则例外并记录分析覆盖。检查候选与本次执行清单分离，配置可独立验证而不启动构建。旧质量配置若含字符串命令或 when 字段，需按 [使用指南](docs/usage.md) 迁移。

## PRD 分析一致性

导入时先登记读取范围与缺口，再保留带上下文的原文条目，并核对条件、例外到需求的对应关系。`spec/prd-analysis.md` 是生成的分析视图；JSON 规格仍是业务权威。缺少读取记录或复核已过期会阻止开发。脚本不自动证明语义正确，详见 [使用指南](docs/usage.md)。

## 从旧版迁移

旧 `android-feature-delivery` 本体与新 `dev` 分开。安装脚本不会移除旧 Skill，也不会修改个人 `CLAUDE.md`。如果此前添加了 `@~/.agents/skills/android-feature-delivery/SKILL.md`，启用新版前应从个人规则中移除那条旧导入，并把旧 Skill 备份到技能发现目录之外，避免两个版本同时引导工作。0.3 项目 JSON 可继续读取，但继续开发前需要补齐 `prd-intake.json` 和复核；旧 YAML 必须按 [使用指南](docs/usage.md) 重建和校验，不能当成已自动迁移。

## 仓库结构

```text
feature-delivery-skill/
├── skills/dev/              可单独安装的完整 Skill
│   ├── SKILL.md             唯一运行入口
│   ├── core/                规格、校验、渲染、通用脚本
│   └── profiles/            android / generic
├── scripts/install.py       安装、更新、卸载
├── tests/                   隔离回归测试（合成资料）
├── docs/                    使用说明与架构决策
├── MAINTAINER.md             接手入口
├── ROADMAP.md                下一优先项与边界
├── CHANGELOG.md
└── VERSION
```

业务项目运行时创建自己的 `.agent-workflow/`；Skill 仓库不保存真实 PRD、项目状态或接口资料。若项目记录只需本机保留，在业务仓库通过 `git rev-parse --git-path info/exclude` 找到本地排除文件，追加 `.agent-workflow/`。忽略规则不影响已经被跟踪的文件，应先检查 Git 状态。

## 维护

目标、当前进度、阶段计划、决策和验证资料统称“项目维护文档”，文件分工及阅读入口见 [项目维护总览与交接](MAINTAINER.md)。未来计划与问题处理状态统一见 [开发路线图](ROADMAP.md)。这些仓库文档不随 Skill 安装分发。

维护时先读总览，运行 `python3 -m unittest discover -s tests -v`。详情见 [使用指南](docs/usage.md)、[路线图](ROADMAP.md)、[架构决策](docs/decisions/architecture.md)。仓库尚未选择开源许可证；私库可先向协作者授权，公开分发前由仓库所有者明确许可条款。

扫描文件策略（0.4.2）：固定当前基线、草稿校验后发布、变化才备份、默认保留最近 3 份托管历史。详见使用与迭代指南。


## 业务项目文件如何提交（0.4.3）

Skill 仓库提交源码、测试和维护文档；不收录真实业务工作区。业务仓库选择提交当前有效基线、需求/任务/决策/追溯与可共享的交付结论，忽略本机指纹、当次检查选择、原始日志、扫描草稿和备份。

首次使用时 Agent 调用 `setup-workflow-git.py` 安装独立的 `.agent-workflow/.gitignore`。原始来源默认忽略，确认可共享后逐个放行；规格和摘录也需检查是否适合仓库权限。已有跟踪不会自动取消，既有项目规则不会被删除。新克隆项目保留已共享分析，复核后重建本机状态。详见 [Git 协作规则](skills/dev/core/references/git-sharing.md)。

PRD 可由文档、HTML 交互稿或两者组成；使用 `/dev prd <首个文件> --feature <ID> --source <附加文件>`。详细边界见 [使用指南](docs/usage.md)。

已交付功能出现效果不符时可用 `/dev fix FEAT-001 <问题描述>` 建立修复记录；可先保留原因待查；任务描述遗漏和代码缺陷可共同记录。修复需关联受影响需求/任务的回归测试，跨范围测试逐项说明覆盖原因，或明确记录豁免。0.4.6 支持非缺陷、经确认撤回和重复报告的有据关闭；关闭报告不等于修复验证。具体规则见 [修复流程](skills/dev/core/references/fix-workflow.md)。
