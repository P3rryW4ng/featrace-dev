# 当前验证与历史查证入口

更新：2026-10-23。只索引当前实现和必要对照；不把过去测试记作本轮新跑，不以数量证明语义正确或净收益。执行顺序见[ROADMAP](../ROADMAP.md)，实际发布/安装见[MAINTAINER](../MAINTAINER.md)。

## 当前验证入口

正式0.26.1/合同3：复用[221项冻结结果](evaluations/readiness-diagnostics-20261023/result.json)及[实际发布安装核验](evaluations/release-0261-20261023.json)；原214项保留在历史截点。[模块顺序评审](reviews/2026-10-23-module-review-0260.md)是只读源码核对，未新增测试或Agent试验。下列按时间保留原始截点，不把旧标题/当时版本当当前身份。

## 历史截点：0.24.0发布前后，A109–A114及173项

[A109当时结果与原始产物](evaluations/2026-10-22-full-replacement.md)：当时128/128、16份运行/测试/安装器/版本输入冻结一致；双宿主临时目录各10文件、实际CLI通过；200合成任务记录629,600字节、最大3,148字节，模拟+8日后任务/日志0。首轮规模暴露锁冲突，红→绿与修复后的全量/规模重跑均保留。

本轮A110完整回归 **150/150**，18份运行/测试/安装器/版本输入前后一致，外层实测51.87秒。[本轮结果](evaluations/hardening-20261022/result.json)、[完整输出](evaluations/hardening-20261022/full.log)、[输入前](evaluations/hardening-20261022/inputs-before.json)/[输入后](evaluations/hardening-20261022/inputs-after.json)、[三个原始失败反例](evaluations/hardening-20261022/red.log)。[首轮集成](evaluations/hardening-20261022/integration-first.log)发现storage空回执错误，修复后纳入全量；没有把失败运行重命名为通过。[实际命令探针](evaluations/hardening-20261022/cli-probe.json)确认调查后只执行一次、解决未知后复用并结项，storage只读。全量后仅补正文档实际成员匹配说明，脚本/测试未变，差异写入result。skill-creator标准quick_validate因缺PyYAML未运行；实际Ruby YAML/frontmatter解析通过，不冒充标准校验器成功。

这是POSIX隔离程序/结构验证，不是真实Android/真机、50人并发、原生Agent、实际上下文压缩或200个业务需求。费用和真实净收益未测量。上述开发截点日常CC为0.22.0/119；后续0.23.0发布/安装结果单独记录，不改写早先实测。文档整理不重跑这些测试，冻结输入核对可证明本轮未改它们。

## 本轮A111：Figma指引与条件入口

[实际核对结果](evaluations/figma-adapter-20261022.json)：18个既有输入中仅SKILL入口变化，新增一份Figma指引；脚本、6个测试文件、安装器及VERSION均未变，因此未重跑原150项回归，也不将其写成本轮新测试。真实安装器向隔离home复制Claude/Codex两种布局，均为11文件，与来源及安装清单哈希一致，新增指引存在，均显式development身份；只做隔离副本，不更新日常CC。两份实际frontmatter/YAML解析通过。标准quick_validate仍因缺PyYAML不可用，不冒充通过。

当前宿主工具目录声明了设计上下文、截图、元数据、资源和组件映射接口；仅工具发现，不证明CC连接、认证或具体文件访问成功。没有提供目标Figma文件/节点或业务项目，远端调用0次，真实还原/视觉质量/自然上下文控制/净收益未测试，第二阶段仍未完成。

静态场景走查如下，仅表示指引如何处置这些边界，不是实际Agent执行测试或新增强制业务用例：

| 场景 | 指引要求的处置 |
|---|---|
| 私有报错图标/字号/间距 | 读取目标及必要父布局，复用项目资源；检查局部实际展示，不重新验收父PRD逻辑 |
| 共用组件/设计token改变 | 调查真实调用方及变体，扩展相关渲染；不把共享一词直接等同全业务复核 |
| 工具缺失/访问拒绝、但已有截图 | 诚实使用现有资料；缺少的尺寸/状态标未知，必要时询问具体缺口，不伪造实时节点数据 |
| 工具返回稀疏/截断上下文 | 结合参考图定位必要子节点，再定向补取；不把不完整结果当作全部设计 |
| 图标实际改变点击、语义或焦点 | 增加对应交互/状态/可访问性影响检查，不能仅贴UI标签 |
| 远端设计后来变化 | 核对相关设计差异，只更新受影响标准及必要检查；原观察时间不改，无法确认最新时只作截至某时的结论 |

新增指引只在Figma任务加载，无新增运行脚本/强制表单、全文件镜像/同步或写回。它不提供自动远端新鲜度校验，也不能替代宿主工具的专用前置规则。

## 同日较早证据，仅用于追溯

| 材料 | 用途与边界 |
|---|---|
| [A108首批纵切](evaluations/2026-10-22-task-workflow.md) | 791项及当时200任务数据，旧模块尚未裁剪；不作为当前通过证明，不执行其旧下一步 |
| [记录增长评审](https://github.com/P3rryW4ng/featrace-dev/blob/46fa61c/docs/reviews/2026-10-22-record-growth-and-retrieval.md) | codec增长和局部原型测量；永久对象库/历史兼容建议已被A109替代，不据此重开开发 |

这些同日材料尚未进入已提交旧版本，保留原始结果与哈希，不将其唯一原件假称已存在于远端Git。

## 已发布旧版与真实案例：固定版本查证

旧材料移出当前目录，按固定Git提交查阅；原始事实和历史通过/失败不因清理改写。

- [0.22.0发布/安装核验](https://github.com/P3rryW4ng/featrace-dev/blob/54c5260fd6688a0bca9c83f29bad240321a67b52/docs/evaluations/2026-10-21-release-0220.md)：正式/安装119文件，与当前11文件包不同。
- [旧验证索引](https://github.com/P3rryW4ng/featrace-dev/blob/54c5260fd6688a0bca9c83f29bad240321a67b52/docs/validation.md)：历次候选、失败、发布、安装、原生/隔离范围与限制。
- [8025耗时复盘](https://github.com/P3rryW4ng/featrace-dev/blob/54c5260fd6688a0bca9c83f29bad240321a67b52/docs/reviews/2026-10-18-ogfr-8025-cost-review.md)：CC转交的8小时21分，部分为估算，非维护侧实测；不能把全部时间归为可避免成本。
- [旧Skill审查](https://github.com/P3rryW4ng/featrace-dev/blob/54c5260fd6688a0bca9c83f29bad240321a67b52/docs/reviews/2026-10-19-current-skill-audit.md)：全负向留存、全局失效、权限和文档漂移等反例，不能用早先全量通过否认后续缺陷。
- [原始案例/历史文件目录](https://github.com/P3rryW4ng/featrace-dev/tree/54c5260fd6688a0bca9c83f29bad240321a67b52/docs)：需要查证时定向阅读，不作为新任务前置加载。

## 第二阶段自然验证口径

正常完成新需求后一次只读复盘：核对实际加载包/代码/产物身份、改动因果范围、检查与断言、实际观察/静态分析/未知、失败/补证/自动接续、必要与非必要人工介入、现有可归属时间/usage/费用。不为复盘重跑测试、改记录、重签旧观察、操作设备或增加重复表单。

墙钟不等于人工工时；聊天/提交间隔不能证明投入，父子/并行/累计用量不直接相加。未知不是0，缓存读取/context大小/账号额度不是账单。无等质可信基线只报告本次观测，不承诺节省。真实压缩或换会话只有自然发生并有记录才算实测；机械新进程恢复不替代它。

需包含展示与行为/共享反例，不能只报告成功案例。仍要识别错误完成、漏验、误阻塞及声明过宽；重要问题落回当前队列，已结项旧需求不因评估新工具被重开。具体未解决风险保存在ROADMAP，不另设永久复盘台账。

## 0.23.0最终发布输入

[发布冻结结果](evaluations/release-0230-20261022/result.json)：150项完整回归通过，外层实测51.31秒，20份运行/测试/安装器/版本/发布描述输入前后一致；[输入前](evaluations/release-0230-20261022/inputs-before.json)/[输入后](evaluations/release-0230-20261022/inputs-after.json)、[完整输出](evaluations/release-0230-20261022/full.log)保留。发布描述固定11文件和安装器哈希，未重跑任何业务项目。

暂存99个新增/修改文件分两批扫描，原始输出[第一批](evaluations/release-0230-20261022/privacy-0.json)/[第二批](evaluations/release-0230-20261022/privacy-1.json)保留。唯一候选为retirement授权说明，与先前人工确认普通文字的精确哈希一致，[处置](evaluations/release-0230-20261022/privacy-disposition.json)未关闭规则或篡改结果。后加入的本节与发布结果文件另行精确扫描；no_matches不等于全面隐私认证。实际推送、正式安装与身份核对需执行后记，不提前声明。

发布暂存核对发现一处脚本行尾空格，修正并更新发布描述后已重新冻结完整回归；仅上述最终输入作为发布凭据。原始失败日志末尾空行保持原样，格式核对排除该唯一原始日志，其哈希继续核对。

## 0.23.0实际发布与安装

[远端核对](evaluations/release-0230-20261022/publication.json)：正式6ace50d已原子推送，发布分支和标签解引用相同；后续main只提交核验记录，正式引用固定。[正式包探针](evaluations/release-0230-20261022/formal-probe.json)使用已提交引用、不带development选项，Claude/Codex两个隔离目录均为release身份、11文件，来源及实际字节一致。[日常CC实测](evaluations/release-0230-20261022/installation.json)版本0.23.0、来源6ace50d，11文件与正式清单一致，旧0.22.0/119备份完整。没有更新个人Codex安装、访问业务设备/后端、重新验收旧需求或验证真实Figma。新会话加载后才能观察实际工具与Agent行为；第二阶段仍未完成。

## 0.23.1进度指引补丁

[实际核验](evaluations/release-0231-20261022.json)：运行包仍11文件，仅SKILL入口内容改变；11份内核/测试/安装器文件与0.23.0逐字节一致，故未重复执行原150项回归或业务测试。YAML、局部文档链接与精确输出扫描通过。正式237afd1已推送固定发布分支/标签，日常CC为0.23.1正式身份，所有实际字节与来源/清单一致，旧0.23.0备份完整。

这是指导Agent使用宿主原生展示、无工具时正常简短说明进展的指令修正，不新增UI渲染器、进度台账或自动能力注入。不能从安装成功推出原生任务工具可用或实际面板已出现；仍需真实CC会话观察，不为验证展示重做业务测试。

## 2026-10-23 A112第一批边界修正（未发布）

五个旧实现反例：1个断言失败、4个错误；对应选择能力缺失、失败详情缺失、中断仍显示旧通过及结束身份错误未登记。原始工具输出在维护会话，preparation.json仅为结果摘要，不冒充原始日志。修改后11个去重定向用例通过，首轮误加载继承用例的118次调用不计为新增覆盖。

完整当前源码回归：**161/161**，外层实测66.629秒，21份输入前后哈希一致。[本轮结果](evaluations/review-boundaries-20261023/result.json)、[完整输出](evaluations/review-boundaries-20261023/full.log)、[输入前](evaluations/review-boundaries-20261023/inputs-before.json)/[输入后](evaluations/review-boundaries-20261023/inputs-after.json)。冻结回归后仅同步运行指引/维护文字；脚本和测试未再变化。测试使用合成临时仓库，不是业务/设备/真实新上下文验证。

没有发布、安装、业务验收或效果节省声明；VERSION和正式发布身份仍0.23.1。观察有效期、重复扫描成本和自然Agent行为未在本轮解决。

## 2026-10-23 时效探针与扫描成本（不变内核）

[评审与口径](https://github.com/P3rryW4ng/featrace-dev/blob/46fa61c/docs/reviews/2026-10-23-observation-freshness-and-scan-cost.md)、[原始测量](evaluations/freshness-scan-20261023/results.json)、[程序](evaluations/freshness-scan-20261023/measure.py)。两组4MiB/80MiB合成输入，1/4/8项各3次状态查询；共18次查询任务字节未变，两组输入突变均使8项失效。80MiB/8项查询0.541–0.585秒、重复逻辑哈希640MiB，暖缓存结果不能外推真实Android或磁盘I/O。手工观察模拟30天后仍可采用，说明当前没有自动时效约束，不代表远端状态实际不变。三个运行源码哈希不变，未重跑161项、未实施缓存优化或时效字段、未操作业务/设备、未发布安装。

## 2026-10-23 A113时效实现与合并候选验证

新增12个定向反例通过：as_of时间不失效、current过期局部阻塞且记录不变、登记/复核不刷新时钟、期限内目标变化、错误目标/静态证据拒绝、失败不过期、独立检查继续复用、执行按原started_at判断、无效字段拒绝、过期检查实际重跑、过期通过不能解除失败。最初旧实现10项中9项因未支持字段报错、1项非法合同拒绝通过，原始工具输出在维护会话，preparation仅摘要。

含A112四项修正在内的完整当前候选回归：**173/173**，外层实测55.134秒，22份输入哈希前后一致。[结果](evaluations/observation-validity-20261023/result.json)、[完整输出](evaluations/observation-validity-20261023/full.log)、[前](evaluations/observation-validity-20261023/inputs-before.json)/[后](evaluations/observation-validity-20261023/inputs-after.json)。此后只同步指引/维护文字，脚本和测试未变；不是实时后端、实际设备或新上下文Agent验证。

保留已有扫描测量当时输入身份，不把它套成新脚本性能证明。没有发布安装，正式CC仍0.23.1。内核不自动发现环境变化、识别语义中的“当前”或证明时效依据合理，不宣称第二阶段完成。

## 2026-10-23 能力映射基线（不新增执行）

见[标准与看板](capabilities.md)、[机器可读场景/引用](../tests/capability-cases.json)。将既有173项日志中的13个不同用例映射到6项程序保护能力，AST方法存在性、精确通过行及冻结脚本/测试哈希一致；未重新运行这些测试。所有9项Agent能力评分为未知，6类场景均未执行，不把映射覆盖率当整体完善程度或真实收益。

仅新增维护文档与测试引用数据，无运行代码、业务检查、派审或安装变化。后续以同一执行日志更新受影响能力，严重错误单列，不生成全Skill总分。

## 0.24.0实际发布与安装核验

[正式核验](evaluations/release-0240-20261023.json)：7e9ea17已推送main/固定发布分支/标签，远端一致；双宿主隔离正式包与实际CC均11文件哈希匹配。日常仅Claude更新，旧0.23.1完整备份。未重跑不变173项，后续指引与元数据单独核对；33文件选定暂存隐私扫描无匹配，YAML与链接正常。未创建GitHub Release页面、未操作业务或个人Codex；自然Agent评分/宿主呈现/净收益仍未知。

## OGFR-8897反馈后的policy诊断与Android指引候选

只修已知policy错误及CLI安全透传，未知异常不输出私有内容。4项CLI用例旧实现3失败/1通过，修复后4通过：[原反例](evaluations/policy-diagnostics-20261023/red.log)。完整177/177，外层124.361秒，23输入冻结一致：[结果](evaluations/policy-diagnostics-20261023/result.json)、[完整输出](evaluations/policy-diagnostics-20261023/full.log)、[前](evaluations/policy-diagnostics-20261023/inputs-before.json)/[后](evaluations/policy-diagnostics-20261023/inputs-after.json)。合成临时Git/CLI，不是业务/Gradle/设备/自然Agent验证；之后只补维护文字，脚本测试未变。

Android文档不新增解析器或强跑门禁，不能证明CC已遵守。安装仍0.24.0。用户转述与未独立读业务原件的边界见能力看板，不用程序通过替代业务缺口。

## OGFR-8897自然样本的证据等级

[转回摘录与更正](https://github.com/P3rryW4ng/featrace-dev/blob/46fa61c/docs/reviews/2026-10-23-ogfr8897-field-review.md)、[暂定能力评价](capabilities.md)。维护未直接读业务原件/执行补测，不把CC自述升级为独立验证。K3有previous_failure，原分析已撤回；C6旧XML和当前引用不对应，原执行摘要缺失，适用性待核；C2/C3承诺失败行为未被充分验证，C4仅成功路径。局部评分仅对本场景有效，没有总分或节省率，阶段仍未完成。此文档更新不重跑177项。

## 有界更正与固定0.24接续：候选验证

13项定向更正用例通过；旧实现8项因无入口报错，[原始反例](evaluations/correction-20261023/red.log)。完整190/190，外层59.159秒，24输入前后一致：[结果](evaluations/correction-20261023/result.json)、[全量](evaluations/correction-20261023/full.log)、[前](evaluations/correction-20261023/inputs-before.json)/[后](evaluations/correction-20261023/inputs-after.json)。冻结后仅同步指引/维护文字，脚本测试未变。

[实际旧CLI探针](evaluations/correction-20261023/legacy-probe.json)使用本地固定v0.24.0的真实脚本字节并核对发布清单，在临时Git夹具中真实执行/评估/结项。新入口保留原回执与同一执行ID/所有执行字段，重关关联原回执；物理执行总数1，旧CLI拒读格式2。[探针程序](evaluations/correction-20261023/legacy_probe.py)可在仓库根运行，需本机固定旧引用及当前测试夹具；它是隔离程序接续，不是自然Agent试点。探针从stage改为当前源码定位并补固定提交校验后重跑通过，不因此重复190项。

有界历史、输入/产物变化、权限拒绝、时效和清理拒绝反例保留。没有实际Gradle/设备/8897业务更正或当前安装变更，不宣称其证据缺口已补齐。正式CC仍0.24.0；发布身份未准备，不把候选VERSION文字冒充正式能力。

## 0.25.0 publication and installation

[Actual verification](evaluations/release-0250-20261023.json): official1fd6cf4, remote branch/tag verified. Daily CC and two isolated host installations matched all11 files; old0.24.0 backup complete, only daily Claude updated. Existing190 regression results reused against unchanged scripts/tests; no new full run or business operations. Metadata and links checked separately. Initial isolated verification had an incorrect Codex path; actual .agents path passed. No natural-Agent outcome or phase-two completion claim.

## 2026-10-23 验收底层评审（无新运行验证）

[评审](reviews/2026-10-23-acceptance-core-review.md)对照0.25.0源码、既有测试含义和8897直接只读补核。识别主张/证据及执行身份来源的局部替换候选；未来反例只是规格，未执行。维护入口清理采用固定46fa61c原件，不改历史证据。运行脚本、测试、VERSION、release.json和个人安装未变，未重跑190项或业务测试。具体静态取消证明不外推全部并发主张可静态验收；实际设备包身份核对依赖当时CC记录，不伪称重新测量。

## 2026-10-23 合同3底层替换最终验证

完整当前回归 **214/214**，外层81.091秒，26份输入前后一致：[结果](evaluations/core-replacement-20261023/result.json)、[全量](evaluations/core-replacement-20261023/full.log)、[前](evaluations/core-replacement-20261023/inputs-before.json)/[后](evaluations/core-replacement-20261023/inputs-after.json)。185项保留保护用例加29项新增反例；五项仅服务已退出前驱桥接的旧用例退休，两个静态判定用例改为明确证明需求，不放宽真实失败保护。开发期间失败/修正说明见[记录](evaluations/core-replacement-20261023/development-notes.json)，不是隐藏失败或额外独立样本。

[探针结果](evaluations/core-replacement-20261023/probe-result.json)、[程序](evaluations/core-replacement-20261023/probe.py)：64标准/128事实，实际155215字节低于262144上限；不保证任意长文字/输入组合都适合该上限。新进程只读恢复、分页无写入；读取固定v0.25.0真实脚本并核对清单，旧CLI拒读合同3且记录字节未变。双宿主隔离开发安装均12文件匹配，正式安装未变。探针程序移至可从仓库根执行的位置，不更改已执行逻辑或重跑完整套件。

[五份退出文档原件清单](evaluations/core-replacement-20261023/retired-docs.json)：当前字节与固定fe508f0核对后退出，链接改为固定Git；未删除Git历史或业务记录。运行指引/日常流程已替换，旧方案不作为当前路由。旧测试/证据仍只代表其当时合同；没有更新版本/发布清单、推送或个人安装。本轮不是自然Agent、真机/后端、50人并发或提效对照试验，第二阶段仍未完成。

本轮Skill快速校验脚本因本机缺少PyYAML未能运行；未安装依赖或声称其通过。独立Ruby YAML解析核对入口frontmatter与agents元信息通过，全部当前Markdown本地链接及能力用例引用可定位，冻结26份运行/测试/元数据字节仍一致。

收尾补核：五份退出文档也与已推送46fa61c逐字节一致，当前历史链接固定到该可访问提交；fe508f0仍保留最初工作树核对身份。实现本地提交be8c0f2，运行/测试26份冻结输入未变；文档整理不重复测试。

## 0.26.0正式发布与CC安装核验

[实际核验](evaluations/release-0260-20261023.json)：91fc9a7已推送main/固定分支/标签，远端一致；实际CC及双宿主隔离正式包12文件字节匹配，旧0.25.0备份完整，仅日常Claude更新。原214项运行/测试字节不变，仅VERSION/发布描述变化；没有新一轮全量或业务测试。9个发布暂存文件隐私无匹配，链接/清单正常。初次推送审批要求验证具体远端，核实原仓库ADMIN权限后获准完成。未创建GitHub Release页面；自然Agent正确性、压缩恢复、净成本与第二阶段完成均未据此宣称。

## 2026-10-23 状态阻塞原因小修（未发布）

[完整结果](evaluations/readiness-diagnostics-20261023/result.json)、[原始日志](evaluations/readiness-diagnostics-20261023/full.log)、[冻结前](evaluations/readiness-diagnostics-20261023/inputs-before.json)/[后](evaluations/readiness-diagnostics-20261023/inputs-after.json)：221/221，214项原保护加7项新诊断反例，执行期间输入一致。覆盖范围未知/输入漂移/缺策略/适用规则变化、范围就绪不等于交付资格、未知异常和伪代码消息不泄露、不执行不写入且结项仍阻塞。[协议对照](evaluations/readiness-diagnostics-20261023/protocol-check.json)核对实际修前/当前执行闭包相同，查询小修不使执行身份失效。

外层实测用时84.219秒；起止及输入数见result。新反例在修前均暴露字段缺失，最初测试编辑缩进错误及证据边界见[开发说明](evaluations/readiness-diagnostics-20261023/development-notes.json)，原红结果仅在维护工具回执，不伪造独立日志。验证后只更新维护文档和能力证据指针，脚本/测试代码不变。未操作业务、设备、后端或安装，不把本轮程序回归当真实Agent能力得分。

## 2026-10-23 北极星相关指引完善（无新程序执行）

[核对结果](evaluations/northstar-guidance-20261023.json)：三项依次完善现有运行指引，无新命令/字段/运行文件，源码与测试等既有Python输入全部匹配221项冻结身份。核对6个现有方法AST及原完整日志中的精确通过行，覆盖改字仅重判、原观察身份不变、来源局部失效、静态不能替代新增运行承诺、新进程恢复不重跑、限制交接后遗忘；没有新执行或新Agent得分。

五个边界仅作静态指引走查：UI澄清、共享/交互反例、失败后接续、到期知识去向、真实撤回与失败保护冲突。它们不是自然试点或新自动化保护；不宣称语义理解、自然压缩、知识交接完整性已验证。使用说明图同步必要知识去向；真实观察按[精简标准](pilot-observation.md)。未推送/安装，当前运行脚本和正式身份不变。

## 0.26.1发布准备

复用readiness-diagnostics的221项冻结结果；17份Python程序/测试/安装器输入与当前字节一致，指引单独核对，不重跑不变套件。补丁版保留合同3/12文件，更新双语README、使用说明与实际发布清单。实际远端/隔离正式安装/日常CC更新在执行后记录，不预先宣称通过。

## 0.26.1实际发布与CC安装

[实际核验](evaluations/release-0261-20261023.json)：正式abac4f1和远端main/发布分支/标签一致；双宿主隔离正式安装及日常CC均12文件匹配，完整备份旧0.26.0，仅日常Claude更新。复用221项，17份Python程序/测试/安装器身份未变；指引/元数据/链接另核对，8个发布暂存文件扫描无匹配。不重跑业务或制造自然Agent试点，阶段二仍未完成。

## 2026-10-26三批顺序隔离Agent演练

[冻结规格与可复建夹具](evaluations/isolated-agent-20261026/assessment-plan.json)、[精简执行身份与计数](evaluations/isolated-agent-20261026/results.json)、[评审与反证](reviews/2026-10-26-isolated-agent-review.md)。固定0.26.1运行与安装12文件前后一致；6个适配场景及1个长期资料后续任务，执行者与评审者使用实际独立新上下文，未拿评分答案。维护者设计规格且知期望，非盲测；读取路径隔离仅为指令约束。

可复建包22个独立文本blob共23,287字节，在全新临时目录逐文件核对重建，无旧任务事实复制或业务数据。新增重建脚本后的完整当前套件实际运行一次221/221，外层75.955秒、30份冻结输入一致：[结果](evaluations/isolated-agent-20261026/repository-validation/result.json)、[全量日志](evaluations/isolated-agent-20261026/repository-validation/full.log)。此维护回归不是Agent自然判断证据。

实际失败、启动重试、执行前拒绝与第一版修复后的兼容补充均保留在精简计数/报告；原临时任务和证据不入维护仓库。SC06旧失败全字段一致、新事实明确解决；后续克隆仅含受管资料，原任务没有删除，不冒充到期清理。原说明曾将SC06修复后两次通过说成一次，读原记录后已更正：第二次实际修改空值保护/断言，非登记重跑。

嵌套构建缓存归属、真实远端时效/期限、自然压缩与CC原生进度、真实移动设备、Figma和7日清理未在本轮验证；成本无等质量基线，未知不填0。0.26.1正式/安装不变，纯文档收尾不重复完整套件或业务检查。

收尾身份核对：完整回归期间30份输入一致；结果登记后29份仍与冻结字节一致，唯一变化为tests/capability-cases.json的场景状态/证据指针元数据。已确认没有代码/测试读取该目录表，JSON及链接核对通过，运行与测试断言未变，不重复运行套件。

## 2026-10-26共享分类与独立评审触发评审（只读）

[专项报告](reviews/2026-10-26-shared-review-trigger-review.md)核对0.26.1指引、validate_plan/review_required/assess/view/criterion_stamp、现有测试与SC02/04/05原件。确认shared强制独审条件；未新增测试或Agent，不能把旧221项视为候选政策验证。SC04/05缺实际生产调用依据，夹具共享评审条款使成本归因存在混杂；不宣称独审全部多余。静态AST查询确认run_check→ready→validate_plan进入执行协议采集，未执行升级或复用探针。候选分离共享调查与风险/项目规则驱动独审，开发反例尚未执行，运行/版本/安装和业务记录均未改。

## 2026-10-26共享评审策略局部替换：程序验证

完整当前回归228/228，外层88.130秒，27份运行/测试/安装/版本输入前后一致：[结果](evaluations/shared-review-fix-20261026/result.json)、[全量](evaluations/shared-review-fix-20261026/full.log)、[前](evaluations/shared-review-fix-20261026/inputs-before.json)/[后](evaluations/shared-review-fix-20261026/inputs-after.json)。新增7个反例；原shared强制独审测试改为真实低风险共享可自评，不减少实际失败、权限、时效、出处/选定事实等保护。项目必要评审反例验证的是已声明选择的程序强制，不冒充自动读懂项目规范。

定向开发首次测试1项预期写错：静态覆盖运行失败应被RUNTIME_FAILURE_NEEDS_RUNTIME拒绝，而非登记后再阻塞；修正反例，未改保护。首次定向导入也额外发现基类被unittest收集，改为模块引用，避免新文件增加无关基类重复；7项定向及完整228项均通过。首轮62项结果为开发工具回执，未伪造独立红日志。

[旧/新协议边界](evaluations/shared-review-fix-20261026/initial-protocol-boundary.json)实际采集固定abac4f1源码及候选源码，确认首次拆分协议不同；不会自动认可旧任务执行。新增反例核对验收校验源码变化不改变新协议、原执行ID/全部字段/日志/时间保持，真实执行校验变化仍物理执行。该变异测试改变被采集源码而非宣称部署任意版本兼容；完整模块仍保守绑定。真实Agent前向验证单列，不把程序结果充作主观范围选择证明。

共享评审候选前向验证：[实际报告](reviews/2026-10-26-shared-review-fix-result.md)、[共享UI运行](evaluations/shared-review-fix-20261026/agent-forward-result.json)、[明确强制条款只读规划](evaluations/shared-review-fix-20261026/mandatory-rule-result.json)。第一例3次浏览器尝试（1启动失败，2页面通过），无领域/键盘重测，shared保留而有据自评；第二例0运行/0写入，明确要求局部独审。原任务/运行日志/产物摘要已核对，不将只读计划算新验收或真实独审。日常CC仍固定0.26.1；候选安装只在会话独立目录，12文件字节匹配。通用quick_validate因缺PyYAML不可运行，frontmatter未改，未声称该工具通过。

## 0.27.0实际发布与CC安装

[实际核验](evaluations/release-0270-20261026.json)：正式2c75539已推送main/固定发布分支/标签，远端解引用一致；双宿主隔离正式安装和日常Claude均12文件与源码/描述/安装清单匹配，旧0.26.1备份精确完整。仅更新日常CC，无业务操作或个人Codex更新，未创建GitHub Release页面。228项运行与测试结果复用，25个非发布元数据输入匹配；VERSION和release.json变更单独核查，双语README修正过时214计数。8个发布暂存文件及2个元数据说明修正扫描无匹配，链接与清单通过。最初对照漏列release.json，已在固定引用前更正，未重跑套件。已有业务复盘只属于当时版本，不因当前安装追溯成为新版自然证据。

## 2026-10-26 OGFR-9060-9062原版本只读反馈

[报告](reviews/2026-10-26-ogfr9060-field-review.md)：业务事实仅来自用户转回CC复盘；维护直接核对固定0.26.1和正式0.27.0的observe/fact_applicability/observation_stamp/validate_plan/执行策略身份源码。确认同标准较晚运行通过自动解除待决失败，未比较复现条件；改expected不恢复失败指针也不可靠排除文件相同对照。A09旧shared+false与计划保存的关系待原categories核实。没有执行新反例、测试、设备或业务流程，没有改任务/安装；本报告不是0.27.0自然效果，也不改228项原结果。

同日补核更新见原报告末节：用户转回A07两事实与判定项结构、原产品决定时间、A09分类/review；维护未读取业务原件。只读源码确认解除不比较旧/新input_digest，不能误写成“digest相同才解除”；validity也不是通用场景字段。A09只声明presentation/state，原guard未触发的原因已明。候选提出失败采集与解除/延期/错误纠正分离，读写者和反例尚未开发或执行；运行/安装不变。
