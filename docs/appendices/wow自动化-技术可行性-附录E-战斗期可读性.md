# 附录 E：Forever Unit API 的 Secret 标记静态分档

版本：2026-09-22 校准版  
数据源：第三方 GitHub 镜像生成文档的项目归档，包括 `UnitDocumentation.lua`、`SecretPredicatesDocumentation.lua`，并参考 Warcraft Wiki 的 Secret Values 语义说明。

> 本附录是静态标记审计，不是运行时能力表。`SecretReturns`、条件 predicate、`SecretContents`、`SecretPayloads`、`Requires*`、taint 和 restricted actions 是不同标记；未标 secret 也不证明值在目标 build、场景或第三方 addon 中可读。

## 一、Secret Values 语义边界

Wiki 资料描述 secret 值在受限执行路径上不能进行部分算术、比较、长度、索引或作为 table key 等操作，并可能在违规操作时导致 Lua 错误。生成文档还使用以下 marker：

- `SecretReturns=true`：静态声明返回 secret。
- `SecretWhen*` / `SecretOn*` / `SecretIn*`：条件 predicate。
- `SecretContents` / `SecretPayloads`：表内容或事件 payload 可能是 secret。
- `Requires*` / `MayReturnNothing`：可能无返回或需要额外条件。
- `SecretArguments`：参数接受规则，不描述返回值是否可读。

运行时记录设计区分 `ERROR`、`NIL`、`SECRET`、`FORBIDDEN` 和正常值。`C_Secrets` 或 `C_RestrictedActions` 的自查结果是旁证，与具体 API 返回和真实场景标签分列。

## 二、A 类：静态声明 `SecretReturns=true`

关键候选包括：

| API | 静态标记 |
|---|---|
| `UnitHealth` | `SecretReturns=true` |
| `UnitHealthMissing` | `SecretReturns=true` |
| `UnitHealthPercent` | `SecretReturns=true`，另有条件 marker |
| `UnitCastingDuration` | `SecretReturns=true`、`MayReturnNothing` |
| `UnitPowerBarTimerInfo` | `SecretReturns=true` |
| `UnitSpellTargetClass` / `UnitSpellTargetName` | `SecretReturns=true` |

这意味着不能预先把这些返回当普通数值做阈值判断。它不证明某个界面像素方案准确，也不证明所有生命/资源相关 API 都有相同标记。

## 三、B 类：带条件 predicate

关键样本：

| API 类别 | 静态 predicate | 待验证问题 |
|---|---|---|
| `UnitHealthMax` | `SecretWhenUnitHealthMaxRestricted` | 对 player/target 等 token 的实际值状态 |
| `UnitPower` / `UnitPowerMax` / `UnitPowerPercent` | Power 相关 predicate | power type、场景和 token 的差异 |
| `UnitCastingInfo` / `UnitChannelInfo` | Cast 相关 predicate | 玩家与非玩家对象的实际返回 |
| `UnitName` / `UnitGUID` / class 类 | Identity 相关 predicate | 身份限制与复合 token |
| Threat 类 | Threat state/value predicate | 单/双 token 组合及值状态 |
| Aura/Cooldown 类 | Aura/Cooldown predicate | combat、地图、PvP 和个别 spell 规则 |
| Spellcast 等事件 | 对应 payload predicate | 事件是否到达及 payload 是否 secret |

predicate 文档中的自然语言只能形成实验假设。不能据此写成“开放世界一定不触发”“玩家的一定可读”或“怪物的一定不可读”。

## 四、C 类：转储未声明 secret 返回守卫

关键样本：

| API | 候选用途 | 仍需验证 |
|---|---|---|
| `UnitExists` | token 是否存在 | 不能单独等同死亡或目标有效 |
| `UnitIsDeadOrGhost` | 死亡/灵魂状态 | token、时序和真实状态一致性 |
| `UnitAffectingCombat` | 战斗状态 | 切换延迟和场景 |
| `UnitDistanceSquared` | 已有 token 的距离 | 单位、NIL/SECRET/ERROR 和可见性 |
| `UnitIsVisible` | 客户端可见状态 | 不等同完整 LOS |
| `UnitIsEnemy` | 敌对关系 | 不等同适合攻击 |
| `UnitLevel` | 等级 | 不等同风险判断 |
| `UnitClassification` 等 | 分类 | 场景和返回稳定性 |

“未声明 secret 返回守卫”只描述转储内容。它不排除 nil、错误、taint、combat lockdown、restricted map、Beta 开关或其他限制。

## 五、视觉候选

当前没有找到可枚举视野内全部敌人的 API。真实画面可能用于敌人集合、血条比例、施法条或动作效果观察，但这些都未采样。不能预先确定：

- 视觉任务只有固定三类；
- OCR、模板或检测模型是否需要；
- 血条比例能满足任何安全阈值；
- 视觉能够替代 secret 值或构成闭环。

Hardcore 不在当前研究目标中。生命值视觉方案的误差和安全含义尚无实测数据。

## 六、运行时测量候选

候选场景包括非战斗、战斗和目标死亡等人工可确认状态。可按 API、unit token 和场景记录参数形状、调用状态、值状态、值类型、限制事件以及人工确认的真实状态。

项目尚未确定具体 API 数量、样本数或通过门槛。单次非空、无事件或 predicate=false 只是一条观察。

## 七、结论

Forever 静态转储显示 Unit 数据存在无条件 secret、条件 secret 和未声明 secret 返回守卫三类表面。它足以形成 T1 能力矩阵，不足以证明状态机输入、视觉工作量、安全策略或自动闭环。
