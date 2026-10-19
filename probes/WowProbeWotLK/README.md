# WowProbeWotLK

3.3.5a 基线只读探针。与 `WowProbeReadOnly`（Forever 目标版）互为对照：在本地私服客户端（WOW_3.3.5a）上记录 3.3.5 时代实际存在的观测表面，为 Forever 限制结论提供"前限制时代"基线。不是 bot，不施法、不移动、不选目标、不交互、不发聊天。

## 与 WowProbeReadOnly 的差异

| 方面 | WowProbeReadOnly (Forever) | WowProbeWotLK (3.3.5a) |
|---|---|---|
| toc Interface | 160001（占位） | 30300 |
| secret 分类 | issecretvalue / C_Secrets 谓词 | 无 secret 概念，仅 NIL/OK/ERROR |
| 位置 | C_Map.GetBestMapForUnit + GetPlayerMapPosition(mapID) | GetZonePoiInfo / GetZoneText / GetPlayerMapPosition("player") |
| Assisted Combat | 四函数实调 | 仅存在性检查（预期 absent_on_335） |
| Forever 专属 API | 实调 | 存在性检查，记 `absent_on_335`，不调用 |
| 经典对照面 | 无 | G8：GetNumSpellTabs / GetSpellBookItemInfo / GetSpellCooldown / 背包 |
| SavedVariables | WowProbe_Report（账号级） | WowProbeWotLK_Report（角色级） |

记录结构（probe_id/sequence/build/scene/monotonic_time/api/args_shape/call_status/value_status/...）与主探针一致，便于同一解析管线处理。

## 使用

1. 拷贝整个目录到客户端 `Interface/AddOns/WowProbeWotLK/`（部署副本，仓库为源）。
2. 角色选择界面勾选启用。
3. 登录后 `/wowprobe once outdoor_still`；手工选目标后 `/wowprobe once target_selected`。
4. 退出后检查 `WTF/Account/<账号>/<realm>/<角色>/SavedVariables/WowProbeWotLK.lua`，确认 `logout_seen=true` 的 run 已落盘。内存赋值不等于文件已写盘。

## 已知注意

- `GetMapFogOfState` 在 3.3.5 可能不存在，预期记 `missing_function`，属观察项而非缺陷。
- 3.3.5 无 `SecureCmdOptionCheck` 类限制事件语义，`ADDON_ACTION_BLOCKED` 计数在此仅作基线对照。
- 主探针的静态检查脚本 `scripts/probe_static_check.py` 同样适用于本探针（禁止调用列表一致）。
