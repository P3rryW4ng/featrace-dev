# 0.5.11 历史修复回归隔离演练

日期：2026-09-21。环境：本机 Claude Code、dev Skill 0.5.11、隔离临时 Git 项目。演练资料为合成支付示例，不含业务仓库代码或真实需求。模型版本未单独记录。

## 覆盖链路与结果

演练建立了历史需求 `DEMO-001`、已验证修复 `FIX-001` 和修改同一 `wallet` 模块及 `src/wallet/payment.py` 的新需求 `DEMO-002`。

以下确定性行为通过：

- 同模块和精确代码路径能发现跨需求 verified FIX；当前需求自己的 verified FIX 也可成为候选。
- 同步只生成 pending 候选时，develop 因缺少 disposition 被阻止。
- 选择 `retest` 并填写 planned checks 后，develop 不再因历史回归阻止；check 仍拒绝缺少当前结果。
- 实现可选 note 后实际运行 5 项标准库 unittest，包含原历史用例、相同 request ID、不同 note、单次 charge、原 receipt 和原 note 保留；另用临时 mutation 检查确认移除守卫或覆盖 note 会使测试失败。
- 当前结果绑定新的 review digest 和工作树身份后，结构 check 通过；未沿用旧历史 revision。
- 修改历史 FIX 描述后，check 先报告 review stale；重新同步后 candidate/review digest 改变，旧 disposition/result 不再有效，develop 回到 pending 阻断。
- 未提示历史回归、只要求普通 develop 时，Agent 会自动运行同步并发现候选；业务代码在前置阶段保持未改。

项目未配置 quality report，因此 delivery audit 失败；这不用于评价历史回归门禁。演练没有测真实项目的候选误报、漏报、跨模块依赖或耗时。

## 暴露的问题

1. 自动 develop 场景中，用户明确要求“需要判断时停止、不要替我做选择”，Agent 仍把新候选写成 `retest`，并将其解释为证据推导而非用户选择。`retest` 虽然是保守方向，但仍属于 disposition，违反本轮明确控制要求。确定性脚本无法识别聊天限制，运行规范需明确：只同步、只列出、停止或不代选时，新候选必须保持 pending。
2. 候选变化后 sync 会删除不匹配的旧 disposition 及 passed result。失效判断正确，但未提交工作区会失去上一轮证据文本，只能依赖 Git 或临时上下文。后续应在 canonical record 内保留 superseded history，同时确保历史项不能满足当前门禁。

## 结论与下一步

0.5.11 的候选发现、阶段门禁、当前证据绑定、失效和自动触发机制通过隔离演练；用户控制边界未通过，因此不能把 Agent 层行为记为完整验收。下一补丁优先修正“明确不代选时保持 pending”，再增加失效 disposition/result 的只读历史保存，并补确定性回归与一次短 Agent 复检。真实项目准确率继续待自然出现的跨需求修改验证。
