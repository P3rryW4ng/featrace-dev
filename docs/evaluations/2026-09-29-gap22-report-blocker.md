# GAP-22：读取失败的项目报告留痕补强（2026-09-29）

## 结论与边界

0.5.33 的最小修正已实现并在全新原生会话观察到：读取被拒绝后，Agent 单独把真实阻塞保存到项目内报告，保持 provisional，未更新完成状态。原0.5.32两次失败[原样保留](2026-09-29-gap22-boundaries.md)。本轮不是267项脚本回归、全PRD长链或自然需求收益测试。

正常对照最终取得单独全文返回并核对后complete，但首次Write/Read曾同批派发，Agent自行纠正。因此本轮证明失败留痕修正及最终完成前的有效回读；**不证明首轮顺序严格采用或长期稳定**。GAP-22的读取失败留痕子缺口已测通过；调用顺序仍应持续观察，不宣称全部风险消失。

源码0.5.33，尚未提交/推送/安装；个人Claude保持0.5.32。北极星、阶段状态不变，不新增命令、Python脚本、字段、调度或多Skill能力。

## 修正内容

仅修改按需加载的verification-workflow：回读前结论保持条件式；读取缺失、拒绝、失败或未补齐时停止complete。报告仍可写则单独保存blocked/provisional、实际失败、仍有效的历史证据与合法下一步，撤回无条件完成措辞。报告不可写则说明未能本地留痕，外部摘要仅作真实兜底，不能假称已保存。写入不等于阅读，不通过改权限绕过读取。不可写兜底本轮没有实际故障注入，属于规则而非已验证能力。

## 隔离方法

两份全新副本来自0.5.32完整演练项目，不继承负向注入后的来源或报告。权威状态重置provisional、删除报告并重新生成视图，预检查validate(check)/audit均0。74个运行文件冻结为临时插件featrace-gap22-report:dev，与最终源码哈希逐一相同；两会话实际调用原生Skill next，使用当前登录CLI默认模型，无模型覆盖，无浏览器/MCP。提示只授权交付，不提前提示“写阻塞报告”的预期答案。

读取失败沿用上轮PreToolUse注入：保存后拒绝指定报告Read及提及delivery-report.md的Bash读取，返回EACCES；Write/Edit仍可用。不是操作系统chmod测试，也不是对所有别名绕过的沙箱保证。正常对照没有故障。两个会话各有独立目录，虽独立运行，不证明生产调度或并发共享状态安全。

## 实际结果

| 场景 | 实际调用及结论 | 现场与限制 |
|---|---|---|
| 读取失败 | Write10成功返回 → Read11被拒绝 → Edit12、13分别更新本地报告；零complete操作，最终provisional | 初稿条件式；最终顶部和结尾均blocked/provisional，保存EACCES、未获得任何报告文本及下一步。仅新增项目报告，旧质量时间/验证历史/来源/代码/HEAD/暂存和个人安装不变 |
| 正常对照 | Write11与Read12同批；Read13被宿主去重；独立Bash14 cat全文成功 → 核对15 → 状态16 | 最终全文返回与保存文本一致，报告未再修改；complete。初次批处理偏差真实保留，不算无偏差通过。新增报告、status及派生视图，代码/来源/旧检查历史保留 |

正常对照还因原子JSON写入把文件模式变为0600，调用18将requirements.json恢复0644。实际发生过模式恢复；其外部摘要“permissions未改变”过于宽泛，不采信。该操作未改变读取注入或权限规则，也不是读取拒绝绕过，但属于提示要求不改permissions的范围偏差，不能将整次对照称作严格副作用完全合规。未修改个人配置、安装或宿主权限。无需为了掩盖该动作重新演练或改写原证据。

父会话事后执行两例validate(check)/audit均0；读取失败仍禁止完成，说明这些结构/新鲜度检查并不证明强制回读已成功。正常对照的feature-status固定输出not evaluated不等于语义完成证明。20项目测试/35验收行系既有09:04:57Z运行，没有新执行或改时间。

读取失败121.369秒，CLI费用估计$0.7107296；正常对照157.406秒，$0.9056362。合计$1.6163658是CLI估计，不含维护者成本；独立进程耗时不是用户开发时间收益，不相加为墙钟时间。

## 证据与接续

[读取失败核查](evidence/2026-09-29-gap22-report-blocker/read-failure/audit.json)、[具体调用](evidence/2026-09-29-gap22-report-blocker/read-failure/critical-calls.json)、[初稿](evidence/2026-09-29-gap22-report-blocker/read-failure/report-at-save.json)、[最终报告](evidence/2026-09-29-gap22-report-blocker/read-failure/report-final.json)。

[正常对照核查](evidence/2026-09-29-gap22-report-blocker/positive-control/audit.json)、[具体调用](evidence/2026-09-29-gap22-report-blocker/positive-control/critical-calls.json)、[Agent自述及偏差](evidence/2026-09-29-gap22-report-blocker/positive-control/assessment.md)。32份精选证据见[哈希清单](evidence/2026-09-29-gap22-report-blocker/manifest.json)，[冻结运行身份](evidence/2026-09-29-gap22-report-blocker/runtime-identity.json)。不归档整个项目工作流、个人设置或完整会话流，故不是独立可重建的完整夹具。

三个Skill格式校验通过。没有Python运行脚本变化，不重复旧267项套件。使用流程图同步失败分支。下一步按用户授权收口发布安装；自然需求观察交付顺序、遗漏、介入与成本。暂不扩大并发/拆分或宣称L2完成。
