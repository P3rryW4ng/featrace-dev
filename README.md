# FeatraceDev

**简体中文** | [English](README.en.md)

面向 **Claude Code 和 Codex** 的开发 Skill，用于在现有项目中实现需求、修复问题和验证改动。它沿代码定位影响范围，按需选择检查，并记录可用于接续的证据。

[安装](#安装) · [使用示例](#使用示例) · [更新与文档](#更新与文档)

## 安装

本发布包 **0.34.4**。需要 Python 3.9+、Git 和对应 Agent；项目构建环境沿用项目要求。

```bash
git clone --branch release/0.34.4 --single-branch https://github.com/P3rryW4ng/featrace-dev.git
cd featrace-dev
python3 scripts/install.py --agent claude
```

Codex 将 `claude` 换成 `codex`；两端都安装用 `both`。安装后打开目标项目的新会话。

## 使用示例

在目标项目中打开新会话。Claude Code 输入 `/dev`，Codex 输入 `$dev`，然后按平常方式描述需求。

以下是 Claude Code 的模拟会话节选。Codex 中将 `/dev` 换成 `$dev`。

**修复问题**

```text
❯ /dev
FeatraceDev ON · 项目：store-web · 版本：0.34.4

❯ 登录失败时页面显示空白。修复错误提示，并验证成功和失败两条路径。
FeatraceDev ON · 项目：store-web
已定位到登录页的错误状态。接下来修改提示并运行登录相关测试。

FeatraceDev ON · 项目：store-web
已修复登录失败时的提示。登录相关测试 2 项通过，未进行浏览器走查。
```

**实现小需求**

```text
❯ /dev
FeatraceDev ON · 项目：store-web · 版本：0.34.4

❯ 给订单列表加“仅显示未完成”筛选，默认展示全部。
FeatraceDev ON · 项目：store-web
订单列表共用分页查询。切换筛选时会回到第一页。

FeatraceDev ON · 项目：store-web
已添加筛选。默认展示、筛选切换和分页测试均通过。
```

**接续已有任务**

```text
❯ /dev
FeatraceDev ON · 项目：store-web · 版本：0.34.4

❯ 继续订单筛选任务。先查已有验证，只补缺失的检查。
FeatraceDev ON · 项目：store-web
已恢复订单筛选任务。筛选结果仍适用，只剩分页检查。

FeatraceDev ON · 项目：store-web
分页检查通过，沿用了原筛选结果。任务已结项。
```

提供必要的需求原文、设计或复现步骤即可。空调用只开启模式并显示已安装版本，输入 `dev off` 退出。结项时会报告实际交付、验证和剩余限制。

## 更新与文档

更新前保留本地改动，获取并切换到固定发布引用 `release/0.34.4`，再运行 `python3 scripts/install.py --agent claude --update`。旧发布分支上直接 `git pull` 不会升级版本。安装器保留旧版备份，拒绝覆盖被修改的副本。

- [使用与接续](docs/usage.md) · [模块与流程](docs/module-guide.md)
- [版本记录](CHANGELOG.md) · [当前维护状态](MAINTAINER.md)
- [验证与限制](docs/validation.md) · [产品方向](PRODUCT.md)

0.34.4 使用合同 10。接续合同 9 的任务请使用固定版本 0.33.3。其他旧合同的接续说明见[使用指南](docs/usage.md)。

**Feature · Trace · Delivery** · Created by [Perry Wang](https://github.com/P3rryW4ng). 尚未指定开源许可证。
