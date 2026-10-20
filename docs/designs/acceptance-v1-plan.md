> 后续发布检查点：用户已在候选核验后批准0.19.0提交推送及日常安装；下文早期授权状态保留为设计时事实。业务项目未迁移。见[发布记录](../evaluations/2026-10-20-release-0190.md)。

# 验收机制替代：最终可开发方案 v1

日期：2026-10-20。状态：**设计定稿，用户随后已批准隔离实现；候选自动核验完成，未批准实际发布或项目迁移**。源码基线 main `3f5ddcee232bea98ed09f8dab5e3f9ac2837658e`，运行安装0.18.4/113。本文取代[上一草案](../reviews/2026-10-20-acceptance-contract-design.md)的开放接口约定；[架构评审](../reviews/2026-10-20-acceptance-architecture.md)保留理由与反证。没有独立第三方认证；实施中若证明约束无法满足，停止并报告，不靠例外维持既定方案。

## 1. 固定开发决策

首批替换**主张适用性与终审绑定**，同时接管普通状态、审计与交付读者。保留原执行器、输入检测、原始事实、必需门禁和产品权威。不是只改一个摘要，也不是重写全部验收。

成功目标：同一代码/测试/命令输入下，局部要求或决定改变，可以只重新判断受影响或未知主张；其他主张通过一次完整差异排除证明复用已有判断，不逐行重新登记原事实、不要求再读全部未变原件。最终仍核对全部活动主张。无依据的“依赖没命中”不能免验。

明确不做：单项检查缓存/输入闭包引擎、拼不同attempt的通过项、设备历史观察拼接、档案粒度拆分、自动依赖完备性、自动产品取舍、取消独立判断、旧项目自动升级、重新验收已结项案例。代码或共享配置变化时，当前执行器仍可能要求整组选中检查；不能宣称本批已消除全部验收成本。

采用单一新内部模块 `acceptance_contract.py`，数据在现有 `verification.json` 内，外部仍用普通next/check。新文件/新版本只能作为实现结果报告，不能把本文当已实现功能。

## 2. 硬性不变量

I1 原事实不可改写；测试版本、时间、结果和原件保持原义。判断改变不伪装成新执行。
I2 当前判断不等于历史事实；世界输入有变化，先待审，不自动失败，也不自动保留通过。
I3 完整变化与全部当前主张均须覆盖；遗漏、未知、部分观察不能凑绿。
I4 同一问题的最新失败/撤回/负向不得通过旧成功、改key、退役或换审查者消除。
I5 独立审查实际需要新上下文；字符串声明不证明独立。无此宿主能力时保持provisional。
I6 脚本检验结构、引用、身份和状态，不声称能证明审查者的语义推理或依赖完备性。
I7 一个需求只有一个活动写入合同；新读者不得回退旧全局戳来补救新合同阻塞。
I8 必需检查、设备FIX、模块档案、需求/任务/修复/来源等控制项仍分别校验，不能被主张复用绕过。
I9 不允许未识别字段、未分类变化或未知读者被默认为无关。
I10 失败、未知和成本变差同样归档；不以投入、功能数或通过数量替代收益。

## 3. 首批进入条件与事实来源

新增格式固定为 `schema_version=6`、`acceptance_contract=1`；正式版本按合同变化评估中间位升级，建议0.19.0，不作为0.18.5提示补丁。根VERSION本轮不变。

- 自动执行仅接入现有 execution_contract2。它是项目级标记，prepare前必须盘点参与活动需求、选择和全部宿主；复用既有准备流程，不在此批修改其启用粒度。
- 支持直接manual passed/failed/unavailable/waived及not_run、当前完整合同2 attempt。旧自动quality-report仅保留历史，不能假冒新attempt。
- schema1–5可读取原格式。**迁移候选事实**必须是可恢复条件的直接原登记；retention_kind、scope_ref、注解/采用等复合链本批不做新适配，若当前活动目标依赖这些链，则整个prepare拒绝并列出，不能跳过活动行。
- 原格式历史中存在复合链并不一律拒绝；只要不作为当前候选来源，旧读者能验证其容器，且没有未解决较新失败，仍可保留为只读历史。
- 设备原回执/连续性与模块档案仍按原合同运行；其读取当前验证失败的地方须适配统一事实障碍接口，不能因新格式改变而漏掉失败。
- 首批迁移对象仅是用户已授权继续变更的活动需求；历史complete不自动重开。全新需求可直接初始化，但仍需用户原始要求及显式合同准备范围。
- 没有可靠环境身份时，只证明事实记载的环境与范围；不能认证未知目标环境。

### 原始历史不用再复制一份

上一草案把原history继续嵌在新文件的方案收敛为**Git原件引用**：首批迁移要求旧verification和旧claim-review（若存在）已在同一可恢复提交中完整保存，工作区字节与该提交一致。prepare不自动提交。未提交时先按原授权正常提交或保持原状；这是一次性前提，不是每次验收要提交。

来源引用固定为完整commit、相对路径、Git blob OID、原始字节SHA-256及记录内JSON Pointer。commit必须在当前历史可恢复，原件必须能按原格式验证；浅克隆缺对象则明确拒绝/请求授权取回，不能凭摘要认定内容。禁止将旧内容重写、自动脱敏后继续沿用原哈希，禁止通过重写Git历史维持来源。

新verification.items保留当前定位和新事实history；迁移前历史通过origin_ref读取，不复制301条旧历史进新文件，不新造事实账。旧claim-review留在Git原件里，新文件成为可重建组合视图。已知隐私/原件不可访问时按现有隐私规则处理，不自动分享或修改绑定原文。新增事实从迁移后由当前helper真实登记。

## 4. 数据合同与单一权威

机器可读约定见[contract.json](acceptance-v1/contract.json)，用于开发规范而非可安装配置。字段允许表、枚举和跨字段规则以本方案为准，不以“实现时方便”为由增加第二判断账。

`verification.json` 根仅扩展：schema_version、feature_id、items、retired、acceptance_contract、acceptance；旧项定位/可编辑映射沿用现有字段，新增来源引用有明确定义。新acceptance包含：
- contract_id：本次准备的UUID；generation：非负整数且等于事件数。
- origins：迁移原件引用；全新需求为空。
- worlds：以世界输入摘要为key的不可变对象，共享存一次。
- events：有序不可变链，只有init/reconcile/fact/assessment四种事件。每项有seq、previous、kind、payload、at、actor、id；id是排除id后的规范JSON SHA-256。禁止NaN、重复key和未知字段。
不再单独保存可手改的frontier或第三份判断表；当前key/版本/有效判断在一次解析中由事件归纳，缓存仅限本操作。根items不是第二个支持判断源。

### 主张key与版本

key由helper生成UUID，不含产品含义；每个当前需求AC/影响行为一对一，重复文本不合并。gate不作为业务主张。

version_digest绑定：kind、该验收文本、所属需求statement/status/assumptions或影响statement/kind、对应来源aspect/批准basis、完整引用的决定/共享约束、实际mode/gates/coverage映射。**不包含兄弟AC、无关决定、history、进度或其他判断事件。** 所有被排除字段仍在全局变化清单或终态控制里，不等于忽略。
父陈述/assumptions变化可使多子项版本改变，这是保守设计；独立差异排除可明确证明某些新旧版本语义等价，再复用原判断。不能因为新旧版本号不同就强制物理重测，也不能因文本相同就直接相等。

reconcile根据精确来源/aspect/basis提出同key新版本；只有一对一且来源证据明确才维持key。歧义、重复文本、重排无法精确对齐则新key并记录前身。拆分/合并允许追溯关系，但不继承通过。退役必须保留未解决障碍与继承关系；产品确实删除范围需合法来源/批准依据，不得通过删行隐藏失败。

### 四类事件

init：记录合同、原件、初始主张集合及世界；不导入旧supported。
reconcile：记录前后活动集合、定位、版本定义、前身关系和权威依据；不产生支持。
fact：在对应row.history追加真实新事实，并记录该不可变条目的摘要引用；不判最终覆盖。
assessment：记录冻结请求、当前世界、独立返回、完整变化分类、重新判断的findings、分组reuse与pending、负向解除依据。当前状态/Verify/终审共同读此事件，不重复保存同义审查。

## 5. 世界输入与确定的判定算法

世界对象固定含：business（既有业务/输入身份）、authority（需求/决定/来源/intake/影响/任务/追溯的完整规范字段）、facts（原件/记录/最新障碍摘要）、claims（精确活动key/version/locator）、execution（选择与当前attempt身份）、environment（已绑定的环境范围）。源/证据路径和业务输入继续使用现有安全读取与受管目录链接边界，不因重构宽放。

世界中只排除本合同自己的判断/生成视图、原规则已明确排除的feature.status和任务status等进度字段；status_note、自由说明、新字段不自动排除。任务done、fix、模块与进程等控制项在终态每次校验，排除戳不代表免检查。文件路径变化/新增/删除、未识别结构都进入差异。原件缺失或当前输入无法识别返回unknown。

resolver流程固定：
1. 读合同/原件/事件链一次，校验所有key、引用、seq、hash；读取当前完整世界与必要控制项。
2. 按当前源生成活动集合，未reconcile或不一致返回PLAN_RECONCILIATION_REQUIRED。不能退回旧戳。
3. 没有当前assessment或world不同：显示待审及完整变化，不执行、不写入。负向事实继续显示，不仅显示stale。
4. capture以上次**最新assessment**为from，首次为null；冻结世界、generation、事实、活动集合和全部delta。from不能选更早有利的判断。
5. 独立返回必须覆盖每个delta和全部当前主张；每条delta分类affected/unaffected_with_evidence/unknown，列目标与实际调查依据。找不到关系不是unaffected。
6. 目标动作只能assess/reuse/pending，互斥且合起来等于活动集合。assess提供逐项完整required/observed/evidence/counterexample及verdict；reuse可成组，明确每个旧判断、新版本对应和变化排除证明；pending保持缺口。
7. reuse仅引用from中已有supported/approved_waiver及其完整事实；跨版本还需语义等价证明。与原facts/环境/包不符或出现最新障碍则拒绝，不能盲继承旧supported。共享关系改变可迫使多项重判。
8. apply再次核对冻结世界、generation和旧事件链；一次原子替换verification，存world与事件，不逐行新签事实。全负向可保存且不会通过。
9. compose以同一个resolver结果检查全部业务主张、全部必需gate、来源/任务/fix/设备/档案/生命周期；生成组合。任何unknown/partial/失败/缺授权阻断；并非行数齐全就交付。

### 消除终审捕获循环

capture只要求结构合法、原件可读和安全冻结，不要求“当前判断已全部通过”。失败/unknown可以被捕获并保存负向；不能以此绕过物理执行失败。实际交付才要求所有强制条件满足。旧文档“check全过之后才能capture”的限制对schema6停用；schema1–5原流程不改。

### 负向与最新结果

障碍从全部相关事件/来源与最新事实归纳，删指针、换key、retire或只改无关world不解除。障碍basis含主张/前身、涉及权威、事实及环境，不以整个world变化当作新证据。
只有明确的新事实覆盖原缺口，或合法新权威使原反例不再违反当前要求，才能由独立判断显式resolve barrier，保存原障碍及解除理由。较新必需gate失败/中断/缺终态永远不能借较早attempt。首批只使用现有当前完整attempt，不拼组。

## 6. 内部接口、命令和退出码

内部函数固定如下（名称可作兼容别名，语义不得拆出另一套当前性）：
inspect_contract(root, feature) → 兼容/准备阻塞，不写；
reconcile_claims(root, feature, resolutions) → 授权sync下的key/版本事件；
capture_assessment(root, feature) → 冻结请求（只读）；
apply_assessment(root, feature, request, review) → 一次事件提交；
resolve_claims(root, feature, snapshot=None) → 分层结果，不写不执行；
compose_delivery(root, feature) → 完整结果与可重建manifest，不改feature状态。

现有verification sync/record/run/status保留普通入口：schema6分别路由reconcile、真实fact、原check_runs执行及统一resolver。claim_review capture/check保留入口，新增内部apply动作；这不是新增用户/dev命令。prepare通过verification已有prepare类内部路由显式启用，不能由status/next猜测授权。

退出码：0操作成功或可读状态（并不等于产品通过）；1输入非法/并发/版本不支持，未写；2输入合法但验收/执行/证据未完成。异步执行失败与生命周期保留原记录。所有输出分开fact_status、applicability、coverage_verdict、blockers、delivery_eligible，并保留原版本/时间/原件ref。当前0.18.4状态字段保留旧模式原义，新模式输出有明确contract字段，不能暗改旧接口。

错误码固定见contract.json；不得依赖英文异常字符串来区分同步、缺原件、最新失败或冲突。

## 7. 读写者接管与旧路径退出

完整清单见[readers.json](acceptance-v1/readers.json)。基线静态分析有27个verification/claim_review反向import触达脚本，加archive_git直接文件枚举，合计28项检查对象；不是宣称28项都必须改实现。动态subprocess/字符串调用与参考文档仍需对照清单检查，不把import图当运行依赖完备证明。

必须改：verification与claim_review分派、统一新模块；validate/audit、status/inventory、closure、impact_results、stage_view与报告草稿等统一读结果。revise中的验证来源选择不能继续只看当前row.history[-1]。设备连续性读取当前验证失败须走统一障碍接口。
纯委托/容器枚举若已不自行判断，可不改代码，但要有schema6调用反例，不能直接从清单删除。

迁移后record/retain/carry/prepare-batch/apply-batch/adoption/旧annotation/correction等旧判断writer不得给schema6写正向；统一在写前返回LEGACY_WRITER_DISABLED并指明新路径。直接事实record仍经新合同工作。首批更正仅支持新增事实/合法reconcile；旧事实说明更正/脱敏如需绑定修改，明确不支持并保留阻塞，不复用宽松旧helper绕过。
旧版本解析/判断分支仅给未迁移schema1–5使用；对schema6不允许捕获错误后fallback。新项目启用后不再创建manual_scope_ref/evidence_digest/retained伪事实或另一份最终判断。新manifest只是生成视图，不能人工写supported。

历史完整判断保留Git原件。没有删除全部旧代码的承诺：遗留需求仍可按原版本读写，但新合同对旧写入的停用必须与新resolver同批完成，不另开“以后再删”任务。

## 8. 事务、迁移与恢复

新修改都先固定锁顺序：工作区execution_lock → verification计划锁。获取失败立即无写拒绝，不等待并列writer。遵守no_unfinished。捕获与提交前复读世界和计划；只是before/after身份保护，不声称阻止外部恶意写入或所有A→B→A变化。

prepare固定序列：
P1 只读盘点当前格式、原件Git引用、活动需求/执行合同2准备、版本/宿主、所有事实障碍与设备/模块义务；来源不支持或未提交就拒绝。
P2 显式授权后构建完整schema6候选；旧观察只转引用，旧独立通过不导入为当前支持。
P3 锁内核对原Git字节、世界和工作区未变；一次原子替换verification作为唯一合同切换点。初始为待审，迁移不能把provisional变complete。既有complete不作为迁移对象。
P4 生成verification.md和claim-review schema2视图。崩溃或磁盘失败只导致视图缺失/过期，可重建；权威不在这些视图中。
P5 首次独立assessment覆盖所有活动主张；旧事实可证明什么由该次判断确认。随后差异审查才可以reuse。

组合manifest固定schema2、kind=acceptance_delivery_manifest，包含feature_id、contract_id、generation、world_digest、active_claims、judgment_refs、required_gate_refs、guard_results、blockers、delivery_eligible、manifest_digest。字段全部由resolver生成、check重新验证，不以manifest本身证明语义。

切换前失败原文件完全不动；切换后失败停在合法schema6 pending，不让旧工具接写。若没有任何新事实/判断且全部受控输入未变，可显式恢复原Git对象；已有新事件/事实则禁止自动降级，必须保留原件、单独设计有损风险审查，否则仅停止当前认证。
新读者能力和项目启用分别核对。不能保证任意旧二进制尊重新标记；已知旧load_plan拒绝schema6，不代表直接写其他JSON的旧工具被技术上隔离。未知/混用宿主阻止prepare，不能宣传万能版本锁。

## 9. 开发任务与交付门槛

D1 固定规范/原件适配/统一解析：实现contract.json约束、schema6读取和Git原件验证；旧模式所有现有测试不改弱。
D2 主张对齐、世界/完整delta和resolver：不会遗漏新增字段、共享影响、同文案重复AC、前身负向；操作内只采集解析一次。
D3 独立capture/apply及组合：处理无循环捕获、全负向、分组reuse、跨版本等价和负向解除；一次原子写、幂等和漂移拒绝。
D4 全读者与普通入口接管、旧writer停用：28项清单逐项给出改动/委托/拒绝证据，所有当前性同源；不支持路径先拒绝。
D5 正反例、故障注入、等价旧/新对照与隔离安装：通过后再讨论正式发布与真实项目启用。
D1–D4不是四个可对外单独启用的合同；先完成隔离纵切，不让真实项目承受半套。源码脚本变化按AGENTS完整回归，调试先定向；文档修改不重复全套。

开发完成必须同时满足：机器清单全部安全反例符合预期；旧模式无回退；局部语义变化至少减少原事实重登记或重复完整判断之一；完整活动集合未缩小；所有旧writer退出；所有引用可恢复；故障后无部分绿灯；全过程新增成本公开。没有预设节省分钟/百分比。只少一条命令而多出更贵的全量审阅，不算已证实提效。

## 10. 对照、维护成本与发布边界

固定同一合成仓库/原事实/变化序列/质量范围分别跑严格0.18.4与候选，不改基线来制造差异。案例与预期见[cases.json](acceptance-v1/cases.json)，只是未执行规范，不是测试通过记录。局部UI、行为和共享变化都需包含，具体破坏必要条件验证拒绝，而非只匹配输出文案。

计入物理执行、原事实登记、独立审阅变化与原件、扫描/读取、序列化、迁移恢复和生成视图成本；等待/人工劳动与并行区间分开。模型usage不能直接当账单，缺失就未知。只采集既有日志/可选stage-cost，不增加业务必填成本表。

新增维护面已知包括：一模块及多读者接管、Git原件/主张映射、一个事件合同与manifest、跨版本兼容和负向传播测试。没有可靠人日/费用估计，本批不是小提示补丁。事件增长成本按实际测量，操作内复用、跨操作缓存/历史裁剪/数据库工程不在本批。

0.18.3/0.18.4局部提示有兼容价值，是否更贵的实测未知；新resolver接管后其重复schema6判断应删除，不以已有投入保留。若Git原件/合同2前提使目标项目无法接入，或统一接管不能维持质量，停止发布或缩小支持范围，不能偷偷改为历史全绿。

本方案定稿只确定开发边界，不授权支付、设备、服务器请求、业务迁移或重验旧需求。真实UI优化待候选正确性与接入条件满足后正常执行，不额外叠加“试点验收”；紧急业务可用现版，不被工具重构阻塞。

## 11. 草案问题的最终处理

F1 终审捕获循环：以安全捕获与交付资格分离解决。
F2 原始历史重复拷贝/新旧双判断账：迁移改Git原件引用，判断事件只存verification，manifest为生成视图。
F3 字段/错误/职责待实现时决定：以contract/readers/cases三清单固定；开发新增语义须回报范围变化。
F4 只改摘要却保留整体终审：首批强制D1–D4纵切，未接管不能发布。
F5 老项目自动模式混用：合同2仍项目级，盘点与显式授权是进入前提，不承诺单feature无影响。
F6 只删pointer或新key消除旧拒绝：事件链与前身障碍归纳，from固定最新assessment，解除必须针对原缺口。
F7 保留旧writer永久叠加：schema6同批拒绝旧活动写入，旧代码仅服务遗留格式。
F8 过度宣称架构科学/收益：本轮未执行候选，无法保证零漏验或固定收益；实现失败和成本更差同样留存。

结论：开发接口、支持/拒绝边界、任务、反例和停止条件已固定，无需再开展一轮泛化架构讨论。获准开发后按D1→D5推进；发生具体反例才修订相应约定。正式运行版本和日常安装仍0.18.4；候选源码已实现，实际执行范围见[核验记录](../evaluations/2026-10-20-acceptance-v1-candidate.md)，不将设计规范本身当执行证明。
