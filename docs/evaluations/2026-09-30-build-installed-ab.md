# 0.5.36 安装版 Build 任务视图与同输入对照

日期：2026-09-30。测试对象是本机 `/Users/mac/.claude/skills/dev` 安装版 0.5.36。使用已有 FEAT-001 合成 CSV/JSONL 双任务夹具，复制为两个独立 Git 项目；起始 HEAD 同为 `27f72944625342209d310f299ee4555848b1b86f9`，原始 PRD、需求/任务/影响记录、源码 stub 与 16 条测试逐字相同。两个 Claude Code CLI 会话都从普通 `/dev develop FEAT-001` 入口启动；串行组增加 `--serial`，并行组按已审任务边界请求考虑双 Worker。两组先后运行，均无业务产品选择或人工代码干预。登录本机 Claude Code 是演练前的环境操作，不计入下表执行时长。

## 结果

| 对照 | 串行单 Agent | 两个 Build Worker |
|---|---:|---:|
| CLI 墙钟 | 102.854 秒 | 223.457 秒 |
| CLI 标价费用估计 | $0.761653 | $1.850939 |
| CLI 汇总输出 Token | 9,449 | 22,991 |
| 已有集成测试，维护者独立重跑 | 16/16 | 16/16 |
| 独立合同探针：有限价格 `1e28` | 通过 | `InvalidOperation` 异常 |
| 主项目代码 | 改 `upper.py`、`lower.py` | 保持不变，结果只在外部集成候选 |

在这一次同输入试验中，两 Worker 用时约为串行的 **2.17 倍**，费用估计约为 **2.43 倍**；不能据此推断所有任务并行更慢。两次运行顺序、CLI 缓存、模型采样、提示中的策略约束及集成开销都是混杂因素。费用是 CLI 按标价的估计，不是账单。未取得可靠的逐 Worker 真实上下文节省量。详细数字、冻结输入摘要和工具计数见[评估数据](evidence/2026-09-30-build-installed-ab/assessment.json)。

## 安装版实际采用

两名原生 `general-purpose` Worker 都在新的 Agent 上下文里先读取 `specialists/featrace-build/SKILL.md`，再依次执行 `preflight` 和本任务的 `task-view`，之后才读取任务证据和源码。T-UP 的读取集中在 `upper.py`、对应测试、集成测试和冻结原 PRD；T-LOW 集中在 `lower.py`、对应测试、集成测试和同一原 PRD。工具轨迹未见 Worker 直接打开完整 `run.json`；两个 `finish` 都返回 ready，集成返回 `candidate_checks_passed`。这证明**安装版 Agent 实际采用任务视图入口**，但不是文件系统强制隔离：两个 Worker 仍可读完整原 PRD，源文件中也同时描述两项任务。此夹具 `run.json` 为 9,804 字节，两个 `task-view` 实际打印分别为 7,847 和 7,862 字节；这只是输出体积，不能等同 Token 节省。

工具轨迹还显示两个 Worker 在 `finish` 前只查看了 `git diff --stat`，没有阅读全文 diff，**未完全遵守 Skill 要求的实际补丁复核顺序**。辅助的第三个 `Explore` Agent 收到 `noop`，不承担任务，应视作本次额外开销；总费用包含它。上述问题不能由 `finish` 的绿色状态抹去。原始 CLI 流保留于 `/private/tmp/featrace-0536-ab-kiwejvfh/`，其中可能含本机配置，不入库。

## 独立正确性探针

维护者在两组完成后独立运行现有 16 条测试，并额外按原 PRD 的“有限 Decimal、非负、最多两位小数、格式化两位、不得因价格抛异常”合同输入 `1e28`。串行输出期望的 `10000000000000000000000000000.00`；并行候选在 `Decimal.quantize(Decimal('0.01'))` 时受默认精度限制抛 `InvalidOperation`。这是**候选代码缺陷**，没有被现有 16 条测试发现；不是任务视图本身的确定性错误。探针见[脚本](evidence/2026-09-30-build-installed-ab/contract_probe.py)及[原样结果](evidence/2026-09-30-build-installed-ab/contract-probe-result.json)。候选未采用，原主工作区、权威记录和 HEAD 均未改。

## 判断与下一步

0.5.36 的任务视图已被安装版 Worker 使用，但这次合成任务**没有证明并行或拆分带来净收益**，且独立合同探针发现了候选行为遗漏。现有选择策略应继续允许串行；不能因“两个任务互不改同一文件”就默认并行。下一步先对 `finish` 前全文 diff 复核做最小提示/采用修正，并在成本证据中保留额外 Agent 与完整来源回读；真实需求仍按路线图检验连续交付收益。无需为了这次探针把隔离候选修成产品版本，也不把本合成结果提升为真实需求结论。

后续状态：全文检查已在 [0.5.37 源仓修正](2026-09-30-build-full-diff.md)中补强；本页保留 0.5.36 的原始观测，不将旧 Worker 结果改写为新版采用证据。
