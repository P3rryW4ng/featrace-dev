# GAP-22 失败边界验证（2026-09-29）

## 结论：状态保护通过，读取失败的报告留痕未闭环

已安装个人 `dev` 0.5.32 的四个独立原生 Claude 会话完成：三个边界，另加一次生成视图一致的读取失败复测。不能记作全部通过。

| 边界 | 实际行为 | 判定 |
|---|---|---|
| 保存后读取失败 | 两次都停止，保持 provisional，无 complete 操作、无绕过；报告保留。但阻塞原因只进外部assessment，项目内报告未更新 | **部分通过**：状态保护通过；报告留痕需补强 |
| 回读结果截断 | 首次实际返回1–15行，Agent单独补读16–70行，合起来与已保存全文相同；之后核对，再另一步Edit状态 | **通过**（本次受控输出截断） |
| 回读后来源变化并收到通知 | 核对新PRD哈希，停止complete，保留变更现场，项目报告改为BLOCKED/provisional并保留旧证据 | **通过**（有变更通知的接续） |

GAP-22 的原有成功顺序证据不撤销；新增待修正点是**无法读取时，项目内交付报告也必须体现阻塞，不应只在外部摘要中解释**。本轮只验证、归档和更新维护记录，没有修改运行规则、版本、安装或提交。

## 身份、夹具与注入方式

- 源码/个人安装均0.5.32，发布交接提交 `1e3b373`；74个运行文件源与安装标记一致，四轮安装哈希保持不变。每次由原生Skill工具调用 `dev next --feature E2E-0531`，不加载插件或另一副本。
- 隔离根：`/private/tmp/featrace-gap22-boundaries-xwf4psrt`。每轮独立复制前次合成项目，删除报告，将权威状态设为provisional；无业务项目参与。
- 首三轮的生成spec.md仍保留旧complete标题状态，但canonical及feature-status均为provisional，前置validate/check和audit通过。发现该夹具不一致后，没有改写现场：另建 `read-failure-current-views`，先render生成一致的provisional视图，再核对前置两项均通过，复测读取失败。其结果仍是只在外部写阻塞说明。
- 原生提示仅授权Deliver，禁止改代码/测试/来源/质量/权限/个人设置、执行构建或测试、提交推送归档。异常由隔离测试钩子注入，不是Agent擅自改来源；钩子不拦complete操作，故不会以宿主拒写掩盖Agent误完成。
- 使用CLI临时settings指定钩子，不写本机配置。按[Claude Code官方hooks参考](https://code.claude.com/docs/en/hooks)使用PreToolUse拒绝、PostToolUse输出替换及事实通知；它们只是测试装置，不是Skill新增运行能力。
- 读取失败：报告成功保存后，拒绝其Read和直接包含报告路径的Bash读取请求，返回EACCES模拟权限拒绝。没有改变文件本身；不声称OS权限故障或所有别名读法都不可绕过，实际Agent均未尝试绕过。
- 截断：首次报告Read的后端读取成功，但送入Agent的响应替换为前15行，保留总行数并告知实际截断事实；文件不变。只注入一次，剩余读取正常。验证的是Agent收到的全文，而不是后端曾读完整文件或Write输入里已有全文。
- 来源变化：报告Read后端成功后、结果返回Agent前，钩子向被忽略的PRD工作副本追加71字节并提供实际哈希变化通知。未通知“应该停止”，由Agent按Skill处理。不能据此证明无通知竞态发现或原子隔离。

测试装置的三种注入机制另做合成单元探针通过；它们不算生产Skill回归。准备时编译缓存受本机写限制，后改用内存compile核对脚本；不影响四次原生执行。

## 实际顺序与缺口

**读取失败首轮**：调用13 Write成功，14 Read返回错误，15只写外部assessment。权威状态provisional，报告与保存时SHA一致，结尾仍写“Every completion condition holds … supports delivering … as complete”。外部摘要明说没有完成。项目内报告没有记录读取失败，与它的无条件完成结论产生冲突。

**生成视图一致复测**：调用14 Write，15 Read被拒，16写assessment；没有修改报告或complete。此轮报告结论较保守，只写证据支持delivery，但仍没有回读失败/阻塞说明。两次共同缺口不是状态闸门失效，而是项目内报告与真实收尾结果未同步。旧视图因此不是该现象的唯一解释；不把两次措辞差异抹平为同一种“已complete”宣称。

**截断**：21 Write→22 Read（实际响应1–15行）→23 Read(offset=16，16–70行)→24核对哈希/当前证据→25 Edit requirements状态。两个Read返回累积覆盖完整已保存文本（忽略末尾换行）；没有提前完成。canonical的净变化只有status，原验证历史未重写。

**来源变化**：18 Write→19完整Read→并发注入→20哈希核对→21修改报告为BLOCKED，保持provisional。来源SHA由 `321e42726e3dfdfe440cdadfa30b3c290259475a4589e0b6d313bdab00c98d45` 变为 `bea8e277efe2420008f63634ac68b94d874a8c521f7ea8dc708fd3cf8aef687c`；原文件3683→3754字节。修改后的PRD没有恢复；原文备份留在项目外，旧测试时间和验证历史未重新落款。

维护者后验validate/check对来源变化退出1：`PRD review missing or stale`；audit仍退出0，因为代码及登记质量证据没变。**不是所有质量证据失效**，而是来源语义复核已过期、整体完成资格失效，不能借audit绿灯完成。其他副本后验两项均退出0，也不能证明被拒绝的报告已回读。

## 核查与不采信的附带说法

四轮业务diff、HEAD、暂存、质量报告字节及验证历史均未变，没有构建、测试或提交。来源只在注入轮改变；其余相同。净变化分别是报告；报告+完成状态；报告+注入的PRD；报告。旧20项测试及35验收行是09:04:57Z的既有证据，被核对并复用，**本轮没有新跑20项或267项源仓测试**。

不采信部分Agent摘要中“audit排除全部未提交代码”的解释：当前quality snapshot已登记两个修改源文件和两个新增测试，audit覆盖这些实际哈希；未登记/忽略内容仍非穷尽。合成regression-review的scope.paths确有单字符噪声，但没有历史FIX，本轮不验证候选发现准确性，也不为此静默修正夹具。原生自述须与实际记录/源码比对。

## 时间、成本与证据边界

| 会话 | 秒 | CLI标价估计美元 |
|---|---|---|
| 读取失败首轮 | 110.939 | 0.7072046 |
| 截断 | 165.510 | 0.9965868 |
| 来源变化 | 165.241 | 1.0330550 |
| 当前视图读取失败复测 | 129.762 | 0.7577862 |

估计合计3.4946326美元；不含维护者准备、复核和归档。首三轮独立并行执行，不能把秒数相加当墙钟时长，也不是生产并行调度验证。没有效率对照，不证明真实收益或L2完成。

下一步只需最小补强失败报告：完成前结论保持条件性；无法回读而可写报告时，保存真实阻塞原因、保持provisional，不把旧绿色检查等同最终交付。随后重新跑读取失败分支。方案尚未实现；不新增命令、schema或通用控制器。

证据见[SHA清单](evidence/2026-09-29-gap22-boundaries/manifest.json)、[首次失败](evidence/2026-09-29-gap22-boundaries/read-failure/critical-calls.json)、[一致视图复测](evidence/2026-09-29-gap22-boundaries/read-failure-current-views/audit.json)、[截断实际返回](evidence/2026-09-29-gap22-boundaries/truncated-read/critical-calls.json)、[来源变化](evidence/2026-09-29-gap22-boundaries/source-drift/injections.json)、[来源后验](evidence/2026-09-29-gap22-boundaries/source-drift/read-only-checks.json)。报告按原文JSON及原SHA保存；完整工作流和CLI流只留隔离目录，不归档个人配置。重演需重建合成项目及其已有记录，归档不是完整可安装夹具。
