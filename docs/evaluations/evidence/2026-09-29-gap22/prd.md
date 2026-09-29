# E2E-0531 — 本地查询快照

产品编号：E2E-0531。本次是已有纯 Python 项目的本地函数扩展，不增加 UI、后端接口、网络、持久化或第三方依赖。业务能力为本地查询快照；catalog 负责产品选择与标签，audit 负责事件汇总，shared 的已有收据格式必须保持。

## 产品快照（catalog）
新增公开函数 `product_snapshot(items, category=None)`，放在 src/catalog/query.py。items 是由字典组成的列表。返回 `{"products": [...], "errors": [...]}`。逐项处理，products 保留输入顺序，不去重。

每项按下面次序验证，仅记录该项第一个错误：
1. id 必须是非空字符串（不进行trim）；否则 error 为 `{"index": 从0开始的索引, "reason": "invalid_id"}`。
2. name 必须是字符串，空串允许；否则 reason 为 invalid_name。
3. active 必须是真正的 bool（整数0/1不算）；否则 reason 为 invalid_active。
4. category 必须是字符串，空串允许；否则 reason 为 invalid_category。
5. price 必须是 ASCII 十进制字符串，格式 `[0-9]+(\.[0-9]{1,2})?`，无符号、空白或科学计数法；否则 reason 为 invalid_price。验证不得改变调用方 decimal context。

所有字段先验证，再过滤：active 为 false 的有效项不进products；提供 category 时仅保留category精确相等的项。所有无效项即使不匹配过滤条件也须进入errors。
products 每项恰好为 `{"id": 原id, "label": name前8个Python字符, "price": 两位小数的字符串}`。例：name="ABCDEFGHIJK", price="001.2" -> label="ABCDEFGH", price="1.20"。允许name空串和price="0"。

## 事件快照（audit）
新增公开函数 `event_snapshot(events, start=None, end=None)`，放在 src/audit/summary.py。events 是由字典组成的列表。返回 `{"counts": {kind: 次数}, "accepted_ids": [...], "errors": [...]}`，accepted_ids保留有效首次事件的输入顺序；counts只含实际接受的kind，kind不改写。

每项按下面次序验证，仅记录该项第一个错误：
1. id必须是非空字符串，不trim；否则 invalid_id。
2. kind必须是非空字符串，不trim；否则 invalid_kind。
3. timestamp必须是字符串且严格为ASCII `YYYY-MM-DDTHH:MM:SSZ`，必须是有效日历时刻；否则 invalid_timestamp。
errors格式为 `{"index": 从0开始的索引, "reason": 上述原因}`。

start/end缺省时没有该侧边界；给定时为合法的同格式时刻（调用方会保证合法且start<=end）。时间窗口两端均包含。有效但窗外项跳过，不进入errors。
在验证和时间过滤之后按id去重：同id首次有效且在窗口内的事件胜出；无效项和窗外项不得占用id。因此第一次无效或窗外，后续同id有效且在窗内仍应接受；第二次有效同id即使kind不同也忽略。counts只累计这些接受的事件。

## 应保持的行为与约束
- `receipt_for`依旧使用12字符收据编号；不得随产品8字符label改变。
- `all_product_ids`仍保留所有输入顺序及重复id；`legacy_summary`仍统计全部输入（含重复）。
- 两个新增函数不得修改输入列表/字典，不共享跨调用可变状态，不执行外部读写；相同输入重复调用结果相同。
- 字段缺失按该字段无效处理。items/events列表里的项均为字典；额外字段忽略。未列出的输入类型不在本期契约范围。category参数由调用方保证是字符串或None。
- 所有验收都可在本机通过断言或技术调查验证，不要求真机/视觉/用户目视，不需Figma/API；技术实现选择由Agent在上述契约内决定。
