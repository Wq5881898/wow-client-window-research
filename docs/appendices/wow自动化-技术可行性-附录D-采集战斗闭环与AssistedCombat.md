# 附录 D：Forever 目标、战斗、采集与 Assisted Combat 静态审计

版本：2026-09-22 校准版  
数据源同附录 C：第三方 GitHub 镜像的生成文档与 `sources/forever_dumps/` 归档。

> 本附录记录静态 API 表面，不是目标客户端运行时结果。

## 一、Assisted Combat 候选

`AssistedCombatDocumentation.lua` 列出：

| 成员 | 类型 | 静态标记 |
|---|---|---|
| `GetRotationSpells` | Function | 无附加标记 |
| `GetNextCastSpell` | Function | `SecretArguments: AllowedWhenUntainted` |
| `GetActionSpell` | Function | 无附加标记 |
| `IsAvailable` | Function | 无附加标记 |
| `AssistedCombatActionSpellCast` | Event | 无附加标记 |

`GetNextCastSpell` 的返回类型为可空 `spellID`。这使它值得进入 G7，但不能推出：

- 第三方 addon 在 Forever 中可得到非空、非秘密值；
- 返回值等于完整或正确的职业循环；
- 可以省掉内容维护或视觉；
- 官方提供接口等于授权外部执行或商业使用。

运行时尚未取得这些状态下的返回样本、失败分类或场景一致性数据。单次有效值也不足以描述跨场景行为。

## 二、目标与攻击动作表面

`TargetScriptDocumentation.lua` 列出 `TargetNearestEnemy`、`AttackTarget`、`ClearTarget`、`TargetLastTarget`、`IsTargetLoose` 等名称。

当前边界：

- `TargetNearestEnemy` 不是敌人集合 API，不提供每个敌人的位置、种类、LOS、搜索半径或 ADD 风险。
- `AttackTarget` 是动作表面，不证明第三方 addon 或外部输入可以触发实际攻击。
- `IsTargetLoose` 的名称不证明它等价于目标死亡、丢失或不可攻击。
- 项目尚未对这些动作记录调用状态、限制事件和实际效果；输入生效与授权仍是不同问题。
- 外部输入被客户端接收、被归类为硬件事件或没有限制事件，都不等于获得授权。

## 三、采集、拾取和背包候选

归档中存在以下静态表面：

- `C_WorldLootObject`：距离平方、是否在范围内、对象信息等。
- `PlayerInteractionManager`：NPC 交互状态和 frame show/hide 事件等。
- `C_Container`：格数、空格、物品、耐久等。
- `Loot`：`LootOpened`、`LootClosed`、`LootItemAvailable` 等事件。
- `AutoLoot`：自动拾取切换候选。

这些名称没有解决对象如何被发现、对象类型如何确认、交互是否开始、拾取是否完成或动作是否被允许。

G6 的旧假设已被静态否定：`Enum.PlayerInteractionType` 的 81 个成员中没有 `Herbalism`、`Mining`、`Skinning`、`GameObjectLoot`。`LootOpened/LootClosed` 也只能说明拾取界面事件发生，不能证明对象属于某种采集类型。

采集不属于当前讨论的固定目标场景。项目尚无替代枚举或采集运行时探针，相关静态接口也尚未组成已验证闭环。

## 四、战斗日志候选

`CombatLogSecureDocumentation.lua` 列出 `CreateCombatLogMessage`、`GetCurrentEntryInfo`、`GetCurrentEventInfo`、过滤和翻页函数，以及 `CombatLogMessage` 等事件。

这只证明 secure 形态的日志表面存在。命中、暴击、目标死亡和伤害统计能否从第三方 addon 稳定取得，仍受具体返回、Secret/Payload 标记、场景和事件语义影响；不能从函数名推定。

## 五、能力矩阵

| 需要的信息 | 静态候选 | 当前边界 |
|---|---|---|
| 玩家地图坐标 | `C_Map.GetPlayerMapPosition` | 待 G3 测可读率、缺口和抖动 |
| 地图 ID | `C_Map.GetBestMapForUnit` | 待 G3 验证返回与场景 |
| 玩家手工选择后的目标状态 | Unit API、`C_Secrets` | 待 G4 分别记录 call/value/event/effect |
| 选择最近敌人 | `TargetNearestEnemy` | 动作表面；不是敌人感知；不在 T1 |
| 开始攻击 | `AttackTarget` | 动作表面；尚无运行时效果记录 |
| 目标是否“松脱” | `IsTargetLoose` | 语义未知，不能替代死亡/失效判据 |
| 下一个技能候选 | `C_AssistedCombat.GetNextCastSpell` | 待 G7 验证第三方返回和场景一致性 |
| 世界物体距离 | `C_WorldLootObject` | 对象发现与值可读性未解决 |
| 交互/拾取状态 | Interaction 与 Loot 事件 | 对象类型、效果和完成判据未解决 |
| 背包/耐久 | `C_Container` | 静态存在；采集场景暂不执行 |
| 血量/资源/光环/冷却 | Unit、Aura、Spell 候选 | Secret 标记各异，不能统称可用 |
| 视野内敌人集合 | 未找到枚举全部敌人的 API | 视觉是候选，但也未验证 |

## 六、运行时观察维度

位置、目标状态、Assisted Combat、动作、采集和战斗日志是可分别观察的主题。对动作类候选，调用返回、客户端限制事件、实际效果和意外效果需要分列记录，因为其中任一项都不能替代其他项。

项目目前没有这些主题的目标客户端记录，也没有静态证据要求它们必须按固定 T1/T2/T3 顺序研究。
