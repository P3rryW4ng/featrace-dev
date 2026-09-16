# 使用与迭代指南

## 工作原理

1. 在目标项目执行 scan，脚本盘点清单，Agent 阅读实际代码补全技术基线。
2. 导入 PRD，保留原始字节，Agent 生成 JSON 需求、任务、决策和追溯关系。
3. 开发前结构校验。按小模块实现、运行适用检查、更新证据。
4. 后补 API/Figma 时，推断差异可细化；一手证据冲突需记录并请用户决策。
5. 根据实际构建/测试结果和资料适用性决定 provisional 或 complete。

通用核心不要求 UI、后端或某一种语言。API/Figma 状态分别为 present / missing / unknown / not_applicable。只有业务范围不需要时才能 not_applicable，并在 feature.source_notes 中记录理由。present 表示资料存在，不自动表示已完成对齐。

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
