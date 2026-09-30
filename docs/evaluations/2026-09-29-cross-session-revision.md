# 中途PRD变更后的跨会话接续演练（2026-09-29）

## 结论

个人安装版0.5.33的两个独立原生Claude会话，在合成项目完成“部分开发 → 产品修订 → 新会话恢复 → 重开任务 → 重新验证 → 交付”。核心目标在本例通过：原始PRD未改，受控基线v1→v2，未修改R-2语义或收据行为，旧绿灯未充当v2证明，最终confirmed/verified均v2、feature complete。

严格副作用合规仅部分通过：第一轮在项目外临时复制代码做mutation检查后删除，第二轮曾将提案临时写到/tmp后删除，与只写项目及指定摘要的提示不完全一致。保留真实命令与Agent自述，不把“已删除”说成没有越界。没有更改真实业务、Skill安装或个人设置，不因本例扩大并发、专业拆分或宣称L2完成、效率提升。真实跨账号/跨机器未测。

本轮只有评估与维护文档更新；源码和个人安装保持0.5.33（已发布main b05b763）。没有运行实现修改、版本升级、安装、提交或推送。

## 预先固定的任务与中断点

原始PRD两条规则均明确批准，模块formatting，技术实现选择委托Agent。R-1：preview_label按Python Unicode字符截取前8，短/空字符串不变；receipt_id保留前12，不能复用改变后的预览上限。R-2：status_label去前后空白再str.upper，空白输入返回空。无第三方依赖、I/O或主观验收。

第一轮只授权完成R-1，R-2保留planned，不允许交付complete；显式授权受控基线采用、实际检查及隔离本地提交，不允许push。这是人为指定的部分里程碑，不模拟随机崩溃或未保存中断。

第一轮结束后，保存原现场快照；才把此前物理隔离的v2修订和第二轮提示加入可用目录。v2明确只将8改6，长度7必须从“不截断”变为“截断”，R-2及收据不变。第二轮只收到路径、批准修订与继续授权，没有第一轮摘要或对话、预期验收用例、工具调用指导。使用当前个人安装dev，实际Skill调用都是next --feature RESUME-001；新CLI进程、不resume、不同会话标识，串行且零Agent工具派发。不测试另一账号、另一机器或不同模型。

## 实际路径及证据

| 检查点 | 实际结果 |
|---|---|
| 第一轮部分完成 | 基线v1；T-1 done/T-2 planned，provisional，13项项目测试通过。R-2四条未测，所以当时整体check/audit并未通过，不冒称旧需求已经交付 |
| 新会话恢复 | 从现有需求、任务、旧源码/测试、修订规则恢复；添加批准决策D-001，用CHG-001 propose/apply推进v2，分类requirement_change，没有将新要求记作旧版代码bug |
| 旧证据失效 | apply返回后、下一次新检查前的只读观察：确认版本2、quality仍绑定1，旧测试时间10:25:33Z。validate/check、audit、verification status均exit1；audit明确not bound to current requirement baseline及verification stale。该观察不把结果通知Agent，也不更改记录，区别于Agent自身实际调用证据 |
| 任务及来源同步 | 实际更新T-1语义并复核、保持T-2语义，原始intake的5个aspect按CHG-001标为superseded；应用提案成为当前证据。旧PRD和v1语义快照保留，不按“文件较新”静默覆盖原意 |
| 新版开发与检查 | 先红：20测试10失败；改代码后20/20绿，limit6、receipt12、status strip+upper。旧质检不能绑定新版本，重新执行后quality版本2、时间10:31:11Z |
| 历史保留 | 11份先前passed尝试都仍存在于active/retired历史，7条旧验收项retired，旧测试时间和digest保留；旧质量报告另在父会话现场快照保存，不假称当前quality-report同时保存全部历史 |
| Deliver | Write38返回event76 → Read39 event77/返回78（66行全文逐字匹配）→登记v2交付40→状态41；没有同批写读，报告hash与版本交付记录一致，最终complete |

最终16条验收通过：11需求/行为自动行、1自动门禁行、4Agent技术检查行；后者不是用户目视或设备验收。测试revision为40ace5f…，后续仅工作流记录提交不重标旧测试HEAD。

父会话另执行未提供给Agent的7条当前产品契约：第一轮代码5失败、第二轮7/7通过，证明验收区分新旧上限及剩余任务。再次运行最终项目20项、validate/check、audit、revise status均通过；确认baseline2、verified2、无pending。receipt函数AST及两条原有receipt测试字节不变，R-2语义字段不变、原始PRD哈希不变，源码Skill和个人安装均不变。

## 摩擦、成本与未验证范围

第一轮311.296秒，CLI估计$1.789136；第二轮335.153秒，$1.8913976。CLI合计$3.6805336，不含父会话验证、维护文档和准备成本，不是自然开发时间改善指标。没有追加阶段指令或产品回答；预先明确批准和暂停点属于实验条件，不等于零人类设计成本。

Agent曾漏填task review参数，验证先被过期模块档案阻断，又遇到临时输出路径错误；自行纠正后继续，没有隐去这些失败。第一轮mutation的输出管道不是父会话完整返回码证明，不用它宣称绝对覆盖；独立契约的真实结果另列。

项目外临时写入范围偏差保留：本次不是严格沙箱保证；不代表可在生产允许任何临时路径写入。来源和quality默认被gitignore，本例接续发生在同一本机目录，资料仍可读取；不能据此承诺clone、换机器就能恢复同样完整证据。没有新账号登录、会话压缩、多Agent竞争、不可写报告或无通知竞态。部分纯函数no-I/O由Agent查看及mock辅助，未证明任意环境。

## 归档与接续

[总核对](evidence/2026-09-29-cross-session-revision/conclusions.json)、[第一轮核查](evidence/2026-09-29-cross-session-revision/round1/audit.json)、[第二轮核查](evidence/2026-09-29-cross-session-revision/round2/audit.json)、[变更后旧证据拒绝](evidence/2026-09-29-cross-session-revision/round2/after-revision-before-new-checks.json)、[最终独立检查](evidence/2026-09-29-cross-session-revision/round2/parent-checks.json)、[实际关键调用](evidence/2026-09-29-cross-session-revision/round2/critical-calls.json)。31份精选证据见[哈希清单](evidence/2026-09-29-cross-session-revision/manifest.json)。原始输入、代码与部分canonical记录以合成导出保留；不归档整个.agent-workflow、个人配置或会话流，因此不是可独立重建全部原生环境的夹具。

这补足“变更后新会话能继续”的一例隔离证据，不新增能力，也不证明真实准确率或收益。下一步优先自然需求观察修订与接续成本；没有新需求时可检查有业务歧义的修订是否停在产品裁决，但不据本例扩张并行数或全面拆Skill。项目外临时写入边界属于继续观察的宿主采用限制，未在本轮修改运行规则。
