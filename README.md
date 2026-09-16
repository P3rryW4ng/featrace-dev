# Feature Delivery Skill

把 PRD 转换为可追溯的需求、开发任务和验证记录，支持后补 API / Figma、冲突决策和持续迭代。

当前版本 **0.3.0**：通用工作流 + Android 适配 + Generic 适配。iOS/Web/后端可用通用流程，但没有专属自动化适配器。此工具由 Agent 执行需求理解和编码，脚本负责部分确定性检查；不能保证零遗漏或零 bug。

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
| 扫描项目 | `/dev scan` | `$dev scan` |
| 拆解 PRD | `/dev prd /路径/需求.md --feature FEAT-001` | `$dev prd /路径/需求.md --feature FEAT-001` |
| 开发 | `/dev develop FEAT-001` | `$dev develop FEAT-001` |
| 查看进度 | `/dev status FEAT-001` | `$dev status FEAT-001` |
| 自测检查 | `/dev check FEAT-001` | `$dev check FEAT-001` |

补接口：`/dev api /路径/api.yaml --feature FEAT-001`；补设计：`/dev figma <链接或导出文件> --feature FEAT-001`。Codex 替换开头为 `$dev`。这些输入发给 Agent，不是在终端运行的命令。在线资料需要已有连接器或可读取的导出文件。

Claude Code 的 `/dev` 来自标准个人 Skill 目录；Codex 用 `$dev` 显式选择 Skill。参见 [Claude 官方说明](https://code.claude.com/docs/en/skills) 和 [Codex 官方说明](https://learn.chatgpt.com/docs/build-skills)。首次安装后打开新会话；若仍未出现，检查安装输出中的目录和工具配置。

## 更新和卸载

```bash
git pull --ff-only
python3 scripts/install.py --update
# 只卸载 Claude：
python3 scripts/install.py --agent claude --uninstall
```

更新/卸载会把本工具安装的旧副本移到 `~/.feature-delivery/backups/`，不永久删除。若目标是别人的同名 Skill、符号链接或已被本地修改，安装器拒绝覆盖。每个目标单独备份；安装多个目标不是跨目录事务，遇到系统错误可修复后重试。

## 从旧版迁移

旧 `android-feature-delivery` 本体与新 `dev` 分开。安装脚本不会移除旧 Skill，也不会修改个人 `CLAUDE.md`。如果此前添加了 `@~/.agents/skills/android-feature-delivery/SKILL.md`，启用新版前应从个人规则中移除那条旧导入，并把旧 Skill 备份到技能发现目录之外，避免两个版本同时引导工作。旧项目 JSON 可继续读取；旧 YAML 必须按 [使用指南](docs/usage.md) 重建和校验，不能当成已自动迁移。

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

先读 [MAINTAINER.md](MAINTAINER.md)，运行 `python3 -m unittest discover -s tests -v`。详情见 [使用指南](docs/usage.md)、[路线图](ROADMAP.md)、[架构决策](docs/decisions/architecture.md)。仓库尚未选择开源许可证；私库可先向协作者授权，公开分发前由仓库所有者明确许可条款。
