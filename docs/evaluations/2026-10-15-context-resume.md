# 新上下文隔离接续演练（0.13.6，2026-10-15）

## 目的与执行边界

用户授权“新会话接续演练”：不给此前对话，仅按持久资料恢复当前事实、来源、未决项和下一步。使用1个fork_turns=none的Codex新上下文代理，对2个隔离合成项目进行只读核对；不是原生Claude会话、实际业务的压缩恢复、Test Skill准确率对照或全链开发演练。没有执行业务测试、修改权威记录、提交/推送、设备操作或更新安装。

给代理的只有两个项目路径、FEAT-001/T-FOCUS身份、Skill位置、前次starting-view位置和只读/精确临时写范围；没有给预设答案、怀疑点或原主会话。两个项目在同一个新的审查上下文中查看，故不是两个独立样本/双盲试验。代理没有写任何报告文件，结果由其最终回复提供，维护侧在此留档。

## 合成输入与维护侧期望

由既有StageViewTests生成，项目及.sources/JSON均为合成，不入业务仓或Git。相关完整条款R-1要求abc→ABC，原来源可读。旧报告写All checks passed；canonical历史先passed后unavailable；选中的unit实际只断言1+1==2。另有共享approved但缺chosen内容的决策、全局待决D-PENDING、任务和traceability不一致，保持这些未知可见，而不把夹具写成可交付。

- alpha：starting-view与当前输入一致，D-PENDING关联其他需求，但整功能仍有未决；当前R-1 unavailable。
- beta：留同样的旧视图，之后将D-PENDING改为关联R-1并改问题文字。应拒绝旧视图、读取当前权威；旧结果同时stale。

夹具不是完整有效的业务开发准备，缺task/regression review及质量报告；发现这些并不证明真实项目流程误阻塞。演练只评估能否恢复和辨认冲突，不能因“都被挡住”推导对正常ready场景也能推进。

## 代理实际结果

| 检查点 | alpha | beta |
|---|---|---|
| 起点有效性 | helper返回STAGE_VIEW_CURRENT | helper返回stage view stale，未修补旧快照 |
| 当前状态 | provisional，R-1 unavailable，其余4项not_run | provisional，当前R-1 stale，当前D-PENDING直接相关 |
| 旧报告和历史 | 指出旧All checks passed与当前撤回不符，未拿旧pass复活 | 同样保留缺口，不拿旧视图决策代替当前记录 |
| 真实测试范围 | 实际算术断言不能证明大写转换；代码仅占位内容 | 同左，没有真的运行测试 |
| 任务/权威恢复 | 指出T-FOCUS、T-1追溯矛盾、共享决策缺内容，未编造approved的选择 | 同左，并指出先解当前相关产品选择 |
| 可接续步骤 | 修复关联/澄清范围及Scope，执行需另行授权 | 从当前权威重建起点、解决相关选择后Scope→Build/Verify |
| 版本身份 | 源码0.13.6；没有安装清单，所以不声称安装版 | 同左 |

维护侧前后比对：两个项目的业务及canonical文件SHA均不变，HEAD等于冻结视图code_revision，允许result目录没有新文件；[核对结果](context-resume-0136/integrity.json)。这不声称对整个机器或全部.git内容做过审计。

## 读取与成本边界

代理报告实际读取两个starting-view、多份当前canonical JSON、原来源、2个代码文件、门禁配置、旧报告、Skill入口及5份参考说明，还读取部分辅助脚本源码；没有全部历史/全仓扫描。其read清单为代理自报，不是宿主精确I/O统计；工具内部哈希读取不当作语义阅读。

它仍回读较多当前记录，没有同输入无视图对照，也没有本次可核验的实际计费Token/费用或完整耗时，因此都保持未测量。不能用[尺寸探针](2026-10-15-context-reading-audit.md)的字节大小证明这位代理少读、花费更低或真实压缩不丢事实。两例有效恢复不等于可自动切换所有阶段上下文。

## 重现与下一步

合成设置脚本：[setup_fixture.py](context-resume-0136/setup_fixture.py)，从维护仓运行：`PYTHONDONTWRITEBYTECODE=1 python3 docs/evaluations/context-resume-0136/setup_fixture.py`。脚本在系统允许的临时区创建隔离项目，输出位置及尺寸；各项目的scratch被Git忽略。它只生成输入与静态尺寸探针，不自动派Agent，不伪造审查或跑业务检查。完整尺寸结果见[metrics.json](context-resume-0136/metrics.json)。维护侧已实际运行入库的设置脚本，退出0，重现全部归档字节测量；这次重现没有再次派Agent。

后续优先评估Verify说明的条件加载、task/regression历史摘要；必须保留完整父条款/未知/失败/当前计划检查/出处及全量绑定。日常CC固定0.13.6，本轮不改runtime，不新增接续权威文档或context百分比门禁。第二阶段仍按[真实需求基线](../reviews/2026-10-15-phase-two-baseline.md)观察。
