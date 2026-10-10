# 0.7.3 外部配置分流安装版隔离演练

2026-10-10，在本机 Claude Code 2.1.283 中安装源码 0.7.3；安装标记列出 82 个运行文件，逐项 SHA-256 与源码、安装副本一致。原 0.7.2 已由安装器备份。未连接真实后端、未读取或修改业务项目。

两个独立 Git 夹具位于 `/private/tmp/featrace-external-config-073/{supported,unsupported}`。同一合成需求要求既有 eSIM 服务入口打开 `offers?productId=28`，标题和图标不变；`service-contract.md` 明确 GetServices 的 launch 配置由后端下发，`current-response.json` 明确只是旧示例，不代表实时响应。两例的差别只有 `client.py`：supported 对有效 mall.app path 通用转发；unsupported 有只允许 `home` 的本地白名单。给两个全新 CLI 会话的中立提示相同：调用 `/dev`，读取需求、契约、旧响应和客户端，在 Scope 实施归属与下一阶段边界停止，不写文件、不运行测试、不开展 Build。使用 Claude Sonnet、`--no-session-persistence`；第二例禁用编辑和 Bash 工具。仓库 Git 状态前后均干净。

| 场景 | 实际回复与判断 | 轮次 / 耗时 / CLI 报告费用 |
|---|---|---|
| supported | 明确“零本地代码改动”、后端 owner；给出 `launch.target` 的具体新值，保留 kind/title/icon；旧 JSON 不作为生效证据，停在 `pending external application`；待真实响应与一次窄范围点击/解析后 Verify，不进入 Build，也不要求整套客户端构建 | 6 轮 / 90.25 秒 / US$0.54744 |
| unsupported | 发现客户端白名单 `{"home"}` 会拒绝 `offers`，判为客户端代码 + 后端配置的混合实施；本项目进入 Build 修改白名单及针对性单测，外部配置仍须实收，未提前宣称完成 | 7 轮 / 51.74 秒 / US$0.1902856 |

原始返回分别保存在临时目录根部的 `supported-result.json`（SHA-256 `d850a242cd14a6f486a126509c0abc1909d52011eaa882e48a556e3fb2846b49`）与 `unsupported-result.json`（SHA-256 `d250a52b846e89e8d29990037b0b7bc3a3554b1dcc61a140c677a2accbbb7591`）；项目文件未写入。两次均报告成功，未运行真实质量门或设备验证。首次使用 `plan` 权限模式时，Claude Code 尝试创建宿主计划文件，被当前沙箱拒绝；它随后直接返回只读结论。第二次改用不询问权限并禁用写入/命令工具，未出现该额外步骤。

**结论范围**：这证明在两个受控输入里，安装版 Agent 的最终分流判断符合预期，且没有把过时配置样本当作实际部署。JSON 最终回复提到新参考规则，但本轮未保存完整工具调用轨迹，因此不能由此单独证明每一次内部文件读取顺序。没有真实后端、真实混合需求的自然触发、质量报告重用或端到端交付证据；也没有与旧版同输入的时间/费用对照，不能宣称省时比例。纯配置 Feature 的空质量门限制仍在。
