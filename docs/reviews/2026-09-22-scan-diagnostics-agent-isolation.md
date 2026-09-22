# GAP-05 扫描诊断 Agent 隔离复检

日期：2026-09-22。执行环境：本机 Claude Code、已安装 dev Skill 0.5.14、三个相互隔离的临时 Git 项目。复检只验证 `project.py verify` 及经人工判断后的 HEAD-only 刷新，没有读取或修改真实业务仓库。

## 结果

| 场景 | 初始结果 | Agent 处理 | 最终结果 |
|---|---|---|---|
| 未提交、未登记源码 `src/unregistered.py` | 退出码 3；`BASELINE_WORKTREE_REVIEW_REQUIRED`，精确列出路径 | 停在报告阶段，没有扫描或代替用户判断 | 工作区、基线和备份均未改变 |
| 已提交、与基线无关的 `README.md` | 退出码 3；原因仅为 `git_head`，精确列出 HEAD 路径 | 核对实际 diff、证据登记、指纹清单、覆盖说明和基线引用后，执行 prepare/publish | 仅刷新 fingerprint 的 `git_head`；基线正文 7 文件逐字节不变；备份 0→0；最终 verify 退出码 0 |
| HEAD 只增加 `.agent-workflow/shared-note.md` | 退出码 0；同时输出 `BASELINE_VALID` 和 `BASELINE_HEAD_ADVANCED_WORKFLOW_ONLY` | 无需扫描或人工刷新 | fingerprint、基线正文、备份和工作区均不变 |

第二个场景发布时输出 `BASELINE_FINGERPRINT_REFRESHED: baseline content unchanged; no backup created`。除 fingerprint 外的基线聚合 SHA-256 发布前后均为 `234945785ceff6f7138bc805a556c9a7b2e3ce2369fedd4d65e63e8cbed5fb3c`，fingerprint 的 `git_head` 从 `6ebfb6ad2986b3fbae7cb93e41b863a32186e9f9` 更新为 `af1d1fb6c0be046ee09c7bb0eb47054c558963ec`。

第三个场景中，当前 HEAD 为 `ca374e25016fab35df42c01a940a946080ceffc3`，fingerprint 仍保留业务基线 HEAD `6ebfb6ad2986b3fbae7cb93e41b863a32186e9f9`；这说明工作流自身提交没有被误写成业务基线更新。八个基线文件的 SHA-256 全部保持不变，没有生成草稿或备份。

## 结论与边界

0.5.14 的确定性机制和普通 Agent 编排均通过本次隔离复检：诊断信息足以把三个场景分开，Agent 没有在只读要求下擅自扫描，HEAD-only 局部确认没有产生冗余正文或备份，workflow-only 提交没有造成虚假失效。

本次仍是合成项目，不能证明 Agent 对真实代码变化的语义判断一定正确，也不能量化大型项目中核对 diff、依赖和模块档案的时间。GAP-05 的最小修正可视为完成；下一次真实 `/dev scan` 继续记录 Agent 阅读范围、用时、是否误选局部/全量复核以及实际遗漏。
