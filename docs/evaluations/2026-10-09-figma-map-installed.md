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
