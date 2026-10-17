# 自动检查事实与验收绑定分离：第一批实现（2026-10-17）

状态：用户已批准[方案评审](../reviews/2026-10-17-verification-invalidation-scope-review.md)第一批本地开发与隔离验证。源码基线0a33739，VERSION保留已发布0.16.0；没有发布安装、启用业务新模式或推送。日常Claude仍0.16.0/107，逐项哈希未变。此为main集成开发候选，包含此前未安装B1/进度开发指令；临时110文件安装不等于获准把main整树安装到日常CC。

## 已实现

新增check_runs内部共享层，显式项目`execution_contract: 2`启用，现有项目默认legacy；旧config归档/来源哈希、feature选择、已解析命令和feature本地latest/start/result分别保存。共享命令定义仍在原quality-gates，feature只列选中的name/test_ids及理由，不建第二套命令定义。旧读取器拒绝marker，新verification schema 4拒绝旧读取器忽略新自动引用；原历史不伪造迁移，corrections/adoption兼容新plan不降级。选定命令/test_ids/cwd/timeout或必要输入变化仍拒绝复用。

project.py直接check与verification.run共用项目非阻塞锁/attempt写入，按需求隔离完整执行。最新失败、超时、中断、终止记录缺失/损坏不借旧绿灯。start与terminal使用不可替换创建和哈希绑定；latest原子保存。B1读取真实tracked/index/worktree、未跟踪和显式登记输入；流程提交可保持同一业务输入，不冒称冻结外部环境。POSIX运行器终止并核对自己创建的进程组；未确认退出、硬中断/orphan现场拒绝新执行/当前认证，不做自动恢复或副作用命令重试。

执行后的命令成功行可记录实际事实，产品自动验收行不因命令退出0直接通过。新增既有verification入口的capture-check-mapping/adopt-checks：普通Verify检查当前精确断言、实际执行TEST IDs和完整要求后，绑定同一次完整成功attempt。record/选择理由变化不改旧start/result；相同已采用审查再次返回成功且不追加历史，输入漂移/并发覆盖则拒绝。新的执行成功但登记失败可以再采用，不跑命令。只改本行mapping不重签其他行；requirements/decisions/impact语义仍保守绑定，不宣称已解决人工全局失效。

审计、revise、validate-verification、feature-status、Test/Verify起点、报告草稿及最终claim-review使用同一feature结果/当前性；阶段视图引用实际start/result而非旧全局报告。整段交接依旧冻结必要权威输入，完整终审不改成增量缓存。状态批量共享一次执行当前性核对，不逐行重复全仓身份读取；后续语义/impact读取和历史核查仍有开销。

## 实际验证

- **最终定向18/18（33.937秒）**：执行与重绑定计数、幂等、未改行历史、失败/缺terminal/篡改/禁用marker、输入/选择/声明忽略输入变化、跨feature隔离及锁、超时/中断/未知进程组、半写恢复拒绝、登记失败后采用、精确映射缺口/漂移、各读者及旧版明确拒绝。
- **完整519/519（530.774秒）**，零跳过，退出0；运行前后164份runtime/scripts/tests输入SHA一致。519已含本批18，不能与18相加。原始输出、输入清单和[机器结果](check-facts-2026-10-17/results.json)保留。
- **隔离110文件CLI安装/接续**：临时home原0.16.0/107升级到`0.16.0+check-facts-candidate`，源/清单/临时安装哈希一致，旧107及清单备份一致。实际调用候选prepare、sync、run、capture/adopt、status、inputs和audit：命令只执行1次；决定记录变化后采用旧执行，原start/result字节未变；同一审查重复/重新capture均无重复历史，manual保持未验；源码变化后audit拒绝。它是脚本/CLI确定性夹具，不是CC原生语义前向评测、真实Android或真实省时试验。
- **旧版实测**：临时归档旧0a33739工具，verification明确以未知schema拒绝4，project明确以不支持的config字段拒绝marker2；不是仅凭任意非零出口算通过。旧格式路径由完整回归继续覆盖。

## 失败、修正与中断留存

首轮新用例7项均在fixture准备时失败：/var与/private/var根别名处理不一致，修正安全路径规范化；随后一次未知feature预期ValueError而实际为FileNotFoundError的测试错误更正。扩展读者用例又发现selection未规范化别名，已修；schema-3必须有adoption事件的旧约束在自查中恢复，schema4兼容不弱化旧格式。

增加工作区未完成/损坏现场前置核查后，损坏事实正确更早被拒，但一条测试仍只匹配旧“hash”文字，最终18项中1失败；更正为新正确报错。第一次完整运行刚启动便因此主动中断，不算完整通过。隔离演练随后暴露同一已采用review重复返回应幂等成功，补实现及断言，第二次完整运行主动中断重启；两份中断输出保留，不把部分通过计入完整结果。

封装演练首轮把sync的既有“生成成功返回0”误当“验收未完成返回2”，为临时脚本错误，修正后演练通过。所有上述失败保留在本目录；没有为使测试通过放宽失败/未知或旧reader拒绝，没有操作真实业务回执。

## 能力边界与新增维护成本

仅显式启用的新模式拥有attempt与采用路径；旧项目仍用旧逻辑，不批量迁移。每次attempt首期执行完整已选集合；不跨attempt、需求或工作区拼绿灯，不做队列、通用过程恢复或非POSIX进程组执行。必要外部/ignored输入要声明，输入哈希和reviewer文本不证明环境、语义、独立性或真实设备运行。当前普通mapping审查可由授权Verify Agent完成，不另增每行强制人审/新Agent；v6最终新上下文完整复核照常。

代码/测试/config变化仍使自动执行过期，即使实际无关；人工全局摘要/完整父条款carry和whole-evidence合同没有缩小，留第二批。设备延续0.16.0与后端契约等待保持原状；尚不能宣布第二阶段完成或当前FIX免测。

新增维护面：显式模式与旧reader拒绝、选择/attempt/head读写、组进程终止/未知现场、schema4与现有事件兼容、所有读者及断言映射。B1及attempt读取含本地I/O，历史核查随attempt数增长；大型Android耗时、人工投入和实际模型费用未测，没有同任务对照不推算净收益。临时CLI执行1次只是该合成场景，不是整体开发/验收耗时对照。尚未进行新上下文Agent自然接续或真实项目启用验证。

## 接续

本轮交付为本地候选，未提交、推送、发布或日常安装。建议下一步评审可发布范围与兼容/回退：旧记录不改，启用后旧工具拒绝该工作区，不能只降级安装继续认证；未完成现场不得删掉头或终止事实来重跑。发布和业务启用分别需要范围授权，不用等待后端的业务去试验新格式。8025复盘仍按用户安排最后做。


发布前评审接续（2026-10-17）：[精确范围/兼容/回退评审](../reviews/2026-10-17-check-facts-release-review.md)已完成，建议0.17.0定向110文件；独立候选验证仍待做，不将本报告main集成测试改称其结果。B1对legacy旧报告的当前性影响已明确披露；日常安装不变。
