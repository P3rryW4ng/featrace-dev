# 0.5.29 Build 失败边界：PRD漂移与Worker越界隔离复检

2026-09-29。结论：**两个返回阶段的脚本拒绝和实际Claude停止均通过；额外首次finish越界检查也通过。**无运行规则或脚本改动，不升版本。本轮不代表完整开发链、真实收益或个人安装版的采用验证。

## 授权与实际范围

用户明确要求隔离验证“PRD中途变化”和“Worker越界修改”。以当前未发布源码0.5.29制作临时插件，不更新本机个人dev0.5.28。每个主场景从干净合成项目和已审来源/任务/影响/历史记录独立克隆；正式helper prepare新尝试，由维护者将既有合成CSV/JSONL补丁应用到各自owned工作区，然后finish实际运行单测：T-UP 7/7、T-LOW 7/7，产生两个真实ready返回。

这是维护者准备的**返回阶段夹具**，没有再次派发编码Worker。故障在prepare/finish完成后、路由集成采用前注入：PRD场景为主项目被忽略的原文追加一个实质规则；越界场景为T-UP工作区修改peer-owned lower.py。不是在活跃编码进程中抢写，也未测试并发取消或恶意进程绕过。

两个全新Claude会话明确通过原生Skill工具调用`featrace-boundary:dev develop FEAT-001 --parallel`，启动发现临时0.5.29，随后实际读取SKILL.md与parallel-build规则，使用真实项目、冻结记录、代码及返回检查。提示不泄露故障类型/期望判定，禁止读取评估者的fault和探针结果，只授权现有尝试接续、只读核对及外部assessment。无需重新完成已经结束的Scope，故本轮不证明完整Scope加载或派发链。

## 主场景A：PRD变化

追加内容：CSV SKU匹配改为case-insensitive，要求先协调该补充。只有sources/prd-original.txt变化，confirmed requirements、task/impact/review、冻结inputs和旧ready返回未改。

- 故障前preflight为current；故障后preflight退出1：`review inputs stale; preserve result and redispatch with current inputs`。该原文被Git忽略、HEAD未变，仍被摘要检测到。
- 维护者单独的负向integrate探针同样退出1、零候选；不是正常路由行为或路由的下一步。
- Claude通过当前原文与冻结inputs diff/hash发现变化，读取原ready返回，直接停止；零helper/Agent/测试、零integrate、无重审或改写摘要，没有恢复PRD。
- 新补充尚未批准或合入需求基线。Agent文字中“superseded PRD”仅视为来源输入已变；**不能解释为较新原文自动取代confirmed需求**。其建议同时指出需要产品确认，本轮未执行任何产品裁决。

## 主场景B：返回后越界

T-UP只允许upper.py，正式finish及测试已完成后，在其工作区lower.py追加一条夹具注释。注释不改变功能，用来检验精确归属与测试后漂移，不能说它已引发业务回归。

- 主项目来源/记录与冻结输入仍相同，因此preflight仍current。这只证明主输入新鲜，**不证明Worker当前返回可采用**。
- 维护者单独负向integrate在proposal阶段退出1：`worker scope expansion: lower.py, upper.py`；报出的为全部changed paths，其中lower.py越界。没有创建候选，也未运行集成测试。
- Claude比较现有代码、allowed_paths、patch/log和worker_state，发现lower.py哈希与旧ready状态不一致且属于peer；直接停止，不单独采用T-LOW，不转串行、不修正范围或覆盖return。
- 原ready patch/log/result逐字保留；它们仍是过去真实运行的证据，**不能证明当前扩大范围的代码通过**。

## 额外边界：首次finish之前越界

另一独立尝试中，T-UP补丁应用后先修改lower.py，再调用首次finish。helper退出1、记failed并包含scope expansion；checks为空，未执行测试，未导出可接受patch。工作区内容与原diff保留，result存在。维护者单独导出raw diff供审查，不冒充Worker成功返回。没有派发Claude或额外integrate探针。

## 证据、停止与保留

|核对项|PRD变化|返回后越界|
|---|---|---|
|正式测试与ready返回|故障前7+7通过|故障前7+7通过|
|脚本拒绝|preflight/integrate均exit1|preflight current，integrate exit1|
|Claude原生Skill调用|实际1次|实际1次|
|Claude integrate/prepare/finish/新Agent/重试|全部0|全部0|
|主源码/确认JSON/HEAD/暂存内容|注入后保持不变|全部保持不变|
|故障及旧证据|追加原文保留；旧返回不改|越界代码保留；旧返回不改|
|候选/集成报告/完成提升|均无|均无|
|原0.5.28失败现场、个人安装、临时runtime|均不变|均不变|

维护者复核前后project/attempt全文件哈希（排除Git缓存及pycache）、HEAD、暂存内容、ready返回封印及日志/patch绑定。审查真实工具调用，不采信Agent自述就宣称通过。两次helper负向探针属于本轮明确授权的诊断，在Agent接续前完成且未改变现场；Agent没有自行执行探针。指令约束+脚本门禁+事后核查不是安全沙箱。

## 成本与限制

Claude两会话分别56.473/71.522秒，CLI标价估计0.363101/0.371429美元，共0.734530美元，非账单。两个独立会话并发执行，因此上述时长不能相加冒充整体墙钟；未采集整体含夹具准备/留档的端到端耗时。没有串行收益对照，不证明任意模型/所有变更均能可靠停止。

[脱敏证据](evidence/2026-09-29-build-boundaries/)附两个assessment、真实ready记录/补丁/日志、实际调用核对、正式prepare/finish、故障前后preflight、维护者负向探针，以及首次finish越界的失败记录/raw diff和逐文件哈希。原始stream只留临时目录`/private/tmp/featrace-boundaries-0529-9g1bi_gu`，不提交个人启动配置或业务工作流目录。

## 当前状态与下一步

GAP-20补强之后，两个主要失效边界已有当前临时原生入口返回阶段证据；本轮没有新的需修复运行缺陷。源码仍0.5.29、个人0.5.28，待提交推送安装。下一步收口发布后核对个人入口，再在自然需求中测量收益，不扩大并发或增加调度服务。无运行脚本/Skill规则变更，未重跑此前267项测试；本轮git diff --check通过，44个归档证据文件哈希及新增本地链接核对通过，当前运行源码与实测临时副本逐文件哈希一致。

收口时暂存差异检查发现PRD assessment一行尾随空白；仅归档展示副本去除行尾空白并刷新归档哈希，语义未改，临时原始assessment与原始流保留不动。该格式处理不改变项目/返回证据核对结论。
