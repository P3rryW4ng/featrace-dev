# B1共享自动检查输入身份（2026-10-16）

授权：用户明确“先实现B1”；仅维护仓实现/合成测试/文档，不进入B2～B4，不安装、提交、发布或推送，不操作CC业务仓/设备。依据[FT-01/02设计](../reviews/2026-10-16-ft01-ft02-design.md)和[反例盘点](2026-10-16-phase-two-counterexamples.md)，架构边界见A89。保留已有未提交0.14.0勘误候选，既有测试也参与全套回归，不把它视为本次新授权采用。

## 实现范围

新增check_identity.py读取Git根、HEAD业务树、index和实际tracked字节、非忽略未跟踪、显式登记输入。分别给same/changed/unknown；不依赖Git clean/assume-unchanged、mtime作内容身份。文件模式、删除、索引与工作区不同步均可见；unknown不认证。捕获两遍核输入稳定，但不能证明执行区间从未A→B→A，不阻止IDE或其他进程写入。

project.py新增quality_snapshot/quality_comparison用于check与audit-delivery；scan fingerprint v2及非Gitmanifest盘点保留原范围。新报告保存执行前后比较和有效gate_contract；命令全0但输入变化不能通过audit，也不能被verification.py升级成自动行passed。纯理由文字变化不变更gate合同；声明的workflow脚本/忽略配置仍纳入，默认不全扫忽略输出。

新身份只用于本地自动执行与审计；manual_evidence_stamp、carry父条款、设备回执及全部读者分流未改。报告仍项目单份，无attempt隔离/执行锁/通用中断恢复，不宣称FT-01/02整体完成。旧报告缺新身份不自动升级为当前，应在获授权时执行适用检查；不要手写hash或借旧绿灯。正式版本待发布范围确定后依MAINTAINER政策选择，VERSION暂留已有0.14.0候选，不表示B1已随该安装分发。

## 实际验证记录

- 首轮定向57项，2项失败：旧无Git scan夹具被过严的worktree读取误挡；另一个检查夹具无Git、哨兵输出未声明。保留非Git scan仅盘点；自动检查必须有Git身份，执行夹具改为明确Git根并忽略它的哨兵输出，不把输出生成误当源码变化。
- 后续定向83项通过（53.135秒）；该过程仍增补了最后一个自动行拒绝反例，最终17项B1用例与最终代码以完整回归为准。
- 首轮完整463项（463.236秒）有1项失败：需求基线执行中不可读时，旧合同期望退出2，新实现误返回1；已保留unknown/退出2，同时保存不可认证的执行事实。该失败不算通过。
- 自查补充失效登记清单symlink与门禁解析后/执行前变更两条边界。最终B1新增19项；19项加上述旧失败用例共20/20通过（6.544秒）。
- 最终完整回归465/465通过（unittest 458.121秒，外层实测458.234秒，退出0）；运行前后skills/scripts/tests全部输入SHA一致。已保存[原始合成测试输出](b1-check-identity-2026-10-16/full-unittest.txt)和[机器摘要/测试文件身份](b1-check-identity-2026-10-16/results.json)。没有新上下文Agent或真实业务复验。
- 语法AST和git diff --check通过；实际CC安装清单仍0.14.0/104文件，清单哈希无变化，新check_identity未安装。未重复安装或业务测试。

## 代价、已知限制及后续

为覆盖Git标记掩盖的变更，本版直接读取非workflow tracked实际内容并分块hash，每次捕获两遍，执行前后均核；这增加I/O及质量报告体积。大型Android真实耗时/费用未测，不能承诺省时或净收益，不把全套测试耗时当实际项目身份计算耗时。忽略输入需登记，外部依赖/环境/设备/产物构建出处不隐式认证；symlink/未合并index/子模块等明确unknown。不可读文件不当作不存在。

旧报告只保持历史，不批量重跑或更新记录。B2执行尝试隔离、B3统一所有读取者、B4完整兼容采用仍待授权；日常安装保持不动。R-3 assumptions延续阻断和B-16三星绘制缺口均未因此解决；第二阶段仍未完成。
