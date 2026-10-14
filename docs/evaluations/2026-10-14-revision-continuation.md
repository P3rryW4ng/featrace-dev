# 0.13.1 未交付修订接续修复

日期：2026-10-14。真实触发为OGFR-7700：v3/CHG-002已应用，产品又改定R-6通知保留对象。0.13.0拒绝新修订，迫使先交付已否决的中间版本。维护会话只读核对现有基线与提案；没有修改真实需求、代码、设备、任务或推送现场。

## 最小修复

复用propose/apply：基于当前base_version/base_digest/before，明确continues_revision指向当前最新未交付applied，并写continuation_reason和批准决策。保持一次一个pending、旧提案/事件哈希、来源身份及正常confirmations；追加新provisional版本，不取消旧applied、不插入假delivery。已交付基线仍用原普通提案，旧历史兼容。生成revisions.md显示接续关系。

最后交付只针对最新基线，完整现行条款、来源、任务、影响、测试及报告门禁不变。对接续链中仍存活的早前语义字段，最新提案必须承接对应旧提案test_ids；先退役再恢复不能丢掉这些义务。后来明确替换的完整字段/最终退役需求不要求旧测试含义。验收数组整体替换时，新提案负责完整数组，包括文字未改的条款；helper不能机器证明测试断言完整，Verify仍逐条审查实际当前证据。人工/自动分类走既有追加更正，不按test名伪造自动覆盖。

这修复已有流程的误阻塞，按patch0.13.1；不新增阶段、自动merge或批准权限，不证明L2完成。

## 验证

- 目标28/28通过（10项新边界+18项既有修订测试，10.725秒）：连续未交付更新、缺关联/原因/批准、旧base/before、source变更、pending/取消、旧提案/事件篡改、旧quality拒绝、仅最新版delivery、交付后普通修订、跨字段承接和退役恢复。
- 完整374/374通过，238.486秒，exit0。运行文件未在测试中途修改；AST、入口YAML及git diff --check通过。
- 独立只读复核最初发现“仅latest test_ids可能丢失存活旧变化测试”，修正后又发现“历史deprecated并集误判恢复需求”；两处均加入回归并确认复现已阻断。试验均在独立/tmp，不改业务。
- 原生Claude定向合成演练：未交付v3/CHG-002收到新确认后，记录D-003并propose/apply CHG-003至v4。关联CHG-002，旧CHG-001/002、原始来源及代码/测试字节全等；deliveries仍[]，状态provisional，受影响任务重新planned，closure TASKS_PENDING。没有测试、complete、提交或推送。CLI墙钟128.083秒，报告费用0.9559964USD，分类usage见[摘要](revision-continuation-0131/native-result.json)，不是账单核验或真实项目净成本。
- 合成夹具有旧source target未同步，Claude在新修订后保留旧映射并登记新来源、完成全量PRD审阅。它新增了从明确产品文字推导的AC示例，并说明不是用户逐字原话；没有用示例宣称通过。此为定向规则采用，不证明真实v5所有source aspects都能无遗漏。

中途测试夹具直接inspect使用/var路径别名，被安全检查拒绝；改成resolve。另一个新断言误读CLI stdout，而错误写stderr；修正测试读取，不放松运行guard。失败尝试保留日志，不能当绿色结果。

本机CC已安装0.13.1，101运行文件与源码/安装清单一致；原0.13.0/101文件备份 /Users/mac/.feature-delivery/backups/20261014T060612-claude-df8daefe 核对一致。原生日志在/private/tmp/featrace-0131-native/，仓库只保留合成摘要，不复制业务记录或账号元数据。下一真实动作交由CC重载后从OGFR-7700当前v3接续；本仓不宣称真实v4已应用或最终推送已验收。
