# 已确认方向与本次实现选择

## A01 证据与工作规格分离

原始来源保留，JSON 工作规格可修订，Markdown 由 JSON 生成。这样保留原始意图和后补证据，避免以 Agent 推断覆盖事实。

## A02 核心与平台分离

PRD、需求状态、决策和追溯属于通用核心；平台命令/约定属于 profile。当前只有 Android 和 Generic；其他平台专属适配须真实项目验证后添加。

## A03 来源按适用性约束

不需要 API/Figma 的功能可以完整交付；需要但尚未提供时为 provisional。not_applicable 必须有理由。

## A04 仓库与运行名

仓库 feature-delivery-skill 表示产品与维护范围；skills/dev 是可自包含分发的 Skill。核心和 profiles 都在里面，避免只安装 Skill 时丢失仓库外依赖。dev 为实际 Skill 名，从而在 Claude 提供 /dev，在 Codex 提供 $dev。

## A05 安装选择

用 Python 标准库复制到官方个人 Skill 目录。无全局 CLAUDE.md 注入，无符号链接依赖。安装标记包含内容哈希；仅更新未修改的自有安装，并保留备份。代价是 git pull 后还须执行一次 --update。

## A06 质量声明

脚本通过不等于功能正确。说明真实实现限制，优先补全契约校验；此前对“完整迁移/强门禁”的宽泛描述不作为事实延续。
