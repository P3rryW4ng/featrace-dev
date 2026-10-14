# 旧人工证据延续：0.12.0（2026-10-13）

## 实际问题

CC 用户回报 OGFR-7700 / D-006 JSON null 修复及 TEST-9 21用例通过，但决策审批/落实、扩大 allowed_paths、新增行为共同使26条其他验收 stale。旧行没有严格 retain 所需的预登记文件溯源。不能用事后补依赖和重新登记制造资格，也不应仅为摘要绿灯重复界面矩阵或等待真实推送。

## 源码改动

新增 evidence_carry.py 与按需 evidence-carry.md。capture 为只读逐行冻结原最后通过结果、完整父要求/行合同、历史/current工作流、每条代码变更与来源/证据身份。依赖历史完整提交和合同；父条款变更或撤回/失败拒绝。apply要求全新上下文supported审查，逐项覆盖文件与记录变化、原包/工作树归档依据、完整断言、调用/环境和反例；相关/未知不能延续。追加retained回执，保持原tested_revision，另记reviewed_revision，不生成新测试结果。receipt载入复核完整schema和摘要；later代码/来源/归档证据/traceability/intake变化失效。旧严格retain及自动门禁不变。

verification的sync/run/record/retain和新apply用项目scratch内非阻塞文件锁串行化；保存前核对原计划。只协调参与helper的写入，不是文件系统事务或禁止外部编辑器写入的沙箱。

## 执行证据

- 最终目标回归 `PYTHONPATH=tests python3 -m unittest test_evidence_carry.EvidenceCarryTests -q`：**15/15**，28.554秒。
- 最终完整 `PYTHONPATH=tests python3 -m unittest discover -s tests -q`：**328/328**，160.947秒。
- 正例：无事前依赖溯源的旧需求行，经有据合成审查后追加retained，原result和原tested_revision不变，workflow-only提交不失效。
- 反例：依赖有变/未知变更/partial/同上下文/错误输入/漏审元数据/父条款变化/最后结果失败/原身份未绑定/归档引用缺失均拒绝；来源、代码、追溯变化失效；回执重算hash后缺必填审查仍拒绝；并发他行失败不被覆盖；忙锁拒绝；自动门禁不能使用此路径。
- CLI capture/apply在合成夹具实际运行。临时home安装0.12.0，**92文件**逐项与清单和源码SHA-256相等；未更新日常CC。
- AST语法检查与 `git diff --check`通过。一次py_compile因默认缓存前缀位于受限用户缓存目录而未启动，改用不写缓存的AST检查；不冒称原命令通过。

## 失败与纠正留痕

初版目标回归因macOS /var与/private/var路径别名出现1FAIL/5ERROR，规范化路径后又因source_identity调用未resolve出现2ERROR；已修正。独立Codex代码审查发现回执schema可缺省、追溯不绑定、并发结果覆盖三个问题及旧HEAD不等于原工作树的风险；补完整载入校验、来源/证据/追溯绑定、helper锁及保存前计划比较、原包/树归档依据要求。最终审查确认前三项根因修复，未发现新的具体阻断问题。不是原生CC语义行为验证。

## 真实项目只读适用性检查

使用源码helper只读检查OGFR-7700现行记录：26条stale人工行均可capture，耗时23.32秒，未生成审查结论、未apply、未改业务记录或运行Gradle/设备测试。单条R-1:6初次capture遇到项目中Skill符号链接：改为仅记录Git对象类型/身份，不跟随链接；作为dependency的链接/子模块仍拒绝。26条capture成功只说明历史合同和输入可取得，不证明每条都有充分原身份或完整覆盖证据。

## 未验证与下一步

尚未在已安装CC上自然派发独立carry review或把真实26条延续到交付；本机安装仍0.11.1。审查独立性、理由真实性、旧包与工作树绑定、外部环境等价性仍由实际reviewer/路由核对，脚本不证明。净省时/Token/误阻塞未测。业务provisional保持原样；安装新版后逐项审查支持的行才apply，未知行定向补测。不要把未更新的本地联调HTML“D-006待定”继续当现行结论。

## 后续本机安装

本机CC由受管且未改动的0.11.1更新为0.12.0候选版，92运行文件与源码/安装标记逐一SHA-256一致。备份20261013T082719-claude-dd84fd55包含原0.11.1的89文件，逐一核对完整。未修改业务验收记录，未执行真实carry审查或apply；源码未提交/推送。前述“日常仍0.11.1”属于安装前截点。
