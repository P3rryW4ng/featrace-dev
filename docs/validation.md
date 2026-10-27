# 当前验证与历史查证入口

核对：2026-10-27。当前正式及CC为0.30.0合同6。这里只索引仍需使用的证据；不把旧执行记作本轮新跑，不从测试数量推算成熟度或收益。身份见[MAINTAINER](../MAINTAINER.md)，阶段出口见[ROADMAP](../ROADMAP.md)。

## 当前验证入口

| 要核对什么 | 原始依据 | 准确边界 |
|---|---|---|
| 完整343项程序回归 | [最终结果及输入摘要](evaluations/contract6-build-20261027/retirement-result.json) | 134.695秒；运行/测试输入冻结。中间317/335/341不能掩盖随后发现的问题；发布只改元数据和文档，未重复不变套件 |
| 受控环境纵切 | [环境结果](evaluations/contract6-build-20261027/environment-result.json) | 真正传入选定变量、固定PATH/工具字节及后检；不保证发现动态依赖或构成OS沙箱 |
| 独立源码纠错 | [初审](evaluations/contract6-build-20261027/source-review.json)、[差异复核](evaluations/contract6-build-20261027/source-review-followup.json)、[定点最终复核](evaluations/contract6-build-20261027/source-review-final.json) | 两项发现及一项归属残留已修正；审查者未运行测试，不冒充实测 |
| 新上下文前向演练 | [合同6演练](evaluations/contract6-build-20261027/forward-result.json) | 合成任务实际2次检查（1通过、1失败）、2次入口拒绝；保留失败/代码/交接并retired，非交付、非自然业务 |
| 正式发布与CC安装 | [0.30.0核验](evaluations/release-0300-20261027.json) | 固定729f473远端匹配，双宿主隔离/日常CC各15文件；旧0.29.0备份完整，个人Codex和业务未动 |
| 接续、中断、清理及规模对照 | [0.29.0隔离结果](evaluations/phase2-isolated-20261027/results.json)、[报告](reviews/2026-10-27-phase2-isolated-result.md) | 原版本合成结果，含模拟保留期、真实父进程终止及200/800草稿；不是自然压缩、真实7天或净成本证明 |
| 为什么替换环境/生命周期 | [底层评审](reviews/2026-10-27-environment-lifecycle-review.md)、[因果结果](evaluations/environment-lifecycle-review-20261027/results.json) | 评审时未实施；当前已按[合同6方案](designs/controlled-environment-retirement.md)实现，不能再拿其中“待确认”当待办 |
| 维护清理本身 | 见本页末节和本轮维护提交 | 只核对链接、来源保留、当前口径、隐私及冻结字节；不因此重跑业务/程序 |

## 自然反馈与专项能力

- 9058是用户转回的0.28.0自然报告；[授权/资料评审](reviews/2026-10-26-authorization-input-review.md)保留归因。维护未独立读取业务原件，不能作为0.30.0自然验证。
- 9060–9062是原版本失败误解除的反馈；[核对](reviews/2026-10-26-ogfr9060-field-review.md)与[原修正结果](evaluations/failure-lifecycle-20261026/result.json)保留负面来源，不重签或重开业务。
- 8897初评与定向更正的不同证据等级见[清理前索引](https://github.com/P3rryW4ng/featrace-dev/blob/0fcf9a4a47268f2ded65a48e80dd5f15fcd5a3f0/docs/validation.md)。新增自动回归资产缺失不自动等于当次证据不足，具体静态链条与运行事实分别判断。
- Figma适配[既有核对](evaluations/figma-adapter-20261022.json)证明指引/条件入口，不证明真实连接或设计还原；Android的UP-TO-DATE、包/设备身份仍须在实际任务核对。
- 能力评分采用[当前标准](capabilities.md)及[场景映射](../tests/capability-cases.json)，原分数是其采集截点，不随新版本自动提高。

## 未证明的边界

自然压缩后的恢复、自然长期语义可靠性、同质量同范围净成本、全动态依赖、跨机器/Windows与大团队并发仍未知。官方quick_validate在合同6开发时因PyYAML缺失不可用；必要前置字段另核对，不宣称该标准检查成功。有限扫描no_matches不是全面隐私保证，源码候选人工处置与原失败保留在结果中，图像另审。

## 历史证据如何查

[清理前完整索引](https://github.com/P3rryW4ng/featrace-dev/blob/0fcf9a4a47268f2ded65a48e80dd5f15fcd5a3f0/docs/validation.md)保留逐版日志/输入/失败/版本引用；只有实际查证某次变化时选择读取。docs/evaluations和日期reviews的原件未删除、不改写通过/失败；它们是证据，不是当前执行清单。旧1–5任务使用固定原工具，不因新版或本文清理自动迁移、补测或认证。

当前实现的日常路径见[usage](usage.md)、[运行指引](../skills/dev/core/references/task-workflow.md)、[模块与运行甘特图](module-guide.md)。

## 2026-10-27文档清理

当前MAINTAINER/ROADMAP/本页退出重复的已完成“待开发/待发布”接续段；旧合同5设计从当前树移除并改用已推送固定引用。保留有效规则、稳定GAP、源码/测试、原失败与验证原件；未改运行/安装文件、业务数据或Git历史。本轮新增的甘特图仅解释相对时序，不提供实际耗时或新增固定阶段要求。
