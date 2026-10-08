# 验证与评估索引

更新：2026-10-08。本页只提供当前证据导航与结论边界。历次执行的完整记录保留在[验证历史](history/2026-09-30-validation.md)；其中版本、安装和“下一步”只代表当时。当前任务见 [ROADMAP](../ROADMAP.md)。

## 当前发布与检查

当前源码和本机 Claude 安装均为 0.5.37；安装版 76 个运行文件与标记哈希相符。[单 Worker 隔离复检](evaluations/2026-09-30-build-installed-full-diff.md)观察到 Agent 实际按顺序读取任务视图、输出完整补丁并交回 ready；旧[双 Worker 对照](evaluations/2026-09-30-build-installed-ab.md)保留。0.5.37 的 `test_parallel_build` 29/29、完整 unittest 277/277 于 2026-09-30 实跑通过（84.957 秒，退出码 0）。测试不证明 Agent 理解、行为覆盖或产品成熟度。Skill Creator `quick_validate.py` 因 PyYAML 不可用未成功运行；三个 Skill frontmatter 的 Ruby YAML 解析、`py_compile` 与 `git diff --check` 通过。

## 能力证据导航

| 能力 | 证据 | 能证明／不能证明 |
|---|---|---|
| 基础真实交付 | [CASE-01](reviews/2026-09-18-case-01.md)、[CASE-02](reviews/2026-09-21-case-02.md) | 已取得最终交付及多来源案例；新版模块/影响机制没有在所有案例完整采用 |
| PRD 表达差异 | [样例评估](evaluations/2026-09-18-prd-styles.md) | 8/8 样例语义通过；单模型样例不证明所有 PRD 无遗漏 |
| 独立 Verify | [Claude 0.5.24](evaluations/2026-09-28-claude-0524-verify.md)、[0.5.37 同输入对照](evaluations/2026-10-08-verify-same-input.md) | 合成缺陷/正确例两路均判对；独立路由未增加有效发现，总墙钟 +50.4%、CLI 估费 +63.9%，另有一条轻微依据不足判断；真实准确率与净收益仍待测，保持可选 |
| 内部选择串行／两 Worker | [原生策略演练](evaluations/2026-09-29-native-auto-build.md) | 有实际选择与候选检查；不支持任意宽度调度或证明提速 |
| Build 任务级输入视图 | [0.5.36 源仓测量](evaluations/2026-09-30-build-task-view.md)、[安装版同输入对照](evaluations/2026-09-30-build-installed-ab.md)，完整回归 272/272 | 安装版两个 Worker 均按顺序调用预检和任务视图；本次并行更慢更贵，候选被独立合同探针检出缺陷；不证明真实上下文节省或提效 |
| Worker 全文补丁检查 | [0.5.37 源仓验证](evaluations/2026-09-30-build-full-diff.md)、[安装版单 Worker 复检](evaluations/2026-09-30-build-installed-full-diff.md)，完整回归 277/277 | 实际 Agent 单独调用并收到完整补丁后才 `finish`，补丁与返回逐字一致；未验证语义判断或双 Worker 集成 |
| Build 失败边界 | [边界验证](evaluations/2026-09-29-build-boundaries.md)、[失败返回](evaluations/2026-09-29-gap20-return-gate.md) | 来源漂移/越界/失败返回停止；并非新版所有分支都重跑完整派发 |
| 候选采用与普通 Verify | [接续演练](evaluations/2026-09-29-adoption.md) | 采用前阻断、漂移拒绝与技术证据回填；不冒充产品/真机验收 |
| 修复→重测→交付 | [Repair 演练](evaluations/2026-09-29-repair.md) | 修复/重测已执行；早期报告曾需提醒，后由 Deliver 规则补强 |
| PRD 到交付 | [完整链复检](evaluations/2026-09-29-gap22.md) | 合成项目能执行到报告与完成；无真实时间收益对照 |
| 报告失败留痕 | [0.5.33 复检](evaluations/2026-09-29-gap22-report-blocker.md) | 读取失败后保存阻塞；StoreFlow 两轮首次收口均先单独全文回读，真实稳定性仍待观察 |
| 中途变更跨会话 | [0.5.33 接续](evaluations/2026-09-29-cross-session-revision.md) | 同机新会话重开任务、旧证据失效及重新交付；两轮临时范围偏差保留 |
| 临时写入范围 | [0.5.34 复检](evaluations/2026-09-30-write-scope.md) | 提案/故障副本在项目内、拒绝时停止；不是宿主文件系统沙箱 |
| 跨会话综合交付 | [StoreFlow 演练](evaluations/2026-09-30-storeflow.md) | 合成 v1→v2→人为回归修复三会话通过独立契约；原报告文字滞后，后续修正见 GAP-23 |
| GAP-23 报告结论收口 | [0.5.35 原生复核](evaluations/2026-09-30-gap23.md) | 原生会话修正了旧待办措辞，单独全文回读后登记哈希再更新状态；真实项目稳定性仍待测 |
| GAP-06 流程成本 | [轻量测量口径与 StoreFlow 样本](evaluations/gap06-cost-measurement.md) | 三轮合成执行的总时间、CLI 费用估计和调用次数可核；记录分钟数、维护者工时及真实净收益未测量 |
| GAP-18/19 模块图候选与条件边 | [0.5.35 安装版 Agent 正反例](evaluations/2026-09-30-gap18-19-installed.md) | 小型合成 Gradle 仓库中未知目标、条件边均保留；错误无条件目录边被硬拒绝并由 Agent 修正。未运行 Gradle，真实复杂项目采用待测 |

## 本轮综合演练

[协议](evaluations/2026-09-30-storeflow-protocol.md)在结果前固定；[结果](evaluations/2026-09-30-storeflow.md)已归档。三轮原生 Claude Code 合成演练分别完成部分开发、获批修订后交付、故意注入回归后的修复。最终项目 32/32、独立契约 18/18；0.5.34 安装版未改。第三轮 0.5.34 报告结论仍写已完成步骤为待办，作为原始失败保留；0.5.35 的后续[最小修正复核](evaluations/2026-09-30-gap23.md)不能改写该旧结果。此案例不代表自然业务需求。

## 统一评价口径

记录被测源码/安装版本、输入与代码身份、工具轨迹、实际命令/返回、发现与误判、必要/非必要介入、总耗时、Token或费用（可取得时）、维护者额外成本。测试覆盖看断言与行为，不看数量。人工目视、Agent 技术调查、自动化测试分别注明。

跨机恢复、真实准确率、实际节省时间与记录成本仍未充分测量。失败、旧结果、过期和未批准中间态保留，不能用后一次通过改写前一次失败。按需阅读相关案例，不全量加载历史。
