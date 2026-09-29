# GAP-20：0.5.29 失败返回停止规则窄复检

2026-09-29。**规则已补强，临时原生入口的返回阶段复检通过；尚未安装或重跑新版完整双Worker链。**

## 问题与最小修正

[0.5.28个人原生失败演练](2026-09-29-worker-failure.md)已知一个Worker failed后，总路由仍调用integrate验证拒绝。helper正确阻断、没有候选，但路由没有严格停止。0.5.29仅修改build-strategy/parallel-build的运行说明：先检查返回资格；失败、阻塞、缺失、无效或过期直接保留并停止，不调用集成作拒绝探针。单独明确请求的负向探针属于独立诊断，不能从“演练/验证”措辞推断，也不推进原尝试。

无helper、命令、记录结构、自动重试或调度改动。使用指南流程图已同步。

## 夹具与实际执行

原计划复用上次真实返回，但0.5.29 helper preflight正确拒绝旧尝试：`review inputs stale`。0.5.28个人helper对同一旧尝试仍返回current；verify-handoff输入摘要包括Skill文件，因此规则更新也是输入变化。旧记录与摘要未改写。

为测当前规则下的失败分支，维护者创建一个**新的返回阶段夹具**：克隆原干净合成主项目与已审记录，临时0.5.29 helper正式prepare，按原任务归属在新detached工作区应用原合成补丁，再正式finish执行原检查器。没有重新编码或派发Worker，不能称作新版Agent完整开发演练。T-UP功能7项通过、固定模拟探针失败，结果failed；T-LOW 7/7，结果ready。新preflight通过、封印/补丁/日志/worker状态均绑定当前尝试。

随后全新Claude会话使用临时原生 `/featrace-gap20:dev develop FEAT-001 --parallel` 入口，启动发现清单包含该入口和0.5.29插件。它实际读取临时build-strategy/parallel-build、新run.json、双方真实patch/log/result，核对冻结资料与当前工作区，再决定下一步。提示没有泄露期望答案或要求“不调用integrate”，只限定现有尝试接续、不重新开发。工具轨迹没有单独Skill调用或读取SKILL.md，所以本轮仅证明已注册临时入口下**实际读取新references后的返回阶段采用**，不证明完整总路由加载链；个人/dev仍0.5.28。

## 实际核对

|项|结果|
|---|---|
|返回阶段决策|发现T-UP failed，停止并保留，不把功能7项绿转换成ready|
|integrate调用|0（以实际工具调用为准）|
|prepare/finish/新Agent调用|接续期间均0；夹具预先准备的操作分开记录|
|候选/集成报告|均未产生|
|单个成功结果采用/降级/完成提升|均无|
|新主项目/权威记录/HEAD/暂存内容|前后不变|
|新尝试/双方worker/return/patch/log|前后不变，维护者preflight与封印/状态/哈希复核通过|
|原0.5.28主项目与失败尝试|前后不变|
|个人安装及临时runtime|前后不变；个人仍0.5.28|

会话只额外写项目外assessment.md。墙钟65.001秒，CLI标价估计0.451137美元，非账单/收益对照。实测失败探针为夹具故障，不是产品算法缺陷。指令与事后核查不是权限沙箱；一次样本不能证明所有宿主或全部failed/blocked/missing/stale分支的普遍采用。

## 证据与后续

[脱敏核对](evidence/2026-09-29-gap20-return-gate/audited.json)及同目录真实返回、补丁、检查日志、夹具prepare/finish/preflight输出、assessment和逐文件哈希。原始流含个人启动配置，仅留临时目录 `/private/tmp/featrace-gap20-replay-0529-orwgp4u6`，未入库；未提交业务项目的工作流目录。

GAP-20记为“0.5.29规则补强，返回阶段隔离采用通过”，不记个人安装验证完成或正常开发全链回归通过。源仓未提交/推送，个人仍0.5.28。下一步收口发布安装，再继续PRD过期/越界隔离或自然需求成本验证，不扩展并发/调度。无运行Python脚本变更，未重跑此前267项测试；router/Build/Verify三个quick_validate通过，git diff --check通过，测试runtime与当前源码逐文件一致、两份证据清单哈希及新增本地链接通过。
