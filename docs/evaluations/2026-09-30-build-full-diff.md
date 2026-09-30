# 0.5.37 Worker 全文补丁检查

2026-09-30。触发证据是[0.5.36 安装版对照](2026-09-30-build-installed-ab.md)：两个 Worker 虽按编辑→差异→`finish` 的顺序运行，却只查看了 `git diff --stat`，没有看完整补丁。此次只修正这一检查缺口；未修复该候选的价格行为缺陷，也未扩大并发范围。

## 实现与边界

- Worker 编辑成功后，单独调用 `parallel-build.py inspect-diff <RUN> <TASK-ID>`。helper 使用与 `finish` 相同的私有索引和作用域检查输出完整 `full_diff`，成功写出后才在外部尝试目录保存绑定尝试摘要、补丁 SHA-256、改变路径和工作区状态的检查记录；输出写入失败不会留下可复用记录。
- `finish ready` 在没有对应记录、代码/索引变动导致记录过期或记录被改写时失败，且不会运行任务检查。阻塞或失败的诚实返回不要求全文检查。集成时再次核对记录与已测试补丁。
- Skill 要求 Agent 阅读每个变更块；若工具输出截断，须补读缺失部分或以 blocked 返回。脚本只证明完整补丁**曾被输出且对应当前候选**，不能证明 Agent 看完、理解或验证了行为。原任务检查、集成检查、主项目 Verify 仍必须执行。

## 实际验证

`test_parallel_build` 29/29；完整 `python3 -m unittest discover -s tests -q` **277/277**（84.957 秒，退出码 0）。覆盖缺检查拒绝且测试未运行、CLI 输出实际代码块、输出失败无记录、修改后旧记录失效、重新检查可继续、记录篡改拒绝、两 Worker 集成以及既有越界/过期/失败路径。`py_compile`（缓存定向至临时目录）、三个 Skill frontmatter 的 Ruby YAML 解析、`git diff --check` 通过。Skill Creator 的 `quick_validate.py` 在导入 PyYAML 时失败；未声称其通过。

本轮没有启动 0.5.37 Claude/Codex Agent，也未安装或推送。安装版仍为 0.5.36；下一次安装后需在隔离夹具观察 Worker 实际调用 `inspect-diff` 并阅读全文，而非仅依赖脚本测试。
