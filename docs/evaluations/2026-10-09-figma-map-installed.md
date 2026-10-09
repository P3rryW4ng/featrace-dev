# 0.5.41–0.5.42 安装版 Figma 与项目地图隔离复核

日期：2026-10-09。该记录区分脚本实测、Claude Code Agent 采用以及真实业务项目地图；三者不能互相替代。

## Figma 索引

0.5.41 的源码合成回归与模块定位一起完成 292/292。安装后核对 `/Users/mac/.claude/skills/dev` 中 78 个运行文件、安装标记和当时 0.5.41 源码的 SHA-256 全部一致。在 `/private/tmp/featrace-design-isolation-rxp5ot9o` 构造一份两状态的 `DEMO-DESIGN` 资料，实际调用**安装目录**下的 `core/scripts/design_index.py`：

| 输入 | 实际结果 |
|---|---|
| 两个已读状态与 intake 节点一致，`validate --stage check` | 退出 0 |
| 原文件 `ABC123` 的既有节点 `1:3` | `exact_identity`；仍标 `content_review_required=true`，因为未提供新稿字节 |
| 复制到新文件 `NEW123` 的节点 `9:9` | `candidate_only`、`requires_confirmation=true`，返回两个同页候选，未擅选 |
| 在登记后修改设计证据文件字节 | check 退出 1，两个状态均报来源字节变化 |

随后尝试用 Claude Code `-p` 在该隔离目录里执行 Agent 级只读复核，API 在模型调用前返回 **401 OAuth access token has expired**，无模型 Token 消耗、无 Agent 工具调用。故**安装版脚本隔离检查通过，Agent 自然采用未验证**。未读取远端 Figma 页面、未测截图识别，也不能由来源摘要证明视觉内容不变。

## Android 项目首块地图

业务项目 `/Users/mac/StudioProjects/zymix-im-android-cloud` 在本次之前无 `.agent-workflow/modules/`。安装版静态 Gradle 发现生成 30 个候选、166 条候选边、21 个解析/外部目标缺口。对 `app`、`zymix-chat`、`zymix-wallet`、`zymix-uikit` 的 settings 与 build 声明逐行核对后，建立**部分正式目录**；其余模块继续是待审候选，不自动确认。图生成 46 个节点、173 条边；图上的虚线仍是候选，不是运行时调用图。

四个模块只有已核对的构建边界与文字摘要，**尚无行为档案**。`plan --module wallet` 把直接调用方 `app`、`chat` 和依赖 `uikit` 列入调查范围，四项都为 `unreviewed`；这不能放行需要当前档案的开发门禁。首轮 `locate` 输出了未复核范围的全部文件名，真实使用暴露可读性问题。0.5.42 将其收敛为范围文件数量，且把全局登记证据单列为 `project_evidence`；具体变更文件仍由 `plan` 按需提供。

此轮没有修改业务代码、没有运行 Android 构建或真机测试，也未声称四个模块的功能细节已被审完。业务仓库原有未跟踪 `acceptance/` 未碰。六个地图文件经路径/内容范围检查后以 `5f4027c01` 单独提交并推送到 Codeup 的 `feature/wallet-module` 分支；其他分支需合并后才能使用。真实多人交接、跨模块问题定位速度和遗漏率未测。

业务项目旧基线的 `project.py verify` 仍返回 `BASELINE_STALE`（manifests、evidence、git_head），涉及此前累积的项目变更，并非仅此地图提交。未为消除此状态而重扫、改写旧基线或运行 Android 构建；开始新功能前应按当前代码和登记证据审查并刷新基线。

## 登录恢复后的安装版 Claude Code Agent 隔离复检

2026-10-09 在 Claude Code 重新登录后，另建 `/private/tmp/featrace-agent-isolation-v3caj8m7/` 下的两份固定小夹具，使用本机安装的 **0.5.42** 和 `claude -p` 全新会话执行只读调查。此节是上述 401 失败之后的新证据，不改写旧失败。CLI 的可读目录显式增加安装版 Skill 路径，允许 Read/Bash；没有启用权限绕过。完整工具轨迹与结果保存在该临时目录的 `figma-agent-v3.jsonl`、`map-agent.jsonl`，临时文件可能被清理，不把它们算作仓库长期证据。

Figma 首次 Agent 尝试读到了 Skill 和参考说明，但在运行索引命令前达到预设的 10 轮上限（`error_max_turns`，估费约 $0.32）。第二次提高上限后，非交互权限配置仍阻止读取安装目录及执行脚本；Agent 如实表示三项均未实测（估费约 $0.30）。第三次明确允许安装目录和只读工具，Agent 读取设计索引契约并实际调用安装版脚本：`validate --stage check` 退出 0；原文件节点 `1:3` 配合不同字节来源得到 `exact_identity`、`content_review_required=true`、`evidence_bytes=different`；复制节点 `NEW123/9:9` 只得到两个 `candidate_only` 状态、`requires_confirmation=true`，未擅自选定。Agent 还通过阅读材料发现修订文件多了未登记的 `1:4`，没有把校验通过说成状态枚举完整。第三次 5 轮、CLI 估费约 $0.27；五个夹具文件的 SHA-256 前后相同。

模块地图 Agent 读取安装版说明并实际运行定位和计划。它先用错误的 shell 循环把整串参数当成一个参数，三次 argparse 均退出 2；随后分别重跑，`wallet/payment.py` 得到 `mapped`、档案 `unreviewed`，`outside/bug.py` 得到 `outside_map`，两次定位均退出 0；`plan --module wallet` 列出 wallet 与直接调用方 app、chat，三者档案均未复核，退出 2。Agent 将退出 2 正确解释为档案缺口而非可直接开发，并说明图只反映登记的静态关系，不证明完整运行时调用链。该会话 8 轮、CLI 估费约 $0.37；Git HEAD 与干净工作树前后未变。

**结论边界**：已观察到安装版 Agent 在定向隔离任务中读取相关指引、调用脚本、保留候选和未知区域，并识别资料新增状态；不能由此宣称它在普通真实需求中会自然触发、Figma 页面/状态无遗漏、共享地图已被同事复用，或这套流程节省了时间。两次失败及 Agent 的一次命令拼装错误也说明安装权限和 CLI 调用方式有实际成本。下一笔真实需求继续按 ROADMAP 采集自然采用、遗漏、误判和维护耗时。
