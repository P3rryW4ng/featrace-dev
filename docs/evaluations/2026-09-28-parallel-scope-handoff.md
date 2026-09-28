# 0.5.26 并行 Build 的 Scope 接续复检

日期：2026-09-28。依据 0.5.25 Claude 演练的规则采用缺口，用户授权补强接续。源码 0.5.26；个人 Claude 安装仍 0.5.25；本轮未提交、推送或安装个人副本。CLI 2.1.283，实际模型 claude-opus-5-5，未指定或更换模型。

## 改动与结果

并行只替换 Build 执行方式，先采用原有 orchestration/workflow、影响、任务语义、历史回归规则及适用 profile。当前依据可以复用；缺项需要由获授权的总路由按原流程补齐。只读、禁止写记录或裁决时停在 Scope，不让 worker 补记录或转串行规避。prepare 在创建输出/工作区前要求 task-review.json 和 regression-review.json，并交既有 develop 校验核对；不新增另一套权威记录或 Scope 自报标记，不改变普通串行兼容。

- 目标回归 **23/23**，30.728 秒；完整回归 **267/267**，81.037 秒。新增检查覆盖兼容模式绿灯不能绕过缺失 review、任务语义过期及同步后未复核仍阻断。此前失败/越界/集成/版本变化检查仍执行。
- BLOCKED2：明确读取临时 0.5.26 的必要 Scope 规则，识别两份 canonical review 缺失；保留的 Markdown 视图不能代替 JSON。普通 develop 返回 FEATURE_VALID 与兼容警告，但路由停止，**零 prepare、零 Agent、零工作区**，没有写复核记录或转串行。
- READY2：当前 reviews 完整，但夹具缺 feature.title；加载普通 feature-selection 后停止，零派发。按授权仅在新 READY3 隔离夹具补标题、具体机制依据和保留行为，并重新核对来源，未放宽规则或重写旧失败。
- READY3：实际读必要 Scope 规则和 generic profile，复用当前 reviews，不运行 sync/review；prepare/preflight 各一次。**两个独立 native Agent** 使用同一 Build 专业说明，分别改各自函数；各自真实检查 1/1，第三候选集成 **2/2**，candidate_checks_passed。主项目未应用、共享记录未改、任务未完成，未进入最终 Verify/交付。

READY3 两个 Agent 调用属于同一 assistant message（流式记录分两块）。调用参数没有 run_in_background；执行方 assessment 的“background”说法没有参数证据，维护者只认定同一消息中的两次独立派发，不用它宣称某种后台调度能力。源码测试分别证明机制；工具轨迹证明指令被读取，不能证明理解永远正确。

## 原生入口与临时副本限制

初始 READY/BLOCKED 及一次只读发现复检使用 user,project 发现方式，仍选中了个人同名 dev 0.5.25，按版本要求停止，没有冒充新版通过。为不更改个人安装，后续 READY2/BLOCKED2/READY3 显式读取临时 0.5.26 Skill 后运行，其 native Agent 派发是真实的，但**新版原生 /dev 入口未验证**。安装新版后再核对发现/入口；此次没有修改个人配置或插件。MCP、Chrome 和当前进程 hooks 禁用，登录只用于已授权 CLI 运行。

## 维护者独立核对

BLOCKED2/READY2/READY3 的项目文件、忽略的来源和 canonical 记录、HEAD、索引及状态与执行前快照相同。个人安装全部 73 运行文件仍匹配 0.5.25 安装标记。READY3 允许的 Git worktree 注册是唯一主要仓库元数据变化；未提交。

维护者运行 preflight，回读两份实际补丁与 worker 状态、返回和日志 SHA-256，并用 candidate git write-tree 核对集成报告 tree（d52165715259258da3837731a70eac3849b7da96），不是只采信 Claude 总结。补丁分别只改 upper.py/lower.py，日志确实为 unittest 通过。保留行为部分依靠差异审查，集成检查不独立覆盖全部副作用。

见[核对统计与工具引用](evidence/2026-09-28-parallel-scope/measurements.json)、[缺项停止评估](evidence/2026-09-28-parallel-scope/BLOCKED2-assessment.md)、[标题缺项评估](evidence/2026-09-28-parallel-scope/READY2-assessment.md)、[正常候选评估](evidence/2026-09-28-parallel-scope/READY3-assessment.md)、[真实集成报告](evidence/2026-09-28-parallel-scope/READY3/integration-report.json)、[完整回归输出](evidence/2026-09-28-parallel-scope/full-tests.txt)。评估为执行方原文，解释冲突以此维护者结论为准。仓库不保存原始完整流、个人配置、登录资料或业务工作区。

## 时间与成本

| 场景 | 墙钟秒 | CLI 标价估计美元 | 结果 |
|---|---:|---:|---|
| READY 初始入口 | 49.837 | 0.292680 | 选中旧版，停止 |
| BLOCKED 初始入口 | 53.361 | 0.277465 | 选中旧版，停止 |
| 只读临时副本发现 | 见统计中的 duration_ms | 0.169722 | 仍选中个人旧版 |
| READY2 | 107.436 | 0.631105 | 标题缺项停止 |
| BLOCKED2 | 88.492 | 0.523197 | Scope review 缺项停止 |
| READY3 | 168.993 | 1.299776 | 两 worker + 外部候选检查通过 |

合计标价估计 **3.193944 美元**，保留发现失败与夹具修正成本，非账户实际结算。READY3 worker 的宿主统计约 33.2/33.9 秒与 32.5k/33.6k token 是局部口径，不能当成整轮成本。无同阶段串行对照，不宣称提速或减少真实遗漏。

## 剩余边界

这是合成小函数、预先具备 Scope 的采用复检，不是从 PRD 开始建立所有资料的真实案例。BLOCKED2 夹具还有标题/具体影响依据缺口；它证明针对缺 review 的停止，不证明唯一阻塞已定位；确定性测试单独隔离了该条件。无模块目录，不覆盖真实模块档案调查。

quick_validate 已尝试，因缺少 PyYAML 失败，不记为通过；基本 frontmatter、相对资源/文档引用和差异空白另行核对。权限主要为指令及事后检查，工作区不是安全沙箱。下一步在用户授权后提交/安装，再补新版原生入口确认；保持默认串行和可选两任务，不扩大通用调度。真实收益需自然需求对照。
