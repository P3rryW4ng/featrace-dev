# 0.5.37 安装版 Build Worker 全文差异隔离复检

日期：2026-09-30。安装器将源码 0.5.37 更新到本机 `/Users/mac/.claude/skills/dev`，原 0.5.36 保存在 `/Users/mac/.feature-delivery/backups/20260930T104036-claude-71c01745`。安装标记的 76 个运行文件逐一重算 SHA-256，零差异。使用旧 FEAT-001 合成夹具的干净拷贝、新的外部 attempt 和全新 Claude Code CLI 会话；本轮只派发 T-UP，不运行另一 Worker、集成或主项目采用。

首次启动因 Claude Code 本机登录过期而在读取任何项目证据前失败，原始输出单独留存。恢复既有账号登录后才启动新的会话；本页以下结果只属于后者。派发提示只给项目、attempt、T-UP、安装目录、专业 Skill 路径和副作用边界，没有写出 `inspect-diff` 命令或预期答案。运行环境关闭 hooks、Chrome 与 MCP，禁止提交、推送和主项目写入。

原生工具轨迹显示：先读取安装版 `featrace-build/SKILL.md`，调用 `preflight`（`PARALLEL_BUILD_INPUTS_CURRENT`），再调用 T-UP 的 `task-view`（`PARALLEL_BUILD_TASK_VIEW_CURRENT`）；之后才读取冻结 PRD、`upper.py` 及有关测试。Worker 单独写入 `upper.py`，等待写操作成功，再单独调用 `inspect-diff`，收到 `PARALLEL_BUILD_FULL_DIFF_EMITTED` 和完整 `full_diff`。该输出为 1,829 字节，未截断，包含 `upper.py` 的每个变更块；随后一条独立的 `finish --status ready` 调用返回 ready，分配的 `test_upper.py` **7/7** 通过。

维护者独立比对：`full_diff` 与 `returns/T-UP/patch.diff` 逐字相同，实际字节数与报告值相同，SHA-256 与返回记录相同。主项目 `git status` 干净，T-LOW 工作区干净；T-UP 的 `upper.py` 改动保留在隔离工作区。Worker 自述已阅读全文 diff，工具轨迹证明全文确实返回到其上下文、调用顺序正确，但**不能证明语义理解或所有产品行为正确**。本轮仅验证单 Worker 对 0.5.37 新入口的采用；没有重跑双 Worker 集成、候选采用、独立 Verify 或真实需求交付。旧 0.5.36 对照中并行更慢、更贵以及价格合同探针失败的结论不因本次复检而消失。

CLI 墙钟 77.054 秒，CLI 估计费用 $0.2731402；这些是合成单 Worker 数值，不与旧双 Worker 总成本直接比较。原始 CLI 流、提示、attempt 和执行摘要留在 `/private/tmp/featrace-0537-worker-lcyxmcmt/`，含本机运行细节，未入库。未改运行代码，未提交业务项目。
