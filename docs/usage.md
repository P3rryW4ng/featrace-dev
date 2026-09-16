# 使用与迭代指南

## 工作原理

1. 在目标项目执行 scan，脚本盘点清单，Agent 阅读实际代码补全技术基线。
2. 导入 PRD，保留原始字节，Agent 生成 JSON 需求、任务、决策和追溯关系。
3. 开发前结构校验。按小模块实现、运行适用检查、更新证据。
4. 后补 API/Figma 时，推断差异可细化；一手证据冲突需记录并请用户决策。
5. 根据实际构建/测试结果和资料适用性决定 provisional 或 complete。

通用核心不要求 UI、后端或某一种语言。API/Figma 状态分别为 present / missing / unknown / not_applicable。只有业务范围不需要时才能 not_applicable，并在 feature.source_notes 中记录理由。present 表示资料存在，不自动表示已完成对齐。

## 日常工作流

适用版本：0.3.0；最后核对：2026-09-16。下图描述当前 Agent 工作流程；结构校验由脚本辅助，资料理解、冲突判断和最终完成条件仍需 Agent 结合证据核对。

```mermaid
flowchart TD
    A["在目标业务项目启动 Agent"] --> B["scan：校验项目基线与当前代码变化"]
    B --> C{"基线缺失或过期？"}
    C -->|是| D["盘点项目，选择 Android 或 Generic<br/>阅读代码，更新规范、示例和质量命令"]
    C -->|否| E["prd：保留原始需求资料"]
    D --> E
    E --> F["拆解原子需求、任务和验收条件<br/>更新 JSON 规格、决策、追溯与测试计划"]
    F --> G["判断 API / Figma 适用性<br/>不需要：记录理由；需要但缺失：记录假设"]
    G --> H["执行 draft 校验并修正规格"]
    H --> I{"存在一手来源冲突<br/>或未决决策？"}
    I -->|是| J["记录冲突、影响与选项<br/>等待用户决策"]
    J --> K["保存已确认决策<br/>修订 JSON 规格与受影响任务"]
    K --> H
    I -->|否| L{"develop 校验通过？"}
    L -->|否| F
    L -->|是| M["develop：按小模块实现与自测<br/>更新任务、追溯和证据，生成 Markdown"]
    M --> N["check：校验记录<br/>执行项目适用的构建与测试"]
    N --> O{"检查结果？"}
    O -->|失败| P["修复问题或补齐记录"]
    P --> M
    O -->|未配置或环境不可用| Q["provisional：记录缺口与下一步<br/>不宣称完整交付"]
    O -->|通过| R{"完成条件全部满足？"}
    R -->|否| Q
    R -->|是| S["complete：生成交付报告<br/>记录本次验证证据"]
    Q -->|补齐环境或检查配置| N
    T["任意阶段：新 PRD / API / Figma<br/>或需求修订到来"] --> U["保留新版本来源，逐项对齐<br/>分析受影响需求、代码和测试"]
    U --> V{"一手来源互相矛盾？"}
    V -->|是| J
    V -->|否：补全或细化推断| F
    Q -.->|等待资料补充| T
    S -.->|后续需求变更| T
```

读图时注意：

- **API、Figma 不是必经依赖**：功能不需要时记为 `not_applicable` 并说明理由；需要但尚未提供时允许有据可查的暂定实现，不允许宣称完整交付。
- **新证据随时可进入**：已有功能直接读取其记录并走“保留新版本 → 对齐 → 更新规格”分支，不重复初始化。来源版本与影响分析目前由 Agent 执行，尚未实现自动来源变更检测。
- **冲突先决策**：当前 develop 校验会在任一需求 blocked 时阻断整个功能的编码；可以继续无关分析和文档工作，但不能把任务级自动隔离当作已实现能力。
- **通过校验不等于 complete**：还需核对有效需求已确认、任务完成、无未决冲突、必要资料已对齐或合理不适用、追溯与测试证据齐全、适用质量检查实际通过。未满足时保持 provisional，并列出待办。
- **恢复进度用 status**：Claude 输入 `/dev status FEAT-001`，Codex 输入 `$dev status FEAT-001`，先读取已有状态，再决定开发、补资料或检查；无需重走所有步骤。

### 流程图维护约定

本节是日常流程的统一可读入口，与 `skills/dev/SKILL.md`、脚本实现及 `MAINTAINER.md` 中的实际限制保持一致。修改命令、状态、资料适用性、冲突处理或质量门禁时，在同一次改动中同步检查并更新本图、说明和核对日期；未实现能力只写入 ROADMAP，不画成现有自动流程。这里的“同步更新”是维护约定，并非自动生成机制。

## 项目质量配置

scan 会生成 `.agent-workflow/project-baseline/quality-gates.json`，初始 gates 为空。Agent 根据项目 CI/构建文件填入命令，不凭语言猜测命令。示例：

```json
{"gates":[{"name":"unit","command":["python3","-m","unittest","discover"],"cwd":".","timeout_seconds":600}]}
```

每个列出的 gate 都必须通过。命令参数数组避免 shell 拼接；这些命令仍会执行项目代码，需在执行前核对。脚本生成 quality-report.json，Agent 将本次结果及限制写入功能 delivery-report.md。未配置、缺运行环境或测试失败不算通过。

## 兼容和迁移

- JSON 项目继续使用原路径；新增 source_notes 与 not_applicable 不要求批量改写旧数据。
- 旧 missing/unknown 必须逐项判断适用性，不能机械替换为 not_applicable。
- 新 scan 使用新版清单指纹；旧指纹验证会过期，重新扫描并审查基线说明。
- migrate-workspace.py 仅创建 migration_required 脚手架；保留旧 YAML，不自动理解转换。遇到任何已有 JSON 目标都拒绝写入。迁移时由 Agent 逐条重建并核对来源与决策，再清除 migration_required、验证及渲染。
- render-workspace.py 会覆盖生成 Markdown。旧手写 Markdown 先保存在迁移备份中，不能丢弃其中未结构化的决策。

## 安装分发

当前选择“克隆 + 一个 Python 安装命令”：不依赖远程安装服务，也不需要维护两份 Skill。安装器把同一个 skills/dev 完整复制到个人发现目录。更新需 git pull 后再次运行 --update；不是自动同步。

仓库地址：[P3rryW4ng/feature-delivery-skill](https://github.com/P3rryW4ng/feature-delivery-skill)。代码提交到远端后，给使用者发送仓库 README 即可。Codex 用户也可请求内置 skill-installer 安装仓库中的 skills/dev（访问私库须授权）；本仓库测试覆盖的是本地安装脚本。

## 维护交接

对其他 Agent 说：

> 继续维护 feature-delivery-skill。先读 MAINTAINER.md、ROADMAP.md、CHANGELOG.md、docs/decisions/architecture.md 和 skills/dev/SKILL.md。运行已有测试，核对实现与文档；只实施当前明确授权的下一项，不改变既定原则。完成后更新变更记录、版本和交接状态，报告实际验证及限制。

Git 管理本体；项目 .agent-workflow/ 另行管理。聊天分享链接只是背景，不能替代可运行代码和交接文档。
