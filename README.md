# FeatraceDev

**简体中文** | [English](README.en.md)

面向 **Claude Code 和 Codex** 的开发 Skill：理解改动影响、实现需求、定向验证，减少不必要的重复验收。

## 安装

当前正式版 **0.30.7**。需要 Python 3.9+、Git 和对应 Agent；项目构建环境沿用项目要求。

```bash
git clone --branch release/0.30.7 --single-branch https://github.com/P3rryW4ng/featrace-dev.git
cd featrace-dev
python3 scripts/install.py --agent claude
```

Codex 将 `claude` 换成 `codex`；两端都安装用 `both`。安装后打开目标项目的新会话。

## 使用

Claude Code 输入 `/dev`，Codex 输入 `$dev`，然后直接描述需求，例如：

> 修复登录页的错误提示，先确认影响范围，再实现并验证相关行为。

提供必要的需求原文、设计或问题现象即可，不需要手动操作内部命令。空调用只开启模式；`dev off` 退出。进入时显示实际版本，成功结项时明确报告完成范围。

Skill 按实际影响选择检查，复用仍有效的结果，保存必要证据，并在授权范围内按小任务提交。它不替代产品判断、项目门禁或发布批准。

## 更新与文档

更新前保留本地改动，获取并切换到固定发布引用 `release/0.30.7`，再运行 `python3 scripts/install.py --agent claude --update`。旧发布分支上直接 `git pull` 不会升级版本。安装器保留旧版备份，拒绝覆盖被修改的副本。

- [使用与接续](docs/usage.md) · [模块与流程](docs/module-guide.md)
- [版本记录](CHANGELOG.md) · [当前维护状态](MAINTAINER.md)
- [验证与限制](docs/validation.md) · [产品方向](PRODUCT.md)

旧任务使用对应固定版本，不自动迁移或删除业务资料。长期可靠性与净收益仍需真实使用验证。

**Feature · Trace · Delivery** · Created by [Perry Wang](https://github.com/P3rryW4ng). 尚未指定开源许可证。
