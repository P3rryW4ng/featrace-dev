# 0.13.0 原生 Claude Code 隔离验证与发布检查

日期：2026-10-14。使用本机已登录 Claude Code CLI 的默认模型，在临时 Git 项目安装候选 Skill；本轮没有更改真实业务项目。仅加载临时项目设置，禁用该临时环境的hooks，允许只读工具和明确授权的检查结果/scratch写入，禁止编辑代码/测试、人工通过登记、complete、提交、推送和子Agent。不是生产项目hook兼容演练，也不证明独立Test Skill。

## 三个原生场景

| 场景 | 实际结果 | CLI墙钟 | CLI报告费用（USD） |
|---|---|---:|---:|
| 只读T-1复核（DEMO-PREVIEW） | 自行读取stage-inputs，生成/核对任务Verify视图；发现共享常量使收据12→8、短字符串测试不足、遗漏消费者，保留全局未决信息，未修改业务/权威记录 | 113.425秒 | 0.827974 |
| 执行被前置阻断（DEMO-PREVIEW） | 生成Test视图后run因另一条需求缺title/source/test被拒；没有借旧质量报告宣称这次执行成功。未修复夹具，保持缺口 | 130.037秒 | 0.6532682 |
| 实际Test→Verify（FEAT-001） | 合格小型夹具正常执行现有unit检查；生成新的Verify视图。指出1+1=2的断言不能证明abc→ABC，未标完整需求通过 | 93.847秒 | 0.699694 |

三个场景共337.309秒，CLI费用报告合计2.1809362 USD。费用是CLI报告，不是账单核验；输入、输出、缓存读写分别保存在[摘要](stage-native-0130/results.json)，不把上下文大小或缓存读次数当独立交付Token总量。本轮没有同输入原生对照组，不宣称净效率提升。

在第三场景完成后，维护会话实际核查：测试前视图check返回1、明确stale；测试后Verify视图check返回0、STAGE_VIEW_CURRENT。新质量报告有当天tested_at、unit returncode=0/passed。逐文件哈希比较只改变quality-report.json、verification.json、verification.md，均属于授权标准结果留证；代码、需求、决策、影响和门禁选择不变。未登记人工通过、未改feature状态。第一场景scratch外文件哈希全等。

## 返工与局限

第一次CLI调用在网络沙箱内重试失败（exit1），不计有效演练。授权网络调用后才得到上述结果。执行场景最初使用只读复核的故意不完整夹具，正确被develop拒绝；维护会话补合成字段时又遇到sources格式、重复任务和intake无效，最终采用既有已通过开发预检的VerificationTests夹具完成执行接续。没有改Skill规则来放过它，也没有将失败尝试算作成功。上述开销不隐藏。

Agent仍为核查而回读部分完整JSON、检查了重复历史片段；只读组返回还附带了无关连接器授权提示。失败场景首句写“I ran the selected Python check”，随后明确runner拒绝执行；首句仍易被读成测试已实际运行，不据此宣称所有报告叙述完全准确。这些说明实际读取量、简洁性和普通入口自主采用仍需真实观察。此轮是有明确范围/副作用限制的定向原生验证，不能证明生产环境自然连续交付或准确率。

源码发布前重新运行完整回归：364/364通过，257.943秒，exit0。所有Python AST检查及变更总览文档本地链接通过，git diff --check通过。skill-creator quick_validate缺PyYAML无法启动，使用Ruby YAML检查三份Skill的frontmatter、name、description通过；未把该替代检查说成原validator通过。

日常CC从未修改的0.12.2更新为0.13.0：101运行文件与源码和安装清单SHA-256逐一一致。旧96文件保存在 /Users/mac/.feature-delivery/backups/20261014T022635-claude-5af375c0，备份哈希与旧清单一致。该安装不改变业务项目的验收或提交。

原始stream日志位于 /private/tmp/featrace-0130-native/，可能清理。仓库只保留合成输出/命令/用量摘要及原报告哈希，不提交账号元数据、个人配置、完整原始transcript或业务证据。
