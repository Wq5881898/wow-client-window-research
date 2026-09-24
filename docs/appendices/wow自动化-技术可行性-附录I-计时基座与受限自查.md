# 附录 I：计时、限制状态、小地图与数据出口静态审计

更新：2026-09-23  
数据源：项目归档的 `SystemTimeDocumentation.lua`、`RestrictedActionsDocumentation.lua`、`TimeDocumentation.lua`、`PlayerLocationDocumentation.lua`、`MinimapDocumentation.lua`、`AddOnsDocumentation.lua`。

## 一、计时候选

`C_SystemTime` 转储列出 `GetGameTime`、`GetLocalGameTime`、`GetServerTime`、`GetSessionTime`、`GetTickTime`、`GetTime`、`IsUsingFixedTimeStep`。归档静态文档没有为这些函数列 secret predicate。

由名称和签名不能确定返回单位、精度、单调性、跨 reload 行为、与事件时间的关系或 `IsUsingFixedTimeStep` 的具体语义。这些是运行时未知项。

## 二、限制状态与事件候选

转储列出：

- `CheckAllowProtectedFunctions`
- `GetAddOnRestrictionState`
- `InCombatLockdown`
- `IsAddOnRestrictionActive`
- `AddonActionBlocked` / `AddonActionForbidden`
- `AddonRestrictionStateChanged`
- `MacroActionBlocked` / `MacroActionForbidden`

这些是限制状态和事件的静态表面。事件可能只覆盖特定路径；无事件不证明调用或动作成功，有事件也不记录实际效果本身。

## 三、位置与小地图候选

`PlayerLocationDocumentation.lua` 归档中没有坐标函数；`C_Map.GetPlayerMapPosition` 位于 Map 文档。该分布不能证明它是唯一位置来源。

`C_Minimap` 转储列出 `GetUiMapID`、`GetViewRadius`、tracking 数量/信息、POI 纹理坐标、`MinimapPing`、`MinimapUpdateTracking`、`MinimapUpdateZoom` 等表面。

静态文档没有给出 `GetViewRadius` 的单位和稳定性，也没有证明 tracking 暴露逐图标位置、POI 纹理坐标等于世界位置，或 minimap 能替代画面处理。

## 四、数据路径候选

| 路径 | 静态或机制依据 | 当前未知项 |
|---|---|---|
| SavedVariables | addon 内存数据在正常 reload/logout 时可持久化的机制资料 | 目标 build 的实际持久化时机、延迟、丢失和具体数据范围 |
| 聊天 | `C_ChatInfo.SendChatMessage`，带限制标记 | 调用、限频、频道、日志、隐私和实际到达 |
| 屏显 | addon 可呈现 UI，外部可候选观察像素 | 可读性、遮挡、刷新、采集误差和具体适用范围 |

三条路径彼此独立。内存赋值不等于文件已写盘；发送调用不等于消息到达；屏幕显示不等于外部识别准确。

可以记录的指标包括发送/到达序号、丢失、重复、乱序和延迟分布。项目当前没有真实样本，也没有依据把 100 条、1% 或 p95 500 ms 设为通用门槛。

## 五、其他事实

- `GetScriptsDisallowedForBeta` 的运行时值尚未取得。
- 在线端点已有少量秒到数十秒延迟样本，见附录 G。
- 外部输入仪器有 dry-run 记录，但未发送真实输入。
- `sources/参考原始资料/SavedVariables_刷新语义_wiki.md` 有归档内容；`SaveAddOnVariables_wiki.md`、`SaveRegisteredAddOns_wiki.md` 是本次抓取的空壳页。
