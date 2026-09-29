# 已安装 0.5.26 的原生并行 Build 隔离演练

日期：2026-09-29。用户授权在无新需求时，从原生 `/dev develop FEAT-001 --parallel` 验证缺项停止与正常两任务链。源码及个人安装均 0.5.26，运行前后 73 个文件与源码/安装标记 SHA-256 相等。实现提交 c794152，当前维护提交 197de18。未更换模型，CLI 实际模型 claude-opus-5-5；未改运行 Skill、安装副本、个人配置或真实项目，本轮不提交推送。

## 指定结果

| 路径 | 真实行为 | 结论 |
|---|---|---|
| BLOCKED 缺两份 canonical review | 原生 dev 已发现；普通 develop 兼容警告 + FEATURE_VALID，但路由停在 Scope；零 prepare/Agent/工作区 | 缺项停止通过 |
| READY 前置齐全 | 原生 dev 已发现；加载必要 Scope 和适用 profile；复用当前依据，prepare/preflight 后两 native Agent 各自执行，第三候选真实集成 4/4 | 正常候选链通过 |

两个全新 Claude CLI 会话启用 user 来源、仅在进程中禁用 hooks/MCP/Chrome，使用个人安装副本，项目内没有另装同名 Skill。启动清单均发现 dev，实际读取个人安装 marker/规则；不是上一轮手动指定临时 Skill 的替代读法。CLI 未显式指定模型。权限是指令约束和 helper 事后检查，不是安全沙箱。

夹具从上一轮正确但尚未实现的纯函数基点建立新 Git 副本：upper/lower 都原样返回输入；确认需求是各自转换大小写。需求标题、具体影响依据、保留行为、来源和 task review 均已在 READY 齐备。BLOCKED 只移除两份 review JSON 及其强制标记以测兼容边界，保留 Markdown 视图；标题和具体影响没有额外缺口。两份还预先新增组合、空输入集成断言，执行过程中任何 Agent 均不得改测试。

## 规则采用边界

READY 工具轨迹确认读取 orchestration、workflow、impact-review、task-semantic-review、historical-regression、parallel-build 及适用 profile；实际内容是否理解正确仍由返回和代码证据核对。没有模块目录，该夹具不覆盖真实模块档案调查。

BLOCKED 完整读 orchestration/parallel-build，并定向检索任务语义/历史规则，在确认缺 canonical review 后提前停止；没有完整加载全部 Scope references 或 profile。它验证安全停止和未接受生成视图，不算“所有 Scope 规则已完整读取”的证据；正常路径的读取证据另行成立。没有把缺项警告当成开发许可，也没有代写记录、请求 worker 补齐或改成串行绕过。

## 返回与维护者核对

两个 READY Agent 的实际调用、preflight 和返回顺序保留在工具轨迹中。它们使用同一 featrace-build 专业说明，各在独立工作区只修改 upper.py 或 lower.py；各自原有单测 1/1 通过，两个返回 ready。总路由等待两者停止、回读补丁/日志，才运行 integrate；候选集成 4/4（大小写、组合、空字符串），status=candidate_checks_passed。

维护者另行运行已安装 preflight，核对返回摘要、实际 worker 状态、路径归属、补丁与日志 SHA-256，并比较 candidate git write-tree 与报告相等。原项目业务文件、忽略来源和 canonical JSON、HEAD、原始索引 SHA-256、Git 状态均与运行前快照一致。BLOCKED 无 worktree 注册；READY 只有授权的两 worker/第三候选注册。个人安装 73 文件及源码 HEAD/status 在写本轮维护文档前也未变。外部工作区与失败/停止现场保留，未清理。

候选通过不是已交付：没有将补丁应用到主项目，没有 task done、最终 Verify/check/audit 或自动提交。后续主项目应用和共享记录更新仍须走普通授权 Build/Verify。

## Worker 顺序观察（待补强，不隐去）

两份 Worker 轨迹均显示 Edit 与 finish 在同一 assistant message 中提交，不能据此认定已等待编辑结果才发起检查。实际 helper 返回、补丁、工作树状态和真实单测绑定一致，本次未发生假绿或证据错配；也没有证据证明底层一定并发执行这两个工具。这个观察支持明确“编辑成功返回后，才单独调用 finish”的轻量顺序提示，而不支持把现有原型升级为通用调度。已登记为下一评审项，本轮未改运行规则。

## 成本与限制

| 路径 | 整轮墙钟秒 | CLI 标价估计美元 |
|---|---:|---:|
| BLOCKED | 72.885 | 0.424619 |
| READY | 183.233 | 1.340625 |

合计 1.765243 美元是 CLI 标价估计，非账户结算。该成本包含路由读取和维护者要求的评估输出，不是 worker 局部时间。无串行对照，不能说明真实提速或减少遗漏。原生入口/前置/两任务机制指定目标已通过，可在自然、明确独立的真实需求中小范围试用并测总成本；默认串行，不据此扩大拆分、任务数或通用调度。

本轮没有运行实现改动，因此未重跑此前 267 项完整回归、不升版本；本次真正执行的是夹具 worker 两项单测和候选四项集成。仓库只保存脱离个人配置的合成评估、统计、补丁/日志及校验摘要，不保存完整会话流、登录资料或项目 .agent-workflow。

证据：[缺项评估](evidence/2026-09-29-claude-0526-native-build/BLOCKED-assessment.md)、[正常评估](evidence/2026-09-29-claude-0526-native-build/READY-assessment.md)、[独立核对统计](evidence/2026-09-29-claude-0526-native-build/READY-measurements.json)、[worker 轨迹](evidence/2026-09-29-claude-0526-native-build/READY-worker-timeline.json)、[集成报告](evidence/2026-09-29-claude-0526-native-build/READY/integration-report.json)。评估为执行方原文，不覆盖维护者证据和限制。
