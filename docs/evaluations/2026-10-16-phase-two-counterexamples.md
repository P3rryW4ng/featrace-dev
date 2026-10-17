# 第二阶段固定反例与现有覆盖盘点（2026-10-16）

本轮仅核对源码断言和已有验证记录，没有运行测试、派Agent、访问业务仓/设备或改变门禁。用户授权的是等待CC期间的维护准备2/3；本页不是新增测试集、运行规则或开发授权。正式已提交基线bf348c9/0.13.6；本地0.14.0及其新增测试是未提交候选，单列，不能算本方案已批准。当前队列见[ROADMAP](../../ROADMAP.md)，批次见[收敛方案](../reviews/2026-10-16-phase-two-final-plan.md)。

后续截点：用户之后批准B1，CE-02/03/04相关自动检查/审计边界已补[19项断言及完整回归](2026-10-16-b1-check-identity.md)。下表保留盘点时状态；不是所有入口、执行隔离或结项恢复都已完成，当前队列仍见ROADMAP。

## 阅读方式

下表CE编号只是本页反例索引，不是新增GAP、任务或第二问题队列。覆盖分为：已有局部断言、机制缺口、真实行为待验、候选局部断言。链接对应测试源码；“存在断言”不等于本轮通过，不等于覆盖所有入口。既有执行结果从[验证索引](../validation.md)回读，不能把历史测试数算成本轮测试数。

## 固定反例与正向对照

| 索引/需求/GAP | 反例及应有结论（后续验收目标） | 已有测试/证据 | 当前不足及最小补充候选 |
|---|---|---|---|
| CE-01 FT-01；GAP-05/14 | 测试后提交业务变化，旧报告应失效；纯流程提交不无故重跑 | [test_delivery_audit.py](../../tests/test_delivery_audit.py)：test_report_tracks_selected_fix_test_and_current_revision、test_mixed_workflow_and_project_commit_stales_quality_report、test_workflow_only_commit_does_not_stale_quality_report | 已有两侧局部断言；不代表所有工作区/忽略输入被覆盖 |
| CE-02 FT-01；GAP-05/38 | 暂存、未暂存、未跟踪代码变化，各入口不得对同一验证对象矛盾放行 | [test_scan_contract.py](../../tests/test_scan_contract.py)：test_unregistered_tracked_worktree_change_requires_review、test_untracked_worktree_change_requires_review；[test_verify_handoff.py](../../tests/test_verify_handoff.py)：test_dirty_start_supported_but_later_tracked_untracked_and_ignored_changes_stale、test_new_commit_and_index_only_changes_stale | 基线/交接已有断言；质量报告snapshot主要清单/登记文件/HEAD，缺跨入口同输入一致性矩阵。需固定内容、索引及未跟踪变化分别核查，不重复重建已有交接绑定 |
| CE-03 FT-01；GAP-14/28 | 检查期间输入变化，命令退出0也不能认证最终输入 | [test_delivery_audit.py](../../tests/test_delivery_audit.py)：test_check_cannot_claim_final_snapshot_after_manifest_changes；[test_verification.py](../../tests/test_verification.py)：test_drift_during_command_cannot_pass；[test_revisions.py](../../tests/test_revisions.py)：test_check_detects_requirement_drift_during_execution | 已覆盖具体变化，需补报告入口普通源码/索引变化，不能把manifest反例当所有对象已覆盖 |
| CE-04 FT-01/04 | 忽略输入、缺文件、符号链接、子模块不能默认为已验证 | [test_verify_handoff.py](../../tests/test_verify_handoff.py)：test_unbound_ignored_read_is_rejected_then_explicit_binding_works、test_missing_extra_becomes_available_and_stales、test_submodule_is_explicitly_unsupported | 显式绑定/拒绝已有；环境、SDK外部目录、设备状态并未通用冻结。最小验收为明确缺口且不误放行，不要求自动收集全部机器状态 |
| CE-05 FT-02；A71 | A的门禁选择不能用于B；未绑定不得执行 | [test_verification.py](../../tests/test_verification.py)：test_unbound_or_other_feature_gates_stop_before_execution；[test_delivery_audit.py](../../tests/test_delivery_audit.py)：test_selection_is_bound_to_feature_and_executed_commands | 已有静态错绑定拒绝；不等于A/B交错执行结果能同时保存 |
| CE-06 FT-02 | A开始→B执行→A返回，不得覆盖/借用；不安全可明确拒绝 | [project.py](../../skills/dev/core/scripts/project.py)写共用project-baseline/quality-report.json；verification锁按feature | 机制缺口。未来做两需求受控交错，确认结果身份/保留和锁范围；不建设调度队列 |
| CE-07 FT-02；GAP-25 | 同需求通过→失败→重试，不能挑旧通过遮失败；命令未产报告不得借旧绿灯 | [test_verification.py](../../tests/test_verification.py)：test_failure_history_and_removed_items_preserved、test_stale_quality_report_cannot_be_reused、test_failed_and_unavailable_commands | 行历史有局部断言；运行器报告仍单份，缺稳定attempt身份与不可混用的独立结果。不得说所有执行历史已可靠保存 |
| CE-08 FT-03；GAP-24/28 | 条件不全却标complete，check必须拒绝；路由也不得将过期完成说成有效交付 | [test_workflow.py](../../tests/test_workflow.py)：test_new_complete_feature_requires_current_delivery_audit；test_closure_route_is_read_only_and_waits_for_tasks | check保护已有；后者还明确断言status=complete时直接返回COMPLETE，因此是当前行为定位，不是“完成当前性”验收。后续须区分历史完成与当前有效 |
| CE-09 FT-03；GAP-22/23/27 | 报告/登记/状态各步骤前后中断，保留待恢复，不误报有效完成 | [test_revisions.py](../../tests/test_revisions.py)：test_verify_records_version_code_and_evidence_without_auto_complete；现有原子单文件保存与GAP-22回读演练见验证索引 | 有单步保护，无整段结项故障注入/恢复合同。下一批才设计关键点中断及恢复，不将单文件原子写说成整个结项事务 |
| CE-10 FT-03 | 同输入重复收尾只登记一次；别人修改后恢复不覆盖；正向恢复可完成 | [revise.py](../../skills/dev/core/scripts/revise.py)有保存前原文核对；[test_evidence_carry.py](../../tests/test_evidence_carry.py)：test_concurrent_other_row_failure_is_not_overwritten、test_nested_helper_mutation_refuses_busy_lock | 局部helper已有冲突保护；交付整体幂等及恢复仍缺，不能复用carry锁测试冒充结项恢复 |
| CE-11 FT-04/10；GAP-28 | partial/漏行/无授权豁免不能通过，输入变化使复核失效 | [test_claim_review.py](../../tests/test_claim_review.py)：test_missing_partial_and_supported_review、test_changed_source_or_result_invalidates_review、test_missing_row_and_waiver_without_matching_result_rejected | 结构拒绝已有；自填reviewer不证明独立。v6真实新上下文派发及语义准确性需独立事实，不可在fixture填名字就宣称通过 |
| CE-12 FT-01/04；GAP-26/32/37/38 | 旧pass后有失败/撤回，不得复活；保留原测试版本；相关/未知拒绝 | [test_evidence_carry.py](../../tests/test_evidence_carry.py)：test_full_parent_change_and_latest_failure_do_not_revive_pass、test_withdrawal_cannot_be_revived、test_explicit_record_revision_carries_and_keeps_test_identity、test_repeat_partial_review_stays_stale_without_writes | 已有局部保护，继续保留；它不证明依赖清单完整或旧包实际身份 |
| CE-13 FT-01/07；GAP-32 | 父条款只补其他AC的推断说明，当前AC/代码/观察不变，须能有据判断而非只好重测 | CE-12的父条款反例实际改statement，属于真正含义改变；本次OGFR-8024用户转交CC回报：R-3只变assumptions仍拒绝R-3:1/2 | 新边界待设计：不能取消全部父条款保护或按字段名免审。正例仅相关性审查有据保留；反例为assumptions改变当前AC解释/共享条件则受影响或未知。本轮不改工具、不执行该反例 |
| CE-14 FT-04/07；GAP-39 | 纯描述/持久证据路径纠正不冒充重测；不能改coverage/status或救活stale | 未提交候选[test_result_corrections.py](../../tests/test_result_corrections.py)：test_stale_pass_stays_stale_with_pending_decision、test_historical_correction_does_not_revive_later_withdrawal、test_partial_review_and_forbidden_field_refused_without_writes | 候选局部断言与既有446回归记录单列；CC回报6条已采用、四轮审查，其中三轮措辞返工。真实效果仅为转交回报，净收益未证明，不自动批准候选 |
| CE-15 FT-05/07；GAP-13/27 | 新上下文必须识别撤回/过期/未决，不信旧全绿报告；正常解阻也应能继续 | [接续演练](2026-10-15-context-resume.md)：1个Codex新上下文只读核对2个合成项目 | 已有负向辨认证据；不是2个独立Agent，也没证明正常ready→开发闭环、跨机完整资料或真实CC压缩恢复 |
| CE-16 FT-07；GAP-06 | 历史增长不全文透传；当前未知、失败、完整相关条款和回读出处不丢 | [test_stage_view.py](../../tests/test_stage_view.py)：test_task_projection_preserves_full_parent_shared_rules_and_global_unknowns、test_unrelated_failed_claim_is_globally_visible_without_loading_its_history；[读取审计](2026-10-15-context-reading-audit.md) | verification旧历史已省略，task/regression仍全文透传。需同输入内容反例和实际读取比较，不拿字节探针当Token收益 |
| CE-17 FT-12/04；GAP-28/30 | 编译/未触发/近似模式不算完整业务通过，负向断言需观察窗口和观察者 | [test_verification.py](../../tests/test_verification.py)：test_run_records_actual_commands_without_passing_ui_items；[CASE-07](../reviews/2026-10-15-case-07.md)保留toast窗口/开户模式缺口 | 结构分责已有，任意测试语义不由脚本自动证明。OGFR-8024的三星失败恢复是CC报告真实缺口，不能以API35未复现替代；不能用工具误阻塞掩盖它 |
| CE-18 FT-05/07/10 | 只读/停止不触发写；相同阻塞不循环；支持条件齐全的正向接续 | [test_workflow.py](../../tests/test_workflow.py)：test_closure_route_is_read_only_and_waits_for_tasks；[orchestration](../../skills/dev/core/references/orchestration.md)有不循环/尊重只读规则 | helper局部只读不证明Agent整链遵守；需以后真实宿主同时覆盖blocked与ready，不只验证所有例子都停下 |

## 选用规则与不应重建的部分

- FT-01优先补跨入口一致性及普通源码/索引变化；现有交接快照、impact、安装哈希继续复用。
- FT-02补需求/attempt独立结果及安全竞争；错feature绑定拒绝与失败行留史继续复用。
- FT-03补整体恢复、幂等、当前有效性；保留已有报告回读、check/audit、v6复核，不重造需求状态。
- 既有合法拒绝与正向对照一起保留：真实语义改变拒绝、撤回不能复活、纯流程提交可不重测、正常有效输入可通过。不能以“所有例子被挡住”证明改进有效。
- 后续开发按受影响组选择定向测试；运行脚本变更仍遵守AGENTS的完整回归要求。只改本文不运行旧测试，不制造新的passing计数。

## 本次CC回报的成本与可靠性线索（非维护侧独立业务核验）

用户转交OGFR-8024核对：六条勘误四轮审查、其中三轮为措辞返工；冻结后修改门禁使六份快照失效并重新核对；R-1:3范围纠错引出重复检索/登记；grpc两次门禁含一次既有熔断测试失败。分段耗时未测量；用户说“已运行约2小时”不等同净Agent时间、人时或账单。R-3合同阻断与B-16实际漏验分别记录；缩小门禁是否合理需要范围证据，不能将所有重跑都叫无效检查。本轮不为CC新增任务或改变其本次授权。

这份盘点只证明找到了已有断言和缺口，不关闭GAP、不宣布第二阶段通过。指标口径见[最小指标字典](2026-10-16-phase-two-metrics.md)。
