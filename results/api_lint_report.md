# API 静态对账结果

生成：2026-09-24T00:34:46.739064+00:00  
来源：项目本地归档的第三方 GitHub 镜像生成文档，共 31 份；不是从本机已安装客户端直接提取，静态存在性不代表真机可用。

## 摘要

- 调用：{'OK': 47}
- 事件：{'OK': 8}
- 枚举假设：{'OK': 2, 'MISSING_EXPECTED_FIELDS': 1}
- 旧设计中需改为完整命名空间：19 项
- 非 WoW API / 仍需运行时验证：6 项

## 调用

| 组 | 规范名称 | 计划参数数 | 签名 | 状态 | 转储位置 | 备注 |
|---|---|---:|---|---|---|---|
| G1 | `GetBuildInfo` | 0 | 0..0 | OK | `BuildDocumentation.lua:9` | client build/version |
| G1 | `C_AddOns.GetAddOnSecurity` | 1 | 1..1 | OK | `AddOnsDocumentation.lua:225` | addon name |
| G1 | `C_AddOns.GetScriptsDisallowedForBeta` | 0 | 0..0 | OK | `AddOnsDocumentation.lua:264` | old design omitted namespace；原文 `GetScriptsDisallowedForBeta`，实现须用规范名 |
| G1 | `C_RestrictedActions.GetAddOnRestrictionState` | 1 | 1..1 | OK | `RestrictedActionsDocumentation.lua:28` | old design omitted namespace；原文 `GetAddOnRestrictionState`，实现须用规范名 |
| G1 | `C_RestrictedActions.IsAddOnRestrictionActive` | 1 | 1..1 | OK | `RestrictedActionsDocumentation.lua:54` | old design omitted namespace；原文 `IsAddOnRestrictionActive`，实现须用规范名 |
| G1 | `InCombatLockdown` | 0 | 0..0 | OK | `RestrictedActionsDocumentation.lua:44` | global API |
| G2 | `GetTime` | 0 | 0..0 | OK | `SystemTimeDocumentation.lua:56` | global API |
| G2 | `GetServerTime` | 0 | 0..0 | OK | `SystemTimeDocumentation.lua:29` | global API |
| G2 | `GetSessionTime` | 0 | 0..0 | OK | `SystemTimeDocumentation.lua:38` | global API |
| G2 | `GetTickTime` | 0 | 0..0 | OK | `SystemTimeDocumentation.lua:47` | global API |
| G2 | `IsUsingFixedTimeStep` | 0 | 0..0 | OK | `SystemTimeDocumentation.lua:65` | global API |
| G3 | `C_Map.GetBestMapForUnit` | 1 | 1..1 | OK | `MapDocumentation.lua:48` | player |
| G3 | `C_Map.GetPlayerMapPosition` | 2 | 2..2 | OK | `MapDocumentation.lua:436` | old design omitted namespace on second call；原文 `GetPlayerMapPosition`，实现须用规范名 |
| G4 | `UnitHealth` | 1 | 1..2 | OK | `UnitDocumentation.lua:1525` | unit token |
| G4 | `UnitHealthMax` | 1 | 1..1 | OK | `UnitDocumentation.lua:1471` | unit token |
| G4 | `UnitPower` | 1 | 1..3 | OK | `UnitDocumentation.lua:2731` | optional power type omitted |
| G4 | `UnitPowerMax` | 1 | 1..3 | OK | `UnitDocumentation.lua:2800` | optional power type omitted |
| G4 | `UnitCastingInfo` | 1 | 1..1 | OK | `UnitDocumentation.lua:827` | unit token |
| G4 | `UnitChannelInfo` | 1 | 1..1 | OK | `UnitDocumentation.lua:869` | unit token |
| G4 | `UnitExists` | 1 | 0..1 | OK | `UnitDocumentation.lua:1191` | unit token |
| G4 | `UnitIsDeadOrGhost` | 1 | 1..1 | OK | `UnitDocumentation.lua:1930` | unit token |
| G4 | `UnitDistanceSquared` | 1 | 1..1 | OK | `UnitDocumentation.lua:1107` | unit token |
| G4 | `UnitAffectingCombat` | 1 | 1..1 | OK | `UnitDocumentation.lua:613` | unit token |
| G4 | `UnitLevel` | 1 | 1..1 | OK | `UnitDocumentation.lua:2473` | unit token |
| G4 | `UnitIsEnemy` | 2 | 2..2 | OK | `UnitDocumentation.lua:1945` | player and observed unit |
| G4 | `C_Secrets.ShouldUnitHealthMaxBeSecret` | 1 | 1..1 | OK | `dump_SecretPredicateAPIDocumentation.lua:288` | expanded from non-callable wildcard；原文 `C_Secrets.Should*BeSecret`，实现须用规范名 |
| G4 | `C_Secrets.ShouldUnitPowerBeSecret` | 1 | 1..2 | OK | `dump_SecretPredicateAPIDocumentation.lua:320` | expanded from non-callable wildcard；原文 `C_Secrets.Should*BeSecret`，实现须用规范名 |
| G4 | `C_Secrets.ShouldUnitPowerMaxBeSecret` | 1 | 1..2 | OK | `dump_SecretPredicateAPIDocumentation.lua:337` | expanded from non-callable wildcard；原文 `C_Secrets.Should*BeSecret`，实现须用规范名 |
| G4 | `C_Secrets.ShouldUnitSpellCastingBeSecret` | 1 | 1..1 | OK | `dump_SecretPredicateAPIDocumentation.lua:371` | expanded from non-callable wildcard；原文 `C_Secrets.Should*BeSecret`，实现须用规范名 |
| G5 | `TargetNearestEnemy` | 0 | 0..1 | OK | `TargetScriptDocumentation.lua:117` | optional reverse omitted |
| G5 | `AttackTarget` | 0 | 0..0 | OK | `TargetScriptDocumentation.lua:21` | global API |
| G5 | `IsTargetLoose` | 0 | 0..0 | OK | `TargetScriptDocumentation.lua:49` | global API |
| G6 | `C_WorldLootObject.GetWorldLootObjectDistanceSquared` | 1 | 1..1 | OK | `WorldLootObjectDocumentation.lua:26` | unit token |
| G6 | `C_WorldLootObject.IsWorldLootObjectInRange` | 1 | 1..1 | OK | `WorldLootObjectDocumentation.lua:103` | old design omitted namespace；原文 `IsWorldLootObjectInRange`，实现须用规范名 |
| G6 | `C_Container.CalculateTotalNumberOfFreeBagSlots` | 0 | 0..0 | OK | `ContainerDocumentation.lua:10` | no arguments |
| G6 | `C_Container.GetContainerItemDurability` | 2 | 2..2 | OK | `ContainerDocumentation.lua:139` | old design omitted namespace；原文 `GetContainerItemDurability`，实现须用规范名 |
| G7 | `C_AssistedCombat.IsAvailable` | 0 | 0..0 | OK | `AssistedCombatDocumentation.lua:43` | no arguments |
| G7 | `C_AssistedCombat.GetRotationSpells` | 0 | 0..0 | OK | `AssistedCombatDocumentation.lua:34` | old design omitted namespace；原文 `GetRotationSpells`，实现须用规范名 |
| G7 | `C_AssistedCombat.GetNextCastSpell` | 0 | 0..1 | OK | `AssistedCombatDocumentation.lua:19` | optional checkForVisibleButton omitted；原文 `GetNextCastSpell`，实现须用规范名 |
| G8 | `C_ChatInfo.SendChatMessage` | 4 | 1..4 | OK | `ChatInfoDocumentation.lua:563` | channel form; old design omitted namespace；原文 `SendChatMessage`，实现须用规范名 |
| G9 | `C_Minimap.GetViewRadius` | 0 | 0..0 | OK | `MinimapDocumentation.lua:126` | returns yards in the static documentation |
| G9 | `C_Minimap.GetUiMapID` | 0 | 0..0 | OK | `MinimapDocumentation.lua:117` | old design omitted namespace；原文 `GetUiMapID`，实现须用规范名 |
| G9 | `C_Minimap.GetNumTrackingTypes` | 0 | 0..0 | OK | `MinimapDocumentation.lua:60` | old design omitted namespace；原文 `GetNumTrackingTypes`，实现须用规范名 |
| G9 | `C_Minimap.GetTrackingInfo` | 1 | 1..1 | OK | `MinimapDocumentation.lua:102` | old design omitted namespace；原文 `GetTrackingInfo`，实现须用规范名 |
| G9 | `C_Minimap.SetTracking` | 2 | 2..2 | OK | `MinimapDocumentation.lua:233` | old design omitted namespace；原文 `SetTracking`，实现须用规范名 |
| G10 | `C_AddOnProfiler.IsEnabled` | 0 | 0..0 | OK | `AddOnProfilerDocumentation.lua:120` | concrete replacement for vague reference；原文 `AddOnProfiler related API`，实现须用规范名 |
| G10 | `C_AddOnProfiler.GetAddOnMetric` | 2 | 2..2 | OK | `AddOnProfilerDocumentation.lua:44` | addon name and metric enum；原文 `AddOnProfiler related API`，实现须用规范名 |

## 事件

| 组 | 事件字面量 | 状态 | 转储位置 |
|---|---|---|---|
| G1 | `ADDON_ACTION_BLOCKED` | OK | `RestrictedActionsDocumentation.lua:74` |
| G1 | `ADDON_ACTION_FORBIDDEN` | OK | `RestrictedActionsDocumentation.lua:85` |
| G1 | `ADDON_RESTRICTION_STATE_CHANGED` | OK | `RestrictedActionsDocumentation.lua:96` |
| G1 | `MACRO_ACTION_BLOCKED` | OK | `RestrictedActionsDocumentation.lua:108` |
| G1 | `MACRO_ACTION_FORBIDDEN` | OK | `RestrictedActionsDocumentation.lua:118` |
| G6 | `LOOT_OPENED` | OK | `LootDocumentation.lua:217` |
| G6 | `LOOT_CLOSED` | OK | `LootDocumentation.lua:186` |
| G9 | `MINIMAP_UPDATE_TRACKING` | OK | `MinimapDocumentation.lua:271` |

## 枚举假设

| 组 | 枚举 | 期望成员 | 缺失成员 | 状态 | 来源 |
|---|---|---|---|---|---|
| G1 | `Enum.AddOnRestrictionType` | `Combat`, `Encounter`, `ChallengeMode`, `PvPMatch`, `Map`, `Chat` | - | OK | `RestrictedActionsConstantsDocumentation.lua` |
| G6 | `Enum.PlayerInteractionType` | `Herbalism`, `Mining`, `Skinning`, `GameObjectLoot` | `Herbalism`, `Mining`, `Skinning`, `GameObjectLoot` | MISSING_EXPECTED_FIELDS | `PlayerInteractionManagerConstantsDocumentation.lua` |
| G10 | `Enum.AddOnProfilerMetric` | `RecentAverageTime`, `PeakTime`, `CountTimeOver1Ms` | - | OK | `AddOnProfilerConstantsDocumentation.lua` |

## 非 API 与未闭合项

- **G2 `OnUpdate`**：frame script callback; runtime measurement required
- **G5 `SendInput`**：Windows input API, not a WoW Lua API
- **G5 `hwevent`**：runtime execution-context property, not a callable API
- **G8 `SavedVariables`**：persistence mechanism, not a callable API
- **G8 `Logs/WoWChatLog.txt`**：client file output, requires runtime measurement
- **G9 `minimap icon coordinates`**：no named API is specified in the probe design

## 静态结论边界

- `OK` 只说明名称及计划参数数与项目归档的第三方镜像生成文档一致。
- 镜像分支、目标客户端 build 和运行时文档可能不同；目标 build 和对应文档尚未取得。
- `SecretArguments`、`HasRestrictions` 和返回值限制仍须在目标客户端、目标场景中测试。
- 无拦截事件不等于成功；实际返回/动作与 NIL、SECRET、ERROR、FORBIDDEN 是不同的运行时记录字段。
- SavedVariables、聊天日志、外部输入和小地图图标坐标均不能由本报告证明可用。
