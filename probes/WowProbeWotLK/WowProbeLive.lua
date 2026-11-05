-- Read-only live telemetry. No targeting, casting, movement or interaction.
-- The panel sits at the bottom right: the top left corner is used by the
-- target frame, by unit nameplates and by the resurrection NPC menu.
local frame = CreateFrame("Frame", "WowProbeLiveFrame", UIParent)
frame:SetPoint("BOTTOMLEFT", UIParent, "BOTTOMLEFT", 20, 260)
frame:SetWidth(600)
frame:SetHeight(65)
local text = frame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
text:SetPoint("TOPLEFT", 0, -18)
text:SetJustifyH("LEFT")

local CELL = 8
local PROTOCOL = 13
local QUEUE = 4
local DATA_BYTES = 140
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
-- The reason of the newest UI error. It survives the spell events that
-- would otherwise overwrite last.reason with zero.
local last = {kind = 0, spell = 0, at = 0, reason = 0, error_reason = 0}
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
  if name == GetSpellInfo(123) then return 123 end
  if name == GetSpellInfo(116) then return 116 end
  if name == GetSpellInfo(213) then return 213 end
  if name == GetSpellInfo(122) then return 122 end
  return 0
end

-- Map localized UI error text to a stable code; unknown text keeps 0.
-- The order matters: the first match wins, so the more specific texts are
-- tested before the generic ones.
local function reason_code(message)
  if type(message) ~= "string" then return 0 end
  local lowered = string.lower(message)
  -- Observed in 3.3.5a: "Target needs to be in front of you." and
  -- "You have no target."
  if string.find(lowered, "in front of you", 1, true)
     or string.find(lowered, "facing", 1, true) then return 5 end
  if string.find(lowered, "no target", 1, true)
     or string.find(lowered, "invalid target", 1, true)
     or string.find(lowered, "dead", 1, true) then return 4 end
  if string.find(lowered, "line of sight", 1, true) then return 6 end
  if string.find(lowered, "range", 1, true) then return 1 end
  if string.find(lowered, "mana", 1, true) then return 2 end
  if string.find(lowered, "not ready", 1, true) or string.find(lowered, "cooldown", 1, true) then return 3 end
  return 0
end

-- The chat edit box being open proves the typed text reached the client.
-- Only the edit box that has the focus counts: the frame of the chat
-- input stays "shown" after it was closed, and a wrong answer here would
-- keep the driver from sending any key.
local function chat_open()
  if ChatEdit_GetActiveWindow and ChatEdit_GetActiveWindow() then return 1 end
  return 0
end

-- Distance to the current target in yards; 0 when unknown.
local function target_distance()
  if not UnitExists("target") then return 0 end
  if not UnitDistance then return 65535 end
  local ok, value = pcall(UnitDistance, "player", "target")
  if not ok or not value then return 65535 end
  return value
end

-- The threat situation of the player: 0 none, 1 low, 2 high, 3 solo.
-- The client does not offer the exact threat, but the situation is enough
-- to tell whether a creature still has the character on its list.
-- 255 means that the threat could not be read at all: the function is
-- missing, the call failed or the client answered with nothing. That is
-- not the same as a threat of zero, and the driver has to tell them apart.
local THREAT_UNKNOWN = 255

local function threat_situation()
  if not UnitThreatSituation then return THREAT_UNKNOWN end
  local ok, value = pcall(UnitThreatSituation, "player")
  if not ok or value == nil then return THREAT_UNKNOWN end
  if value < 0 or value > 3 then return THREAT_UNKNOWN end
  return value
end

-- The number of items in the bags. The containers are only counted every
-- second, because eighty calls in a tenth of a second is too much work for
-- every update.
local bag_count = 0
local bag_tick = 0

local function count_bag_items()
  local count = 0
  for bag = 0, 4 do
    local slots = GetContainerNumSlots and GetContainerNumSlots(bag) or 0
    for slot = 1, slots do
      if GetContainerItemInfo and GetContainerItemInfo(bag, slot) then
        count = count + 1
      end
    end
  end
  return count
end

-- The hash of a name. The byte strip of the panel carries numbers only,
-- so the name of the target travels as a hash of it. The same hash is
-- computed in Python to compare the name the driver wants with the name
-- the client shows.
local function name_hash(text)
  local hash = 5381
  for i = 1, #text do
    hash = (hash * 33 + string.byte(text, i)) % 65536
  end
  return hash
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
    local reason = reason_code(message)
    events.errors = (events.errors + 1) % 65536
    -- The error reason is kept separately: the spell events that follow would
    -- otherwise clear it before the driver can read it.
    last.error_reason = reason
    push(5, 0, reason)
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

-- Spells the driver cares about. The bits of this list build the
-- spell_bits field, so the driver can see which spells the character has
-- without asking the client with a cast.
local KNOWN_SPELLS = {
  [123] = 0,   -- Frostbolt
  [116] = 1,   -- Frost Nova
  [120] = 2,   -- Frost Ward
  [122] = 3,   -- Frost Shock
  [133] = 4,   -- Fireball
  [168] = 5,   -- Frost Armor
  [213] = 6,   -- Fireball, second rank
  [212] = 7,   -- Fireball, higher rank
}

local function update()
  sequence = (sequence + 1) % 65536
  local guid = UnitGUID("target") or "0x0000000000000000"
  local spell = GetSpellInfo(133)
  local range = spell and IsSpellInRange(spell, "target")
  local casting = UnitCastingInfo("player")
  local learned = 0
  local spell_bits = 0
  -- The classification of the target tells the driver whether it is an
  -- ordinary creature, which one spell of the character can finish.
  -- The client of 3.3.5a answers with a word, not with a number.
  local CLASS_CODES = {
    normal = 1, elite = 2, rareelite = 3, worldboss = 4,
    rare = 5, trivial = 6, quest = 7,
  }
  local classification = 0
  if UnitExists("target") and UnitClassification then
    local ok, value = pcall(UnitClassification, "target")
    if ok and value then classification = CLASS_CODES[value] or 0 end
  end
  -- The spot where the corpse lies. It is empty while the character lives
  -- or after the corpse was recovered.
  local corpse_x, corpse_y, corpse_exists = 0, 0, 0
  if GetCorpseMapPosition then
    local ok, cx, cy = pcall(GetCorpseMapPosition)
    if ok and cx and cy then
      corpse_x, corpse_y = cx, cy
      if cx ~= 0 or cy ~= 0 then corpse_exists = 1 end
    end
  end
  local i = 1
  while true do
    local name = GetSpellName(i, BOOKTYPE_SPELL)
    if not name then break end
    if name == spell then learned = 1 end
    for id, bit in pairs(KNOWN_SPELLS) do
      if name == GetSpellInfo(id) then
        spell_bits = spell_bits + 2 ^ bit
      end
    end
    i = i + 1
  end
  local bytes = {}
  local function number(value, count)
    -- A string would break the whole panel, so nothing but a number is
    -- written into the payload.
    value = tonumber(value) or 0
    value = math.floor(value)
    for _ = 1, count do
      bytes[#bytes + 1] = value % 256
      value = math.floor(value / 256)
    end
  end
  number(PROTOCOL, 1)
  number(DATA_BYTES, 1)
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
  -- GetUnitFacing does not exist in 3.3.5a, but GetPlayerFacing does, and
  -- the driver needs the heading to walk towards the corpse after a death.
  local facing = 0
  if GetPlayerFacing then
    local ok, value = pcall(GetPlayerFacing)
    if ok and value then facing = value end
  end
  number(math.floor(facing * 10430), 2)
  number(math.floor(corpse_x * 65535), 2)
  number(math.floor(corpse_y * 65535), 2)
  number(corpse_exists, 1)
  number(events.serial, 2)
  number(events.started, 2)
  number(events.succeeded, 2)
  number(events.failed, 2)
  number(events.errors, 2)
  number(last.kind, 1)
  number(last.spell, 2)
  number(last.at, 4)
  number(last.reason, 1)
  number(last.error_reason, 1)
  number(math.floor(spell_bits), 2)
  number(classification, 1)
  number(UnitBuff("player", GetSpellInfo(168)) and 1 or 0, 1)
  number(chat_open(), 1)
  number(math.floor(target_distance() * 10), 2)
  for index = 1, QUEUE do
    local slot = queue[index]
    number(slot.serial, 2)
    number(slot.kind, 1)
    number(slot.spell, 2)
    number(slot.at, 4)
    number(slot.reason, 1)
  end
  -- The GUID of the player, so a record of a run names the character that
  -- made it, and the name of the target as a hash. Both are written before
  -- the checksum, so the checksum covers them.
  -- The GUID of the player, the same way the GUID of the target is read.
  local player_guid = UnitGUID("player") or "0x0000000000000000"
  for j = 3, 18, 2 do number(tonumber(string.sub(player_guid, j, j + 1), 16) or 0, 1) end
  number(name_hash(UnitName("target") or ""), 2)
  number(threat_situation(), 1)
  -- The level of the character and its experience, so a run that is about
  -- the level can be checked without reading the text of the panel.
  number(UnitLevel("player") or 0, 1)
  number(math.floor(UnitXP("player") or 0), 3)
  number(math.floor(UnitXPMax("player") or 0), 3)
  -- The money of the character, so a trade with a merchant can be checked.
  number(math.floor(GetMoney and GetMoney() or 0), 4)
  -- The number of items in the bags and the name of the creature under the
  -- cursor, which is how a merchant is found.
  bag_tick = bag_tick + 1
  if bag_tick >= 10 then
    bag_tick = 0
    bag_count = count_bag_items()
  end
  number(bag_count, 1)
  number(name_hash(UnitName("mouseover") or ""), 2)
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
    .. "Corpse exists=%s at=%.5f,%.5f\n"
    .. "Events seq=%d start=%d ok=%d fail=%d err=%d last=%d/%d reason=%d er=%d chat=%d dist=%.1f"
    .. " player=%s threat=%d level=%d xp=%d/%d money=%d bags=%d cursor=%s",
    PROTOCOL, sequence, GetTime(), UnitHealth("player"), UnitHealthMax("player"),
    UnitPower("player"), tostring(UnitAffectingCombat("player")),
    tostring(UnitIsDeadOrGhost("player")), tostring(GetUnitSpeed("player")),
    guid, UnitHealth("target"), tostring(range), learned, tostring(casting),
    x or 0, y or 0, facing,
    tostring(corpse_exists == 1), corpse_x, corpse_y,
    events.serial, events.started,
    events.succeeded, events.failed, events.errors, last.kind, last.spell, last.reason,
    last.error_reason, chat_open(), target_distance(), UnitGUID("player") or "",
    threat_situation(), UnitLevel("player") or 0, UnitXP("player") or 0,
    UnitXPMax("player") or 0, GetMoney and GetMoney() or 0, bag_count,
    UnitName("mouseover") or ""))
end

frame:SetScript("OnUpdate", function(_, delta)
  elapsed = elapsed + delta
  if elapsed >= 0.1 then elapsed = 0; update() end
end)
