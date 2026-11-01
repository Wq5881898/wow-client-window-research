-- Read-only live telemetry. No targeting, casting, movement or interaction.
local frame = CreateFrame("Frame", "WowProbeLiveFrame", UIParent)
frame:SetPoint("TOPLEFT", UIParent, "TOPLEFT", 20, -110)
frame:SetWidth(600)
frame:SetHeight(65)
local text = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
text:SetPoint("TOPLEFT", 0, -18)
text:SetJustifyH("LEFT")

local CELL = 8
local PROTOCOL = 3
local QUEUE = 4
local DATA_BYTES = 103
local CELLS = 3 + DATA_BYTES + 1
local cells = {}
for i = 1, CELLS do
  local cell = frame:CreateTexture(nil, "OVERLAY")
  cell:SetWidth(CELL)
  cell:SetHeight(CELL)
  cell:SetPoint("TOPLEFT", (i - 1) * CELL, 0)
  cells[i] = cell
end

local sequence, elapsed = 0, 0
local events = {serial = 0, started = 0, succeeded = 0, failed = 0, errors = 0}
local last = {kind = 0, spell = 0, at = 0, reason = 0}
local queue = {}
for i = 1, QUEUE do queue[i] = {serial = 0, kind = 0, spell = 0, at = 0, reason = 0} end

local kinds = {
  UNIT_SPELLCAST_START = 1, UNIT_SPELLCAST_SUCCEEDED = 2,
  UNIT_SPELLCAST_FAILED = 3, UNIT_SPELLCAST_INTERRUPTED = 4, UI_ERROR_MESSAGE = 5,
}
for event in pairs(kinds) do frame:RegisterEvent(event) end

local function spell_id(name)
  if not name then return 0 end
  if name == GetSpellInfo(133) then return 133 end
  if name == GetSpellInfo(168) then return 168 end
  return 0
end

-- Map localized UI error text to a stable code; unknown text keeps 0.
local function reason_code(message)
  if type(message) ~= "string" then return 0 end
  local lowered = string.lower(message)
  if string.find(lowered, "range", 1, true) then return 1 end
  if string.find(lowered, "mana", 1, true) then return 2 end
  if string.find(lowered, "not ready", 1, true) or string.find(lowered, "cooldown", 1, true) then return 3 end
  if string.find(lowered, "invalid target", 1, true) or string.find(lowered, "dead", 1, true) then return 4 end
  if string.find(lowered, "facing", 1, true) then return 5 end
  if string.find(lowered, "line of sight", 1, true) then return 6 end
  return 0
end

local function push(kind, id, reason)
  events.serial = (events.serial + 1) % 65536
  local slot = queue[(events.serial % QUEUE) + 1]
  slot.serial, slot.kind, slot.spell = events.serial, kind, id
  slot.at = math.floor(GetTime() * 1000) % 4294967296
  slot.reason = reason or 0
  last.kind, last.spell, last.at, last.reason = kind, id, slot.at, reason or 0
end

frame:SetScript("OnEvent", function(_, event, ...)
  if event == "UI_ERROR_MESSAGE" then
    local message = ...
    events.errors = (events.errors + 1) % 65536
    push(5, 0, reason_code(message))
    return
  end
  local unit, name = ...
  if unit ~= "player" then return end
  local id = spell_id(name)
  if event == "UNIT_SPELLCAST_START" then
    events.started = (events.started + 1) % 65536
    push(1, id, 0)
  elseif event == "UNIT_SPELLCAST_SUCCEEDED" then
    events.succeeded = (events.succeeded + 1) % 65536
    push(2, id, 0)
  elseif event == "UNIT_SPELLCAST_FAILED" or event == "UNIT_SPELLCAST_INTERRUPTED" then
    events.failed = (events.failed + 1) % 65536
    push(event == "UNIT_SPELLCAST_FAILED" and 3 or 4, id, 0)
  end
end)

local function update()
  sequence = (sequence + 1) % 65536
  local guid = UnitGUID("target") or "0x0000000000000000"
  local spell = GetSpellInfo(133)
  local range = spell and IsSpellInRange(spell, "target")
  local casting = UnitCastingInfo("player")
  local learned = 0
  local i = 1
  while true do
    local name = GetSpellName(i, BOOKTYPE_SPELL)
    if not name then break end
    if name == spell then learned = 1 end
    i = i + 1
  end
  local bytes = {}
  local function number(value, count)
    value = math.floor(value or 0)
    for _ = 1, count do
      bytes[#bytes + 1] = value % 256
      value = math.floor(value / 256)
    end
  end
  number(PROTOCOL, 1)
  number(103, 1)
  number(sequence, 2)
  number(math.floor(GetTime() * 1000) % 4294967296, 4)
  number(UnitHealth("player"), 2)
  number(UnitHealthMax("player"), 2)
  number(UnitPower("player"), 2)
  number(UnitAffectingCombat("player") and 1 or 0, 1)
  number(UnitIsDeadOrGhost("player") and 1 or 0, 1)
  number(UnitHealth("target"), 2)
  number(UnitHealthMax("target"), 2)
  number(range == 1 and 1 or (range == 0 and 0 or 2), 1)
  number(learned, 1)
  number(casting and 1 or 0, 1)
  number(math.floor(GetUnitSpeed("player") * 100), 2)
  for j = 3, 18, 2 do number(tonumber(string.sub(guid, j, j + 1), 16) or 0, 1) end
  number(UnitExists("target") and 1 or 0, 1)
  number(UnitCanAttack("player", "target") and 1 or 0, 1)
  number(UnitIsDeadOrGhost("target") and 1 or 0, 1)
  local x, y = GetPlayerMapPosition("player")
  number(math.floor((x or 0) * 65535), 2)
  number(math.floor((y or 0) * 65535), 2)
  -- GetUnitFacing does not exist in 3.3.5a; report 0 instead of raising.
  local facing = 0
  if GetUnitFacing then facing = GetUnitFacing("player") or 0 end
  number(math.floor(facing * 10430), 2)
  number(events.serial, 2)
  number(events.started, 2)
  number(events.succeeded, 2)
  number(events.failed, 2)
  number(events.errors, 2)
  number(last.kind, 1)
  number(last.spell, 2)
  number(last.at, 4)
  number(last.reason, 1)
  number(UnitBuff("player", GetSpellInfo(168)) and 1 or 0, 1)
  for index = 1, QUEUE do
    local slot = queue[index]
    number(slot.serial, 2)
    number(slot.kind, 1)
    number(slot.spell, 2)
    number(slot.at, 4)
    number(slot.reason, 1)
  end
  local checksum = 0
  local weighted = 0
  for j = 1, #bytes do
    checksum = (checksum + bytes[j]) % 256
    weighted = (weighted + j * bytes[j]) % 65521
  end
  number(checksum, 1)
  number(weighted % 256, 1)

  cells[1]:SetTexture(1, 0, 0, 1)
  cells[2]:SetTexture(0, 1, 0, 1)
  cells[3]:SetTexture(0, 0, 1, 1)
  for j = 1, #bytes do
    local v = bytes[j] / 255
    cells[j + 3]:SetTexture(v, v, v, 1)
  end
  -- Trailing marker lets the decoder measure the cell pitch from the strip itself.
  cells[#cells]:SetTexture(1, 0, 1, 1)
  text:SetText(string.format("LIVE v%d #%d t=%.1f HP %d/%d MP %d combat=%s dead=%s speed=%s\n"
    .. "Target %s HP %d range=%s learned=%d cast=%s pos=%.4f,%.4f facing=%.2f\n"
    .. "Events seq=%d start=%d ok=%d fail=%d err=%d last=%d/%d reason=%d",
    PROTOCOL, sequence, GetTime(), UnitHealth("player"), UnitHealthMax("player"),
    UnitPower("player"), tostring(UnitAffectingCombat("player")),
    tostring(UnitIsDeadOrGhost("player")), tostring(GetUnitSpeed("player")),
    guid, UnitHealth("target"), tostring(range), learned, tostring(casting),
    x or 0, y or 0, facing, events.serial, events.started,
    events.succeeded, events.failed, events.errors, last.kind, last.spell, last.reason))
end

frame:SetScript("OnUpdate", function(_, delta)
  elapsed = elapsed + delta
  if elapsed >= 0.1 then elapsed = 0; update() end
end)
