# 2026-11-04 架构接续评审与最小实施

对象：0.30.3合同6源码，基线e6126a7；用户授权按架构建议顺序推进。本轮未发布、未安装、不改业务任务。

## 评审结论

保留Agent语义判断、当前事实内核及项目工具的分工，不整体重构。入口绕过是软约束边界：内核只能约束通过自身的操作，不能保证Agent一定调用。新增一个查询命令或hook本身不能证明解决绕过；不因此引入第二套任务状态或跨宿主强制插件。

现有task_list提供分页ID/记录状态；view提供当前阻塞或已结项as-of回执；detail提供请求、计划、原事实、批准与选定检查诊断。check_diagnostic区分旧结果适用性与新执行许可。缺口是指引未把这些能力组织为按需入口，而非缺少事实存储。采用替换原恢复段落的局部指引修正：已知ID直接查；未知ID才list比对请求；歧义不能自动按最新/未完成选；读取必要分页；只对待执行检查按需诊断。当前规则与原授权仍须核对，查询不授权。

未采用：新增resume CLI（重复已有查询、仍不能代替语义选任务）；自动选最新任务（可能串任务）；每次全量恢复（重复读取）；新恢复文件（双份权威）；强制宿主hook（当前缺跨宿主能力及成本依据）。这不是永久否决：若真实样本证明多次查询造成显著遗漏/成本，再评估无新增状态的聚合视图。

## 顺序完成与暂缓边界

1. 修正PRODUCT阶段目标表达及module-guide的“第二阶段继续开放”漂移。第二阶段已通过，第三阶段稳定使用与持续提效。
2. 完成统一接续入口评审；复用现有命令，小修task-workflow恢复段；usage同步ENTRY节点说明，未改CLI/执行协议。
3. 核对程序查询保护并复用6项现有隔离用例；不重跑未改343项，不宣称自然Agent接续已通过。
4. task_workflow约1421行包含多个职责，是维护风险，不是本轮已证实运行缺陷。无功能修改驱动时不机械拆分；后续相关变更可先抽只读查询，必须保持状态/执行协议及旧事实语义不变，先核对真实耦合再做。
5. 容量/团队协作不新增开发。现有拒绝上限保留；不能以新任务ID或自动清理绕过失败。确有容量阻塞时再设计带未决交接的边界，不扩大本轮范围。

## 实际验证

PYTHONDONTWRITEBYTECODE=1，在tests目录运行现有unittest：

- TaskWorkflowTests.test_status_does_not_execute_or_write
- TaskWorkflowTests.test_list_is_paged_and_does_not_certify_recorded_state
- QueryDefaultTests.test_default_detail_recovers_ordinary_request_without_twenty_character_pages
- PolicyDiagnosticsTests.test_status_names_local_unknown_without_execution_or_write
- ExecutionDiagnosticTests.test_completed_task_diagnostic_is_not_permission_to_execute
- ExecutionDiagnosticTests.test_changed_environment_and_new_permission_are_separate

6项实际通过。首次调用前4项通过（该次0.761秒），后2项因维护者误写类名ExecutionDiagnosticsTests加载失败，并非被测程序失败；纠正为ExecutionDiagnosticTests后仅运行后2项，1.135秒通过。一次rg路径也因已在tests目录而写重复前缀失败，未影响源码。保留此次执行失误，不记为首次全绿。

反例与边界：已结项不授权执行、权限与旧结果分离、局部未知不隐去、分页不假装完整均有对应程序证据；多候选选对、记忆原话复用、恢复后实际进入内核属于Agent语义行为，未做独立Agent/自然压缩试验，不能用这6项代替。后续自然样本只观察：是否选对原任务、是否恢复原决定、是否无重复询问和无额外测试；无新任务不重开旧任务凑样本。

## 兼容与代价

仅维护文档和一份运行参考指引改变，15运行文件数量及合同6不变；正式CC仍0.30.3，候选尚未发布。无自动迁移、无用户数据删除、无新批准、无测试强制门禁。代价是恢复时必要的按需查询；未测净节省，不承诺自动防止Agent绕过。
