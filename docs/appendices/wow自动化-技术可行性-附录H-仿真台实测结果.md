# 附录 H：离线状态机与契约仿真记录

版本：v4  
代码：`scripts/bot_contract.py`、`scripts/bot_sim.py`  
机器结果：`results/sim_result.json`

## 一、数据性质

该程序没有连接 WoW 客户端。世界、观测、动作、故障和响应均由代码合成。结果文件中的数值是当前代码、参数和 12 个随机种子下的真实机器输出，可用于模型内比较、敏感性分析、契约检查、回归测试和生成真机假设。

这些数值不直接估计 Forever 的击杀、死亡、卡住、恢复、费用、可靠性、安全性或收益。

## 二、v4 修正

v4 相对旧版修复：

1. 云路径不再读取合成世界隐藏的正确逃生方向。
2. `naive` 真正绕过 `validate_decision`；`cloud_validated` 执行结构、白名单、状态陈旧和动作可行性检查。
3. 本地策略不再直接读取 `World` 中的目标坐标和药水冷却，只消费 `Snap`。
4. 阻塞路径等待实际排定的完成时刻，不再另抽一份延迟近似。
5. `Snap.FIELDS` 和 `relevance_hash()` 显式覆盖 `tdir`、`potionReady` 等使用字段。

这些修改消除了已识别的实现偏差，没有增加真实客户端证据。

## 三、模型内结果

每行是 12 个随机种子的平均值。`kills`、`deaths`、`stuck_pct`、`esc_local`、`esc_cloud`、`issued`、`accepted` 和 `quota_denied` 均为合成指标。

| 场景/故障 | 策略 | kills | deaths | stuck % | local escape | cloud escape | issued | accepted | quota denied |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| calm/ok | local_only | 365.17 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 |
| calm/ok | cloud_validated | 365.17 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 |
| calm/ok | naive | 365.17 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 |
| stuck/ok | local_only | 302.00 | 0 | 22.87 | 14.75 | 0 | 0 | 0 | 0 |
| stuck/ok | cloud_validated | 300.83 | 0 | 22.90 | 13.75 | 0.75 | 2 | 0.17 | 0 |
| stuck/ok | naive | 298.17 | 3.92 | 23.54 | 5.50 | 3.83 | 2 | 2 | 4033.08 |
| add/ok | local_only | 329.00 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 |
| add/ok | cloud_validated | 329.00 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 |
| add/ok | naive | 329.00 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0 |
| mixed/mixed | local_only | 253.00 | 0 | 25.32 | 11.42 | 0 | 0 | 0 | 0 |
| mixed/mixed | cloud_validated | 252.50 | 0 | 25.21 | 11.33 | 0.08 | 2 | 0.08 | 0 |
| mixed/mixed | naive | 266.50 | 7.83 | 24.37 | 6.75 | 1.58 | 2 | 1.42 | 4206.75 |
| mixed/ratelimit | local_only | 253.00 | 0 | 25.32 | 11.42 | 0 | 0 | 0 | 0 |
| mixed/ratelimit | cloud_validated | 251.17 | 0 | 25.55 | 11.58 | 0 | 2 | 0 | 0 |
| mixed/ratelimit | naive | 265.00 | 6.00 | 24.92 | 8.83 | 0 | 2 | 0 | 4474.08 |
| mixed/halluc | local_only | 253.00 | 0 | 25.32 | 11.42 | 0 | 0 | 0 | 0 |
| mixed/halluc | cloud_validated | 252.17 | 0 | 25.46 | 11.75 | 0 | 2 | 0 | 0 |
| mixed/halluc | naive | 265.17 | 7.33 | 23.68 | 9.17 | 0 | 2 | 2 | 4081.58 |

完整字段和未四舍五入前的聚合值以 JSON 为准。

## 四、模型内观察

- calm 和 add 场景下三种策略的主要聚合值相同，事件条件没有发起云请求。
- stuck 和 mixed 场景中，策略标签产生了不同的模型内行为。
- `cloud_validated` 在部分场景记录了 stale/rejected；这表明已编码检查分支被执行。
- `naive` 在配额耗尽后持续尝试，产生数千次 `quota_denied`；这是当前本地循环实现的结果。
- 在当前模型中，`naive` 的部分 mixed 行有更高 kills，同时也有非零 deaths 和大量 quota denial。这是模型内权衡，不是实机策略结论。

这些观察可以支持修改合成参数、检查实现和提出真机问题，但外推需要独立证据。

## 五、合成假设与限制

`tdir`、`hpr`、`powerr`、`potionReady`、`stuck`、坐标、距离、冷却和动作效果都是合成字段。云响应是随机/规则生成器，不是实际模型服务。敌人生成、伤害、移动、故障概率和延迟也由代码设置。

模型不包含真实客户端、服务器、地形、画面、addon 限制、输入系统、反作弊或当前在线服务，因此参数变化可以改变表中差异。结果的外部效度尚未建立。
