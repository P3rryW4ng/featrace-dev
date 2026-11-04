# 2026-11-04 F05反馈：局部评审、定向更正与走查精简

对象：CC返回的0.30.3真实F05样本，以及维护侧直接核对的zymix-core固定6edee22c源码/3份contract6记录。Skill基线275e4bf、正式及安装0.30.4。用户批准按顺序处理；本轮源码候选未发布安装。程序和自然Agent证据分开，第二阶段已通过状态不变。

## 1. 直接核对与归因

主任务wallet-f05-withdraw首次回执为2026-11-03T16:35:53.501927+00:00，6项支持；后两个展示任务5项、1项支持。三个任务确实使用当前同内核字节的contract6。主任务证据要求使用static_analysis+command，有实际执行事实，不能单凭缺producer就判测试未执行；但原结果未按原生产者保留、部分被覆盖后，精确用例和时间无法重新核实。CC关于现存XML/执行窗的逐条补核属于转回报告，维护未将其升级成重新执行或逐份独立验真。

F07“返回自动选中新账户”在原计划有承诺，证明范围被限定为代码/单测、端到端依赖F07；不能笼统说原计划把它全删了。F11在实际F05文档验收中出现，且设计/依赖段写随F11；原主任务直接排除、首次结项前缺明确范围批准。后来用户批准随F07/F11验收，不能倒填首次授权。原计划并无独立F11标准，不能直接把不存在的ID传defer，也不能把整个已实现提现页一并延期。后续更正需补齐原验收对应关系、独立未交付承诺与存活交接，再依法登记，保留原标准/判断。

主任务以debug mock/release传输错误为由不独审，仍实现了将用于真实路径的资金映射/重试/结果处理。mock减少当前资金暴露，不自动消除代码风险；后两个展示任务自评不因此被否定。Android profile已要求按需加载及producer，遗漏属Agent执行；有必要补清结果覆盖前保留和增量走查时序，不用新审批或档案兜底。

## 2. 实际独立源码评审

用户明确批准局部独审，实际由Codex collaboration新上下文/root/f05_funds_review执行，固定上述HEAD。只读必要源码/测试/实际F05资料，无文件写入、构建、测试、网络、设备操作。返回1项确认P2：提现CREATED在submitWithdraw经payoutOutcome为Processing，但order沿用payInOutcome为Failed。当前mock金额21会保存同一CREATED状态，已有确定的源码契约反例；AwaitWithdrawResult遇到该Failed会终止、不给受理事件，确认VM按失败收尾。位置为FundingRepositoryImpl:48、FundingMapping:157/165及AwaitWithdrawResultUseCase:37；不复制业务源码到公开维护仓。

当前mock普通提交即退出、没有提现SCA场景，未证明标准UI已触发、真实GetOrder归一化或真实资金损失；没有确认P0/P1。金额回退与当前F05口径相符，真实v2字段/金额币种关系仍未知；同quote幂等键和一次retryable重试有结构/现有单测依据，不等于真实服务端去重。USED无单号对账能力与真实SCA仍是限制，局部评审不把它们洗成已验证。

最小后续是区分正确查单交易类型/状态语义，核对同笔提现提交与查单一致；不把所有充值CREATED一概改成受理，不跑全部UI。本轮未开发业务修复。

## 3. 已完成的定向更正和外部说明

维护直接通过实际安装的task_workflow.py correct开启wallet-f05-withdraw更正94eecfdf8005451ab3d74c37b7c5ffea，affected为domain/data/confirm-page/withdraw-page。当前state=correcting，原回执/事实/失败完整保留，未重签观察或回填producer，未强行重新结项。assembly/gates原判断未被清除，但这不证明其对当前HEAD仍认证。两个后续展示任务的JSON前后SHA256完全一致。

独审维护摘要作为主任务受管附件88ee4a4e19364b56b6d27d0a74e900fd保存，明确是摘要、真实子上下文出处、非逐标准验收provenance；没有将静态问题伪造为新runtime failure。现有F05文档追加必要交接：真实后来延期、F07已由CC报告承接/F11无单无负责人、P2未修复及切真前条件。没有为F11建占位单。业务源代码和原有工作区改动未动，未提交业务资料。

GitLab !267已通过现有登录浏览器仅替换两处描述并保存读回：api排序只有脚本对比；区分当时XML检查、Gradle日志和已覆盖的报告。未追加未经独立核对的CI新结论。更正截图仅留本地，不提交维护仓。

云效登录过期；用户明确选择“先保留本地，稍后由CC同步”。本轮没有发送云效评论或修改产品状态。CC之后同步OGFR-10178，内容取现有F05文档交接节，不能说问题已修好或任务已重新结项。

## 4. 过度走查的因果与取舍

CC补核确认第2轮只因余额面板改动而全量重走，第3轮因提前恢复干净包后重新打补丁再全走。构建6次的单项耗时不全，不能宣称精确节省；3轮记录约375/382/383秒，来自用户转回报告，不当维护实测或相加算净工时。

第2轮其他观察能否复用仍需真实源码/补丁/状态/产物与证明范围判断，不能仅凭“改面板”自动沿用。设备恢复本身不是业务失败或全量复测理由，但真实current要求/相关输入漂移/产物丢失不能被绕过。32附件接近上限来自重复轮次与重复截图，不提高容量。CC称约7份足够是本场景建议，不固化为截图额度，也不凭文本日志证明对齐/颜色等视觉目标。

## 5. 候选Skill改动与兼容

仅修改现有Android profile与task-workflow参考指引，usage说明同步现有流程图节点。脚本、CLI、合同6、15文件数量及安装都不改；无需旧任务迁移。

- 测试验收所用产物在后续运行覆盖前选定attach并关联真实producer及生产时间，避免保存全部报告；已有结果仍按来源采用，缺失不伪造、不自动全套重跑。
- 修复按因果影响增量走查，保留适用原观察；未知关系先调查。日志与视觉截图按真实证明需要选择。
- 恢复补丁/设备之前保存必要输入及目标证据；尽可能先完成目标相关核对再还原，恢复行为另记。拒绝先诊断，非默认整轮重装重走；不承诺还原后所有历史结果必仍适用。
- 下一受保护动作前合并刷新相关计划，不按每个文件/层强制登记；mock不自动豁免真正高风险逻辑独审，延期门槛须落到存活问题位置。

未采用新增永久档案、自动XML全扫描/保存、全局UI套件、强制rerun-tasks、扩容、独立恢复Agent、每层审批。现有producer/attach/correct机制够用；本轮没有新内核缺陷被证明，不用补丁掩盖业务映射错误。

## 6. 本轮实际验证与未完成事项

6项既有隔离测试实际通过，首组4项1.419秒、次组2项1.390秒：EvidenceCoreTests.test_observed_test_result_binds_actual_producer_and_original_time、test_old_xml_cannot_be_assigned_to_later_invocation、test_new_compatible_observation_does_not_stale_selected_old_fact、test_runtime_requirement_cannot_be_supported_by_static_or_compile_command；TaskCorrectionTests.test_correction_keeps_receipt_and_only_requires_selected_reassessment；FullReplacementTests.test_owned_attachment_copy_is_collected_but_original_is_preserved。未修改程序或测试，不重跑343项。

维护者场景走查：XML后续覆盖前保留；旧XML不能归新执行；面板修复不推出全页业务重测；恢复设备不充当新包验收；真正current条件变化仍需相应核对；mock资金逻辑独审发现不能用通过测试覆盖。这是指引/程序边界核对，不是新版本Agent前向遵从试验。

仍需业务侧：定向解决P2后验证查单一致；按真实后来批准处理F07/F11验收映射及defer；重新判断本次更正范围并close，不能补造被覆盖测试产物或全量重验父需求。云效由CC登录后同步。维护源码候选验证完成后本地提交，推送/发布/安装另按用户明确指令执行。见[机器摘要](../evaluations/f05-feedback-20261104.json)。
