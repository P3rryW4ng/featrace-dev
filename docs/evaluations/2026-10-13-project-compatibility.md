# 项目预配置兼容审查：0.11.2（2026-10-13）

## 问题依据与实现边界

用户提供同事的截图：Agent 判断 Comet/OpenSpec/opsx 重叠并准备修改本机配置。截图未证明 FeatraceDev 被加载，也未证明 skillOverrides 实际受支持。只读检查 zymix-im-android-cloud 主仓确认 CLAUDE.md 引入项目规范、Comet 阶段规则每轮注入，项目 settings 注册 comet-hook-guard.sh；该脚本选首个活跃 Comet 记录控制写入，不关联当前 Feature。检查时主仓无活跃记录；不能替同事现场下结论。项目 Gradle 规则允许已有明确验证授权，无需重复提问。

0.11.2 只增加按需 Agent 指令，入口、编排和 scan 均引用 project-compatibility.md。区分规范/主流程/执行约束；无具体冲突继续，有冲突保留现场并指明受阻动作。既有 conventions/coverage 和 evidence 注册承接项目事实，不改数据格式、外部流程或配置，也不新增脚本门禁。help、空激活和只读 status 不盘点配置。

## 实际执行

- `PYTHONPATH=tests python3 -m unittest test_workflow -q`：24/24 通过，5.070 秒。此次未改脚本，未重跑完整脚本套件。
- `quick_validate.py skills/dev` 因系统 Python 缺 PyYAML 无法启动；Ruby YAML 解析确认入口 name/description 有效。替代检查不冒称原验证器通过。
- 临时 home 安装为 0.11.2：90 个文件与安装清单及源码 SHA-256 逐项一致，新增 reference 由三个入口引用且可读取。未更新日常 Claude Code 安装。
- `git diff --check` 通过；流程图已区分只读入口与首次实质兼容检查。

## 全新上下文合成复核

Codex 子 Agent compatibility_review 只取得隔离安装副本、两个合成项目、用户请求和只读限制；没有收到预期答案。用户请求用 FeatraceDev 准备 VALUE 1→2，已授权后续相关 Gradle 检查，但本次不写文件或运行构建。

两项目均有项目编码规范、Comet Skill 和一个 PreToolUse 钩子。A 有 teammate-task 的 design 记录；B 无活跃记录。钩子故意不做路径或工具筛选，遇到 design 返回 2，否则返回 0。

| 场景 | 实际返回 |
|---|---|
| A 他人活跃记录 | 区分请求的 FeatraceDev 归属与钩子强制限制；引用设置/脚本/实际记录，停止受限执行，保留同事记录，不推荐禁用或改阶段绕过 |
| B 仅安装竞争流程 | 无活跃归属冲突，不新增选择问卷，可继续只读准备；后续测试授权已存在 |

复核者另指出 A 钩子并不限于写入，可能影响任何匹配 PreToolUse 操作；准确限定这是代码审阅，未实际执行钩子。隔离文件检查前后哈希/路径集合一致，无净改动。

## 未验证

这是 Codex 子 Agent 的只读合成 forward evaluation，不是 Claude Code 原生自然派发；只证明这两个具体配置的指令理解和包装完整性。未实测真实工具拒绝、团队冲突解决、配置变化后的恢复、基线摘要发布、上下文/时间/Token 收益；不得据此关闭 GAP-31 或宣布第二阶段完成。下一次安装版真实使用核对上述边界。
