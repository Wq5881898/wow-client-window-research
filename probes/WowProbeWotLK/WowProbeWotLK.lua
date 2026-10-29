-- WowProbeWotLK
-- 3.3.5a baseline read-only recorder. Companion of WowProbeReadOnly (Forever target).
-- Purpose: record which observation surfaces exist on a classic 3.3.5a client, so
-- Forever-era findings can be contrasted against a pre-restriction baseline.
-- Not a bot. Does not cast, move, target, attack, interact, or send chat.
--
-- Slash:
--   /wp once [scene]         one snapshot (short alias, /wowprobe also works)
--   /wp status               record counts
--   /wp stop                 halt this session
-- Console (no chat needed): WowProbeWotLK_AutoOnce = true  -> snapshot on load

local ADDON_NAME = "WowProbeWotLK"
local MAX_RECORDS = 4000

WowProbeWotLK_Report = WowProbeWotLK_Report or { schema = "wowprobe-wotlk-v1", runs = {} }

local run
local seq = 0
local stopped = false
local event_counts = {}

local UNIT_TOKENS = { "player", "target" }

-- Names that exist only on modern/Forever clients. On 3.3.5a they must be
-- recorded as ABSENT without calling them.
local FOREVER_ONLY_GLOBALS = {
  "issecretvalue", "issecrettable", "IsTargetLoose", "UnitDistanceSquared",
  "Is64BitClient",
}
local FOREVER_ONLY_NAMESPACES = {
  { "C_AddOns", "GetAddOnSecurity" },
  { "C_AddOns", "GetScriptsDisallowedForBeta" },
  { "C_RestrictedActions", "GetAddOnRestrictionState" },
  { "C_RestrictedActions", "IsAddOnRestrictionActive" },
  { "C_Secrets", "ShouldUnitHealthMaxBeSecret" },
  { "C_Secrets", "ShouldUnitPowerBeSecret" },
  { "C_Secrets", "ShouldUnitPowerMaxBeSecret" },
  { "C_Secrets", "ShouldUnitSpellCastingBeSecret" },
  { "C_AssistedCombat", "IsAvailable" },
  { "C_AssistedCombat", "GetNextCastSpell" },
  { "C_AssistedCombat", "GetActionSpell" },
  { "C_AssistedCombat", "GetRotationSpells" },
  { "C_Map", "GetBestMapForUnit" },
  { "C_Map", "GetPlayerMapPosition" },
}

local function monotonic()
  if GetTime then
    local ok, t = pcall(GetTime)
    if ok and type(t) == "number" then
      return t
    end
  end
  return nil
end

local function persistable(value)
  local ty = type(value)
  if ty == "number" or ty == "boolean" then
    return value
  end
  if ty == "string" then
    if string.len(value) > 120 then
      return string.sub(value, 1, 120) .. "..."
    end
    return value
  end
  return nil
end

local function add_record(fields)
  if stopped or not run then
    return
  end
  seq = seq + 1
  if seq > MAX_RECORDS then
    stopped = true
    run.meta.stop_reason = "max_records"
    return
  end
  fields.sequence = seq
  fields.build = run.meta.build
  fields.scene = run.meta.scene
  fields.monotonic_time = monotonic()
  fields.event_status = fields.event_status or "NONE"
  fields.effect = fields.effect or "NOT_APPLICABLE"
  table.insert(run.records, fields)
end

local function record_missing(probe_id, api, args_shape, note)
  add_record({
    probe_id = probe_id,
    api = api,
    args_shape = args_shape,
    call_status = "ERROR",
    value_status = "NOT_APPLICABLE",
    error_text = "missing_function",
    note = note,
  })
end

local function classify_and_store(probe_id, api, args_shape, value, extra_note)
  if value == nil then
    add_record({
      probe_id = probe_id,
      api = api,
      args_shape = args_shape,
      call_status = "RETURNED",
      value_status = "NIL",
      value_type = "nil",
      note = extra_note,
    })
    return
  end
  local ty = type(value)
  if ty == "userdata" then
    add_record({
      probe_id = probe_id,
      api = api,
      args_shape = args_shape,
      call_status = "RETURNED",
      value_status = "OK",
      value_type = "userdata",
      note = extra_note or "userdata_not_persisted",
    })
    return
  end
  add_record({
    probe_id = probe_id,
    api = api,
    args_shape = args_shape,
    call_status = "RETURNED",
    value_status = "OK",
    value_type = ty,
    value = persistable(value),
    note = extra_note,
  })
end

local function call_one(probe_id, api, fn, args_shape, ...)
  if type(fn) ~= "function" then
    record_missing(probe_id, api, args_shape)
    return
  end
  local ok, a, b, c, d, e, f = pcall(fn, ...)
  if not ok then
    add_record({
      probe_id = probe_id,
      api = api,
      args_shape = args_shape,
      call_status = "ERROR",
      value_status = "NOT_APPLICABLE",
      error_text = tostring(a),
    })
    return
  end
  classify_and_store(probe_id, api, args_shape, a)
  if b ~= nil then
    classify_and_store(probe_id, api .. "#2", args_shape, b)
  end
  if c ~= nil then
    classify_and_store(probe_id, api .. "#3", args_shape, c)
  end
  if d ~= nil then
    classify_and_store(probe_id, api .. "#4", args_shape, d)
  end
  if e ~= nil then
    classify_and_store(probe_id, api .. "#5", args_shape, e)
  end
  if f ~= nil then
    classify_and_store(probe_id, api .. "#6", args_shape, f)
  end
end

local function ns_get(root, name)
  if type(root) ~= "table" then
    return nil
  end
  return root[name]
end

-- G1: build metadata plus presence/absence of Forever-only surfaces.
local function snapshot_g1()
  call_one("G1.build", "GetBuildInfo", GetBuildInfo, {})
  call_one("G1.lockdown", "InCombatLockdown", InCombatLockdown, {})
  local i
  for i = 1, #FOREVER_ONLY_GLOBALS do
    local name = FOREVER_ONLY_GLOBALS[i]
    if _G[name] == nil then
      add_record({
        probe_id = "G1.absent." .. name,
        api = name,
        args_shape = {},
        call_status = "ERROR",
        value_status = "NOT_APPLICABLE",
        error_text = "absent_on_335",
      })
    else
      add_record({
        probe_id = "G1.absent." .. name,
        api = name,
        args_shape = {},
        call_status = "RETURNED",
        value_status = "OK",
        value_type = type(_G[name]),
        note = "present_unexpectedly_on_335",
      })
    end
  end
  local j
  for j = 1, #FOREVER_ONLY_NAMESPACES do
    local ns_name = FOREVER_ONLY_NAMESPACES[j][1]
    local fn_name = FOREVER_ONLY_NAMESPACES[j][2]
    local api = ns_name .. "." .. fn_name
    if _G[ns_name] == nil or _G[ns_name][fn_name] == nil then
      add_record({
        probe_id = "G1.absent." .. api,
        api = api,
        args_shape = {},
        call_status = "ERROR",
        value_status = "NOT_APPLICABLE",
        error_text = "absent_on_335",
      })
    else
      add_record({
        probe_id = "G1.absent." .. api,
        api = api,
        args_shape = {},
        call_status = "RETURNED",
        value_status = "OK",
        value_type = "function",
        note = "present_unexpectedly_on_335",
      })
    end
  end
end

local function snapshot_g2()
  call_one("G2.time", "GetTime", GetTime, {})
  call_one("G2.server", "GetServerTime", GetServerTime, {})
  call_one("G2.session", "GetSessionTime", GetSessionTime, {})
  call_one("G2.tick", "GetTickTime", GetTickTime, {})
end

-- G3: position via 3.3.5-era APIs. GetPlayerMapPosition returns a literal
-- table {x, y}; expand explicitly.
local function snapshot_g3()
  call_one("G3.continent", "GetZonePoiInfo#1", GetZonePoiInfo, {})
  call_one("G3.zone", "GetZoneText", GetZoneText, {})
  call_one("G3.subzone", "GetSubZoneText", GetSubZoneText, {})
  local ok, x, y = pcall(GetPlayerMapPosition, "player")
  if not ok then
    add_record({
      probe_id = "G3.pos_raw",
      api = "GetPlayerMapPosition",
      args_shape = { "player" },
      call_status = "ERROR",
      value_status = "NOT_APPLICABLE",
      error_text = tostring(x),
    })
  elseif x == nil or y == nil then
    add_record({
      probe_id = "G3.pos_raw",
      api = "GetPlayerMapPosition",
      args_shape = { "player" },
      call_status = "RETURNED",
      value_status = "NIL",
      value_type = "nil",
      note = "no_zone_map",
    })
  else
    add_record({
      probe_id = "G3.pos_raw",
      api = "GetPlayerMapPosition",
      args_shape = { "player" },
      call_status = "RETURNED",
      value_status = "OK",
      value_type = "vector2",
      value = { x = x, y = y },
    })
  end
  call_one("G3.pos_named", "GetPlayerMapPosition", GetPlayerMapPosition, { "player" }, "player")
  call_one("G3.pos_target", "GetPlayerMapPosition", GetPlayerMapPosition, { "target" }, "target")
  call_one("G3.minimap", "Minimap:IsVisible", ns_get(Minimap, "IsVisible"), {})
  call_one("G3.minimap_fow", "GetMapFogOfState", GetMapFogOfState, { "number", "number" }, 0, 0)
end

local function snapshot_g4()
  local i
  for i = 1, #UNIT_TOKENS do
    local unit = UNIT_TOKENS[i]
    local shape = { unit }
    call_one("G4.exists." .. unit, "UnitExists", UnitExists, shape, unit)
    call_one("G4.name." .. unit, "UnitName", UnitName, shape, unit)
    call_one("G4.dead." .. unit, "UnitIsDeadOrGhost", UnitIsDeadOrGhost, shape, unit)
    call_one("G4.combat." .. unit, "UnitAffectingCombat", UnitAffectingCombat, shape, unit)
    call_one("G4.health." .. unit, "UnitHealth", UnitHealth, shape, unit)
    call_one("G4.healthmax." .. unit, "UnitHealthMax", UnitHealthMax, shape, unit)
    call_one("G4.power." .. unit, "UnitPower", UnitPower, shape, unit)
    call_one("G4.powermax." .. unit, "UnitPowerMax", UnitPowerMax, shape, unit)
    call_one("G4.pptype." .. unit, "UnitPowerType", UnitPowerType, shape, unit)
    call_one("G4.level." .. unit, "UnitLevel", UnitLevel, shape, unit)
    call_one("G4.cast." .. unit, "UnitCastingInfo", UnitCastingInfo, shape, unit)
    call_one("G4.aura.count." .. unit, "GetUnitDebuffsCount", GetUnitDebuffsCount, shape, unit)
    if unit ~= "player" then
      call_one("G4.enemy." .. unit, "UnitIsEnemy", UnitIsEnemy, { "player", unit }, "player", unit)
    end
  end
  call_one("G4.guid.player", "UnitGUID", UnitGUID, { "player" }, "player")
  call_one("G4.guid.target", "UnitGUID", UnitGUID, { "target" }, "target")
  call_one("G4.range.target", "CheckInteractDistance", CheckInteractDistance, { "target", "number" }, "target", 4)
  call_one("G4.buff_count.player", "GetUnitBuffCount", GetUnitBuffCount, { "player" }, "player")
end

-- G7: Assisted Combat surface on 3.3.5a (expected fully absent).
local function snapshot_g7()
  local ac = C_AssistedCombat
  call_one("G7.available", "C_AssistedCombat.IsAvailable", ns_get(ac, "IsAvailable"), {})
  call_one("G7.next", "C_AssistedCombat.GetNextCastSpell", ns_get(ac, "GetNextCastSpell"), {})
  call_one("G7.action", "C_AssistedCombat.GetActionSpell", ns_get(ac, "GetActionSpell"), {})
  call_one("G7.rotation", "C_AssistedCombat.GetRotationSpells", ns_get(ac, "GetRotationSpells"), {})
end

-- G8: classic-era spellbook surface, the 3.3.5 analogue of Forever spell reads.
-- GetSpellTabInfo returns 5 values, so it goes through a custom capture.
local function snapshot_g8()
  local ok, n = pcall(GetNumSpellTabs)
  if not ok then
    add_record({
      probe_id = "G8.tabs",
      api = "GetNumSpellTabs",
      args_shape = {},
      call_status = "ERROR",
      value_status = "NOT_APPLICABLE",
      error_text = tostring(n),
    })
    return
  end
  add_record({
    probe_id = "G8.tabs",
    api = "GetNumSpellTabs",
    args_shape = {},
    call_status = "RETURNED",
    value_status = "OK",
    value_type = "number",
    value = persistable(n),
  })
  local i
  for i = 1, 4 do
    local ok2, a, b, c, d, e = pcall(GetSpellTabInfo, i)
    if not ok2 then
      add_record({
        probe_id = "G8.tab." .. i,
        api = "GetSpellTabInfo",
        args_shape = { "number" },
        call_status = "ERROR",
        value_status = "NOT_APPLICABLE",
        error_text = tostring(a),
      })
    else
      add_record({
        probe_id = "G8.tab." .. i,
        api = "GetSpellTabInfo",
        args_shape = { "number" },
        call_status = "RETURNED",
        value_status = (a == nil) and "NIL" or "OK",
        value_type = "multi",
        value = {
          name = persistable(a),
          icon = persistable(b),
          offset = persistable(c),
          num_spells = persistable(d),
          tab_id = persistable(e),
        },
      })
    end
  end
  call_one("G8.bookslot", "GetSpellBookItemInfo", GetSpellBookItemInfo, { "number", "string" }, 1, "spell")
  call_one("G8.bookname", "GetSpellBookItemName", GetSpellBookItemName, { "number", "string" }, 1, "spell")
  call_one("G8.cooldown", "GetSpellCooldown", GetSpellCooldown, { "number", "string" }, 1, "spell")
  call_one("G8.bag_items", "GetContainerNumSlots", GetContainerNumSlots, { "number" }, 0)
end

local function snapshot()
  if not run or stopped then
    return
  end
  snapshot_g1()
  snapshot_g2()
  snapshot_g3()
  snapshot_g4()
  snapshot_g7()
  snapshot_g8()
  run.meta.last_sequence = seq
end

local function new_run(scene)
  seq = 0
  stopped = false
  run = {
    meta = {
      addon = ADDON_NAME,
      scene = scene or "manual_snapshot",
      started_monotonic = monotonic(),
      sv_memory_assigned = false,
      logout_seen = false,
      stop_reason = nil,
      build = nil,
    },
    event_counts = event_counts,
    records = {},
  }
  if GetBuildInfo then
    local ok, ver, num, date, iface = pcall(GetBuildInfo)
    if ok then
      run.meta.build = {
        version = persistable(ver),
        number = persistable(num),
        date = persistable(date),
        interface = persistable(iface),
      }
    end
  end
  table.insert(WowProbeWotLK_Report.runs, run)
  run.meta.sv_memory_assigned = true
  snapshot()
end

local WATCHED_EVENTS = {
  "ADDON_ACTION_BLOCKED",
  "ADDON_ACTION_FORBIDDEN",
  "MACRO_ACTION_BLOCKED",
  "MACRO_ACTION_FORBIDDEN",
  "PLAYER_REGEN_DISABLED",
  "PLAYER_REGEN_ENABLED",
  "PLAYER_TARGET_CHANGED",
  "PLAYER_ENTERING_WORLD",
  "ZONE_CHANGED_NEW_AREA",
  "SPELLS_CHANGED",
}

local frame = CreateFrame("Frame")
local ei
for ei = 1, #WATCHED_EVENTS do
  frame:RegisterEvent(WATCHED_EVENTS[ei])
end
frame:RegisterEvent("ADDON_LOADED")
frame:RegisterEvent("PLAYER_LOGOUT")

frame:SetScript("OnEvent", function(_, event, arg1)
  event_counts[event] = (event_counts[event] or 0) + 1
  if event == "ADDON_LOADED" then
    if arg1 == ADDON_NAME then
      -- Presence of prior runs after reload is the SV persistence observation.
      if type(WowProbeWotLK_Report) ~= "table" then
        WowProbeWotLK_Report = { schema = "wowprobe-wotlk-v1", runs = {} }
      end
      WowProbeWotLK_Report.schema = WowProbeWotLK_Report.schema or "wowprobe-wotlk-v1"
      WowProbeWotLK_Report.runs = WowProbeWotLK_Report.runs or {}
      WowProbeWotLK_Report.load_count = (WowProbeWotLK_Report.load_count or 0) + 1
      if WowProbeWotLK_Report.auto_once_on_load or WowProbeWotLK_AutoOnce then
        new_run("auto_enter_world")
      end
      DEFAULT_CHAT_FRAME:AddMessage("WowProbeWotLK loaded. /wp once [scene]")
    end
    return
  end
  if event == "PLAYER_LOGOUT" then
    if run then
      run.meta.logout_seen = true
    end
    return
  end
  if not run or stopped then
    return
  end
  local note
  -- Record blocked/forbidden add-on names only. Do not store GUIDs.
  if event == "ADDON_ACTION_BLOCKED" or event == "ADDON_ACTION_FORBIDDEN"
      or event == "MACRO_ACTION_BLOCKED" or event == "MACRO_ACTION_FORBIDDEN" then
    note = persistable(arg1)
  end
  add_record({
    probe_id = "EVT." .. event,
    api = event,
    args_shape = {},
    call_status = "RETURNED",
    value_status = "OK",
    value_type = "event",
    event_status = event,
    note = note,
  })
end)

SLASH_WOWPROBE1 = "/wowprobe"
SLASH_WOWPROBE2 = "/wp"
SlashCmdList["WOWPROBE"] = function(msg)
  msg = string.lower(string.gsub(msg or "", "^%s+", ""))
  if msg == "stop" then
    stopped = true
    if run then
      run.meta.stop_reason = "operator"
    end
    return
  end
  if msg == "status" then
    local nruns = WowProbeWotLK_Report and WowProbeWotLK_Report.runs and #WowProbeWotLK_Report.runs or 0
    DEFAULT_CHAT_FRAME:AddMessage(string.format("WowProbeWotLK runs=%d seq=%d stopped=%s", nruns, seq, tostring(stopped)))
    return
  end
  local scene = string.match(msg, "^once%s+(.+)$")
  if msg == "once" or scene then
    new_run(scene or "manual_snapshot")
    DEFAULT_CHAT_FRAME:AddMessage(string.format("WowProbeWotLK snapshot seq=%d", seq))
    return
  end
  DEFAULT_CHAT_FRAME:AddMessage("WowProbeWotLK: /wowprobe once [scene] | status | stop")
end
