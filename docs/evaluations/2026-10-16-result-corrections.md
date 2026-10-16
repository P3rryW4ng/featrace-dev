# 普通验收结果说明的定向勘误（2026-10-16）

## 真实问题与范围

据用户CC回报，OGFR-8024的R-1:2 actual以及R-3:1/2、R-5:1/2、B-15 evidence描述需要纠正或改为持久归档路径，旧工具只接受retained，不能把普通passed转retained绕过。该需求同时有D-005/R-7产品歧义，39 stale/1 not_run。维护工具修复不裁决产品，不重签业务结果，不操作真实业务仓/设备。

候选0.14.0新增result_corrections.py，冻结精确目标和支持文件，fresh-context review支持后追加说明；不改原history、测试身份、时间、coverage、status或evidence_digest。可修正stale历史文字，但不使其current；后来unavailable仍保留。新说明在status/render、stage view和claim-review中出现，支持材料变动使最终复核输入变化。只有首次应用勘误的需求使用verification schema 2，旧版读取器拒绝，新版继续读schema 1；这项明确读写契约变化使用中间位0.14.0，不宣称第二阶段完成。

## 实际执行

- 首批12项目标测试通过（20.138秒）。增加安全路径核对时遇macOS `/var` 与 `/private/var`别名不一致，16项中15项报错；修正root/folder规范化后16/16通过（33.559秒）。记录失败，不放松路径检查。
- 最终运行脚本在加入状态/视图细分标记后冻结，完整回归446/446通过（443.912秒，退出0），包含最终的16项新增用例。另一个组合目标运行曾加载别名修正前的版本，失败日志不当作通过。
- 隔离home安装104文件与源码及清单一致。安装版CLI：partial审查退出1不写记录；支持审查退出0；原items/history逐字段不变、stale仍stale，schema=2；从bf348c9提取的旧0.13.6读取器明确拒绝；支持文件变化改变claim-review digest且stage view显示support_current=false。
- 补充实际门禁探针：先运行1项合成自动门禁，再追加勘误；门禁历史、质量报告字节及全局验收摘要完全不变，不重新执行门禁。[隔离摘要](result-corrections-0140/results.json)。
- 脚本/测试AST、本地文档链接、git diff --check和未修改入口的Ruby YAML检查通过。skill-creator quick_validate仍因本机缺PyYAML未执行，不将替代检查说成原验证器通过。
- 临时审查返回是明确的synthetic fixture，用来验证绑定及拒绝机制，不是原生Agent独立语义复检或人工覆盖批准。没有业务测试或净成本测量。

## 边界与接续

coverage或产品要求变化不走本路径。review字段不是身份认证或语义证明，实际使用时必须真实新上下文读取完整条款、原结果与支持材料。勘误对照当前结果阅读，不改变验收当前性；当最终复核绑定失效时按正常流程更新，不能手改摘要。旧规则及新格式共享者升级到至少0.14.0后才应用；不自动迁移其他记录。

源码候选未提交/推送。完整验证后已安装本机CC0.14.0，104文件与源码/清单逐项SHA一致；原0.13.6/103文件备份于 `/Users/mac/.feature-delivery/backups/20261016T040231-claude-f0dfb3f0` 且与原清单一致。安装不自动迁移任何业务记录；需CC重载规则后应用，不能只把磁盘安装当会话已加载。本轮未处理D-005，也未为CC选择A/B、重新登记、执行设备或恢复complete。
