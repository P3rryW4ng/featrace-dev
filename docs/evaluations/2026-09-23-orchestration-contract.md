# 0.5.17 阶段路由契约复核（2026-09-23）

## 范围与方法

在 Skill 源码工作树中，把 0.5.16 主 `SKILL.md` 的入口与关键约束逐项对照 0.5.17 主入口、`orchestration.md` 和按需参考文件；再用合成输入做路由与停止条件的静态走查。没有调用另一个 Agent、新开 Claude 会话或修改真实业务仓库，因此本报告不能声称独立上下文或真实 Agent 路由准确率。旧命令的脚本/门禁兼容由仓库现有 211 项合成回归覆盖；本次额外复核的是指令是否仍可从入口到达。

## 旧规则可达性

| 0.5.16 主入口规则 | 0.5.17 读取链 | 结果 |
|---|---|---|
| help 不进入项目、不写文件 | `SKILL.md → command-help.md` | 保留 |
| 会话模式与 off | `SKILL.md → session-mode.md` | 保留 |
| 新会话不猜 ID、创建需用户产品编号 | `SKILL.md → feature-selection.md → prd-analysis.md` | 保留 |
| next 依证据用途区分设计、Bug、疑问和修订 | `SKILL.md → next-workflow.md → orchestration.md` | 保留 |
| PRD 多来源、读取缺口、语义复核与原文不覆盖 | `prd-analysis.md → workflow.md` | 保留 |
| 来源登记同时更新 intake 与 `prd_paths` | `prd-analysis.md` | 补明 API 与 Figma 均需本地证据或精确访问缺口 |
| scan 配置、目标 profile、全局/模块范围 | `project-baseline.md → module-context.md` | 补明 scan 前配置、混合项目目标与克隆复用 |
| module scope、影响清单、任务语义与历史 FIX | `orchestration.md/Scope → module-context.md、impact-review.md、task-semantic-review.md、historical-regression.md` | 保留 |
| 历史候选只发现；用户限制时保持 pending | `SKILL.md → historical-regression.md` | 保留 |
| 修复先登记、原因未知可调查、回归或豁免 | `orchestration.md/Repair → fix-workflow.md` | 保留 |
| check 选择适用门禁、执行结果与人工项分开 | `orchestration.md/Verify → verification-workflow.md → project-baseline.md` | 补明质量选择规则必读 |
| 归档预检、报告草稿审阅、旧标签兼容与恢复 | `SKILL.md → feature-archive.md` | 补明旧 classify 与 restore 不需新验收 |
| 来源适用性、旧 YAML 迁移和最终完成条件 | `workflow.md → verification-workflow.md` | 保留 |

复核中修正的三类遗漏：Verify 需明确加载质量选择规则；旧 `classify` 标签需加载归档兼容规则；`restore` 不得受 Deliver 的新验收前提误阻。另将 scan 配置与混合项目约束、API/Figma 本地来源登记明确写入对应阶段参考文件。

## 合成场景走查

| 输入与前置状态 | 应进入的阶段与参考 | 必须停下或继续的边界 | 静态结果 |
|---|---|---|---|
| 新 PRD，未给产品 ID | Requirement；feature-selection、prd-analysis | 初始化前询问 ID，不自编编号 | 契约可达 |
| 新 PRD 含无法读取的交互 | Requirement；prd-analysis | 保存读取缺口和 draft 局部复核，不能进入 Build | 契约可达 |
| 当前需求补充预期设计图 | Requirement/figma；next、prd-analysis | 保存可访问证据并复核；未授权开发不自动改代码 | 契约可达 |
| 当前页面返回失效的实际截图 | Repair/fix；next、fix-workflow | 先登记实际观察，原因保持未知，修复前核对影响与历史回归 | 契约可达 |
| 确认修改旧需求的行为 | Requirement/revise → Scope；revision、prd-analysis、impact | 版本及批准依据有效后应用；重新复核并核对受影响范围 | 契约可达 |
| “继续开发”，有 pending 历史 FIX 候选 | Scope；historical-regression、impact | develop 门禁拒绝未定性候选；只同步指令时保持 pending | 契约可达 |
| “现在还有什么问题？” | status；feature-selection、next | 只读，不触发 build、check 或 audit | 契约可达 |
| “开始验收”，自动测试通过但真机项未测 | Verify；verification、project-baseline | 报告未测人工项，保持 provisional，不进入完成交付 | 契约可达 |
| 已归档需求要求恢复 | lifecycle；feature-archive | 记录 restore，不为恢复重跑 check；后续修改重新守门 | 契约可达 |

这些结果证明入口指向了对应规则，**不证明 Agent 在自然语言场景下真的会选择正确路线**。真正的路由错误率、重复读取、交接遗漏、人工介入和耗时需用新上下文与下一真实需求记录；不能从文档走查或合成单测推算。

## 结论与待测项

静态契约复核通过，发现并修正上述可达性缺口。0.5.17 继续保持一个用户入口、同一 Agent、现有 JSON 权威与旧命令兼容。下节记录随后完成的独立新会话文字路由演练；真实需求仍需比较上下文和时间成本。未拿到这些业务运行证据前，不启动独立 Verify，也不宣称多 Skill 已解决幻觉或漂移。

## 独立 Claude Code 路由演练 — 2026-09-23

在 `/private/tmp` 建立临时插件，复制**未安装**的 0.5.17 `skills/dev` 候选版，以 Claude Code 2.1.280、Claude Opus 5.5 的独立新会话运行六个合成案例。插件通过 `claude plugin validate`；评估设为单次运行、无对照臂、无脚本脚手架、无报告发布，案例只允许 Read/Glob/Grep/Skill，不允许修改业务文件。个人安装版仍是 0.5.16，真实业务仓库未参与。每例只提供独立文字情境，不给完整项目记录；因此测试的是新会话路由与停止边界，**不是**开发、记录写入或测试闭环。

| 案例 | 实际观察 | 结果 |
|---|---|---|
| 新 PRD 缺产品 ID | 询问用户分配的编号，在创建前停止；未自编 ID | 符合 |
| 已完成需求询问“还有哪些问题” | 选择只读 status，不重跑 check/audit 或改记录 | 符合 |
| 只同步历史 FIX 候选且明确不代选 | 保持 pending，说明 develop 仍阻断；未选 retest/not_applicable | 符合 |
| 验收时报告实际返回失败 | 选择 Repair/fix，原因保持 unclassified；缺项目/需求 ID 时先确认归属，不臆造截图或改 PRD | 符合（评分标准修正后复跑） |
| 补充新的预期设计图 | 选择 Requirement/设计来源，不误判为 fix；缺图片字节时不声称读图 | 符合 |
| 恢复已归档需求 | 选择 restore 生命周期动作，不强制为恢复本身重跑交付检查 | 符合 |

首次六例自动评分为 **5/6**，故障截图例被三个评委判失败；人工阅读其完整回答发现，它实际按 Repair 路由、保留原因未知，并因案例没有项目/需求 ID 而没有伪称已写 FIX。原评分文字要求“保存观察为证据”，却未明确无归属时不得要求实际写入。将评分标准改成“先保留用户观察，取得归属后登记”后，以全新会话复跑该例得到 **1/1**。这是一处评估规则歧义，不能把首次 5/6 擦写成未经争议的 6/6；也没有据此修改 Skill 运行规则。复跑保留的工具轨迹确认 Agent 实际调用候选 `dev` Skill，读取了 `fix-workflow.md`、`next-workflow.md`、`feature-selection.md`，然后在缺上下文处停止。

独立演练总计七次运行（其中故障例两次），只覆盖文字路由与停止条件。单次运行和 LLM 评分不能估计真实误路由率；未测图片读取、已有记录变更、真实脚本门禁、PRD 到代码的连续推进、上下文占用或节省的时间。下一真实需求仍需记录这些数据；是否把 Verify 隔离成独立 Agent 继续由对比结果决定。
