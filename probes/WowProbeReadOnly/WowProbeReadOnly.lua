-- WowProbeReadOnly
-- Read-only capability recorder. Not a bot, not a rotation helper, not loaded on the
-- research machine. Does not cast, move, target, attack, interact, or send chat.
--
-- Slash:
--   /wowprobe once [scene]   one snapshot
--   /wowprobe status         record counts
--   /wowprobe stop           halt this session

local ADDON_NAME = "WowProbeReadOnly"
local MAX_RECORDS = 4000

WowProbe_Report = WowProbe_Report or { schema = "wowprobe-readonly-v1", runs = {} }

local run
local seq = 0
local stopped = false
local event_counts = {}

local UNIT_TOKENS = { "player", "target" }
local RESTRICTION_NAMES = {
  "Combat",
  "Encounter",
  "ChallengeMode",
  "PvPMatch",
  "Map",
  "Chat",
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

local function secret_of(value)
  if issecretvalue then
    local ok, s = pcall(issecretvalue, value)
    if ok then
      return s == true
    end
    return nil
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
  fields.probe_id = fields.probe_id
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
  local sec = secret_of(value)
  if sec == true then
    add_record({
      probe_id = probe_id,
      api = api,
      args_shape = args_shape,
      call_status = "RETURNED",
      value_status = "SECRET",
      value_type = type(value),
      note = extra_note,
    })
    return
  end
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
  if type(value) == "table" then
    if type(value.GetXY) == "function" then
      local ok, x, y = pcall(value.GetXY, value)
      if not ok then
        add_record({
          probe_id = probe_id,
          api = api,
          args_shape = args_shape,
          call_status = "ERROR",
          value_status = "NOT_APPLICABLE",
          error_text = tostring(x),
          note = extra_note,
        })
        return
      end
      if secret_of(x) == true or secret_of(y) == true then
        add_record({
          probe_id = probe_id,
          api = api,
          args_shape = args_shape,
          call_status = "RETURNED",
          value_status = "SECRET",
          value_type = "number",
          note = "vector_xy",
        })
        return
      end
      add_record({
        probe_id = probe_id,
        api = api,
        args_shape = args_shape,
        call_status = "RETURNED",
        value_status = "OK",
        value_type = "vector2",
        value = { x = x, y = y },
        note = extra_note,
      })
      return
    end
    add_record({
      probe_id = probe_id,
      api = api,
      args_shape = args_shape,
      call_status = "RETURNED",
      value_status = "OK",
      value_type = "table",
      note = extra_note or "table_not_expanded",
    })
    return
  end
  add_record({
    probe_id = probe_id,
    api = api,
    args_shape = args_shape,
    call_status = "RETURNED",
    value_status = "OK",
    value_type = type(value),
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

local function snapshot_g1()
  call_one("G1.build", "GetBuildInfo", GetBuildInfo, {})
  call_one("G1.beta", "IsBetaBuild", IsBetaBuild, {})
  call_one("G1.x64", "Is64BitClient", Is64BitClient, {})
  call_one("G1.security", "C_AddOns.GetAddOnSecurity", ns_get(C_AddOns, "GetAddOnSecurity"), { "string" }, ADDON_NAME)
  call_one("G1.scripts_beta", "C_AddOns.GetScriptsDisallowedForBeta", ns_get(C_AddOns, "GetScriptsDisallowedForBeta"), {})
  call_one("G1.lockdown", "InCombatLockdown", InCombatLockdown, {})
  local enum = Enum and Enum.AddOnRestrictionType
  local getter = ns_get(C_RestrictedActions, "GetAddOnRestrictionState")
  local active = ns_get(C_RestrictedActions, "IsAddOnRestrictionActive")
  local i
  for i = 1, #RESTRICTION_NAMES do
    local name = RESTRICTION_NAMES[i]
    local value = enum and enum[name]
    if value == nil then
      add_record({
        probe_id = "G1.restriction." .. name,
        api = "Enum.AddOnRestrictionType." .. name,
        args_shape = {},
        call_status = "ERROR",
        value_status = "NOT_APPLICABLE",
        error_text = "missing_enum",
      })
    else
      call_one("G1.restriction." .. name, "C_RestrictedActions.GetAddOnRestrictionState", getter, { "enum" }, value)
      call_one("G1.restriction_active." .. name, "C_RestrictedActions.IsAddOnRestrictionActive", active, { "enum" }, value)
    end
  end
end

local function snapshot_g2()
  call_one("G2.time", "GetTime", GetTime, {})
  call_one("G2.server", "GetServerTime", GetServerTime, {})
  call_one("G2.session", "GetSessionTime", GetSessionTime, {})
  call_one("G2.tick", "GetTickTime", GetTickTime, {})
end

local function snapshot_g3()
  local map_fn = ns_get(C_Map, "GetBestMapForUnit")
  local pos_fn = ns_get(C_Map, "GetPlayerMapPosition")
  if type(map_fn) ~= "function" then
    record_missing("G3.map", "C_Map.GetBestMapForUnit", { "player" })
    return
  end
  local ok, mapID = pcall(map_fn, "player")
  if not ok then
    add_record({
      probe_id = "G3.map",
      api = "C_Map.GetBestMapForUnit",
      args_shape = { "player" },
      call_status = "ERROR",
      value_status = "NOT_APPLICABLE",
      error_text = tostring(mapID),
    })
    return
  end
  classify_and_store("G3.map", "C_Map.GetBestMapForUnit", { "player" }, mapID)
  if mapID == nil or secret_of(mapID) == true then
    add_record({
      probe_id = "G3.position",
      api = "C_Map.GetPlayerMapPosition",
      args_shape = { "mapID", "player" },
      call_status = "RETURNED",
      value_status = "NOT_APPLICABLE",
      note = "skipped_no_public_mapID",
    })
    return
  end
  call_one("G3.position", "C_Map.GetPlayerMapPosition", pos_fn, { "number", "player" }, mapID, "player")
end

local function snapshot_g4()
  local i
  for i = 1, #UNIT_TOKENS do
    local unit = UNIT_TOKENS[i]
    local shape = { unit }
    call_one("G4.exists." .. unit, "UnitExists", UnitExists, shape, unit)
    call_one("G4.dead." .. unit, "UnitIsDeadOrGhost", UnitIsDeadOrGhost, shape, unit)
    call_one("G4.combat." .. unit, "UnitAffectingCombat", UnitAffectingCombat, shape, unit)
    call_one("G4.distance." .. unit, "UnitDistanceSquared", UnitDistanceSquared, shape, unit)
    if unit ~= "player" then
      call_one("G4.enemy." .. unit, "UnitIsEnemy", UnitIsEnemy, { "player", unit }, "player", unit)
    end
    -- Health/power are classified only. Secret numbers are not stored.
    call_one("G4.health." .. unit, "UnitHealth", UnitHealth, shape, unit)
    call_one("G4.healthmax." .. unit, "UnitHealthMax", UnitHealthMax, shape, unit)
    call_one("G4.power." .. unit, "UnitPower", UnitPower, shape, unit)
    call_one("G4.powermax." .. unit, "UnitPowerMax", UnitPowerMax, shape, unit)
    call_one("G4.cast." .. unit, "UnitCastingInfo", UnitCastingInfo, shape, unit)
    local secrets = C_Secrets
    call_one("G4.pred.healthmax." .. unit, "C_Secrets.ShouldUnitHealthMaxBeSecret", ns_get(secrets, "ShouldUnitHealthMaxBeSecret"), shape, unit)
    call_one("G4.pred.power." .. unit, "C_Secrets.ShouldUnitPowerBeSecret", ns_get(secrets, "ShouldUnitPowerBeSecret"), shape, unit)
    call_one("G4.pred.powermax." .. unit, "C_Secrets.ShouldUnitPowerMaxBeSecret", ns_get(secrets, "ShouldUnitPowerMaxBeSecret"), shape, unit)
    call_one("G4.pred.cast." .. unit, "C_Secrets.ShouldUnitSpellCastingBeSecret", ns_get(secrets, "ShouldUnitSpellCastingBeSecret"), shape, unit)
  end
  call_one("G4.loose", "IsTargetLoose", IsTargetLoose, {})
end

local function snapshot_g7()
  local ac = C_AssistedCombat
  call_one("G7.available", "C_AssistedCombat.IsAvailable", ns_get(ac, "IsAvailable"), {})
  call_one("G7.next", "C_AssistedCombat.GetNextCastSpell", ns_get(ac, "GetNextCastSpell"), {})
  call_one("G7.action", "C_AssistedCombat.GetActionSpell", ns_get(ac, "GetActionSpell"), {})
  local rot = ns_get(ac, "GetRotationSpells")
  if type(rot) ~= "function" then
    record_missing("G7.rotation", "C_AssistedCombat.GetRotationSpells", {})
    return
  end
  local ok, spells = pcall(rot)
  if not ok then
    add_record({
      probe_id = "G7.rotation",
      api = "C_AssistedCombat.GetRotationSpells",
      args_shape = {},
      call_status = "ERROR",
      value_status = "NOT_APPLICABLE",
      error_text = tostring(spells),
    })
    return
  end
  if secret_of(spells) == true then
    classify_and_store("G7.rotation", "C_AssistedCombat.GetRotationSpells", {}, spells)
    return
  end
  if type(spells) ~= "table" then
    classify_and_store("G7.rotation", "C_AssistedCombat.GetRotationSpells", {}, spells)
    return
  end
  if issecrettable then
    local tok, st = pcall(issecrettable, spells)
    if tok and st == true then
      add_record({
        probe_id = "G7.rotation",
        api = "C_AssistedCombat.GetRotationSpells",
        args_shape = {},
        call_status = "RETURNED",
        value_status = "SECRET",
        value_type = "table",
        note = "secret_table_not_iterated",
      })
      return
    end
  end
  local ids = {}
  local n = 0
  local hidden = 0
  local k, v
  for k, v in pairs(spells) do
    n = n + 1
    if n > 32 then
      break
    end
    if secret_of(v) == true then
      hidden = hidden + 1
    elseif type(v) == "number" then
      ids[#ids + 1] = v
    end
  end
  add_record({
    probe_id = "G7.rotation",
    api = "C_AssistedCombat.GetRotationSpells",
    args_shape = {},
    call_status = "RETURNED",
    value_status = "OK",
    value_type = "table",
    value = { count = n, secret_members = hidden, spellIDs = ids },
  })
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
  run.meta.issecretvalue = (issecretvalue ~= nil)
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
      issecretvalue = (issecretvalue ~= nil),
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
  table.insert(WowProbe_Report.runs, run)
  run.meta.sv_memory_assigned = true
  snapshot()
end

local WATCHED_EVENTS = {
  "ADDON_ACTION_BLOCKED",
  "ADDON_ACTION_FORBIDDEN",
  "ADDON_RESTRICTION_STATE_CHANGED",
  "MACRO_ACTION_BLOCKED",
  "MACRO_ACTION_FORBIDDEN",
  "PLAYER_SOFT_ENEMY_CHANGED",
  "PLAYER_SOFT_FRIEND_CHANGED",
  "PLAYER_SOFT_INTERACT_CHANGED",
  "PLAYER_REGEN_DISABLED",
  "PLAYER_REGEN_ENABLED",
  "PLAYER_TARGET_CHANGED",
  "ASSISTED_COMBAT_ACTION_SPELL_CAST",
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
      if type(WowProbe_Report) ~= "table" then
        WowProbe_Report = { schema = "wowprobe-readonly-v1", runs = {} }
      end
      WowProbe_Report.schema = WowProbe_Report.schema or "wowprobe-readonly-v1"
      WowProbe_Report.runs = WowProbe_Report.runs or {}
      WowProbe_Report.load_count = (WowProbe_Report.load_count or 0) + 1
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
  -- Record blocked/forbidden function names only. Do not store unit names or GUIDs.
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
    local nruns = WowProbe_Report and WowProbe_Report.runs and #WowProbe_Report.runs or 0
    DEFAULT_CHAT_FRAME:AddMessage(string.format("WowProbeReadOnly runs=%d seq=%d stopped=%s", nruns, seq, tostring(stopped)))
    return
  end
  local scene = string.match(msg, "^once%s+(.+)$")
  if msg == "once" or scene then
    new_run(scene or "manual_snapshot")
    DEFAULT_CHAT_FRAME:AddMessage(string.format("WowProbeReadOnly snapshot seq=%d", seq))
    return
  end
  DEFAULT_CHAT_FRAME:AddMessage("WowProbeReadOnly: /wowprobe once [scene] | status | stop")
end
