# 0.5.13 任务语义复核隔离演练

日期：2026-09-22。环境：本机 Claude Code、已安装 dev Skill 0.5.13、独立临时 Git 项目。演练只使用合成的 uppercase 文本转换需求，不含业务仓库代码或真实需求资料。

基线包含一个已确认需求 R-1、一个任务 T-1 和一次已完成的任务语义复核。R-1 要求把输入转换为 uppercase，验收条件为 `abc` 变成 `ABC`。develop 在基线返回 `FEATURE_VALID`；项目故意不建立 impact 和历史回归记录，因此这两项始终只报告既有 warning，不作为本次结论。

| 步骤 | 操作 | 结果 |
|---|---|---|
| 进度字段 | 仅把 T-1 状态从 planned 改为 in_progress，再同步并运行 develop | `changed=none`，摘要不变，`TASK_SEMANTICS: current`，history=0，develop 通过；task-review 文件未重写 |
| 冲突语义 | 仅把任务标题从 uppercase 改成 lowercase，不执行 review | `changed=T-1`，current/reviewed 摘要分叉，状态 pending；develop 返回 1 并报告 `task semantics need review: T-1` |
| 局部复核 | 将标题改为仍符合需求的 `Convert supplied text to uppercase`，只核对 T-1、R-1 和 PRD 第 1 行后登记 review | current/reviewed 摘要一致，history=1，develop 恢复通过；历史保存原 uppercase 基线，未保存未经批准的 lowercase 中间态 |
| 防篡改 | 只给 history[0].review.notes 追加文字，不重算摘要 | develop 与 sync 均返回 1 并拒绝 `invalid or duplicate task review history`；sync 未覆盖损坏记录 |
| 恢复 | 从项目外备份恢复 task-review.json | SHA-256 与备份完全一致，状态恢复 current/history=1，develop 再次通过 |

演练期间没有业务代码、需求或 PRD 改动，没有提交临时项目。最终工作树只保留预期的 tasks.json 与 task-review.json/.md 三个记录变化。Claude Code 能按指令区分进度和任务含义、在冲突处停止、只读取局部证据，并说明脚本成功只代表复核已登记，不代表自然语言自动正确。

本次证明 0.5.13 的确定性链路和一个普通 Agent 场景符合预期。它不证明所有模型都会正确识别业务冲突，也没有测量真实需求中的额外耗时、误阻塞或多任务/跨需求复杂度；这些仍需随下一真实需求采集。
