"""Single source of truth for the pixel telemetry layout.

The Lua encoder writes fields in a fixed order; the Python decoder reads them
at fixed offsets. `parse_lua_layout` extracts the encoder order from the
probe source so a mismatch fails the test suite instead of silently decoding
garbage.

Protocol v3 and v4 keep separate layouts: v4 adds fields in the middle of
the packet, so sharing one offset table would break v3 screenshots.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / 'probes' / 'WowProbeWotLK' / 'WowProbeLive.lua'

# Protocol v3: 103 bytes total. Frozen so historical screenshots stay readable.
V3_LAYOUT = [
    ('protocol', 1), ('length', 1), ('sequence', 2), ('game_ms', 4),
    ('health', 2), ('max_health', 2), ('power', 2), ('combat', 1), ('dead', 1),
    ('target_health', 2), ('target_max_health', 2), ('spell_range', 1),
    ('spell_learned', 1), ('casting', 1), ('speed', 2), ('target_guid', 8),
    ('target_exists', 1), ('target_attackable', 1), ('target_dead', 1),
    ('pos_x', 2), ('pos_y', 2), ('facing', 2), ('event_serial', 2),
    ('cast_started', 2), ('cast_succeeded', 2), ('cast_failed', 2),
    ('ui_errors', 2), ('last_kind', 1), ('last_spell', 2), ('last_at', 4),
    ('last_reason', 1), ('frost_armor', 1), ('event_queue', 40),
    ('checksum', 1), ('weighted', 1),
]

# Protocol v4: adds chat_open and target_distance before the event queue.
V4_LAYOUT = [
    ('protocol', 1), ('length', 1), ('sequence', 2), ('game_ms', 4),
    ('health', 2), ('max_health', 2), ('power', 2), ('combat', 1), ('dead', 1),
    ('target_health', 2), ('target_max_health', 2), ('spell_range', 1),
    ('spell_learned', 1), ('casting', 1), ('speed', 2), ('target_guid', 8),
    ('target_exists', 1), ('target_attackable', 1), ('target_dead', 1),
    ('pos_x', 2), ('pos_y', 2), ('facing', 2), ('event_serial', 2),
    ('cast_started', 2), ('cast_succeeded', 2), ('cast_failed', 2),
    ('ui_errors', 2), ('last_kind', 1), ('last_spell', 2), ('last_at', 4),
    ('last_reason', 1), ('frost_armor', 1), ('chat_open', 1),
    ('target_distance', 2), ('event_queue', 40),
    ('checksum', 1), ('weighted', 1),
]

# Protocol v5: adds last_error_reason, the reason code of the newest UI
# error. The v4 field last_reason is overwritten by every event, so a cast
# failure that is explained by a later UI message loses its cause. The new
# field only changes when a UI error arrives, which makes it usable as the
# feedback signal for a turn-and-retry loop.
V5_LAYOUT = [
    ('protocol', 1), ('length', 1), ('sequence', 2), ('game_ms', 4),
    ('health', 2), ('max_health', 2), ('power', 2), ('combat', 1), ('dead', 1),
    ('target_health', 2), ('target_max_health', 2), ('spell_range', 1),
    ('spell_learned', 1), ('casting', 1), ('speed', 2), ('target_guid', 8),
    ('target_exists', 1), ('target_attackable', 1), ('target_dead', 1),
    ('pos_x', 2), ('pos_y', 2), ('facing', 2), ('event_serial', 2),
    ('cast_started', 2), ('cast_succeeded', 2), ('cast_failed', 2),
    ('ui_errors', 2), ('last_kind', 1), ('last_spell', 2), ('last_at', 4),
    ('last_reason', 1), ('last_error_reason', 1), ('frost_armor', 1),
    ('chat_open', 1), ('target_distance', 2), ('event_queue', 40),
    ('checksum', 1), ('weighted', 1),
]

# Protocol v6: adds spell_bits, a bit per known spell, so the driver can see
# which spells the character has without asking the client with a cast.
V6_LAYOUT = [
    ('protocol', 1), ('length', 1), ('sequence', 2), ('game_ms', 4),
    ('health', 2), ('max_health', 2), ('power', 2), ('combat', 1), ('dead', 1),
    ('target_health', 2), ('target_max_health', 2), ('spell_range', 1),
    ('spell_learned', 1), ('casting', 1), ('speed', 2), ('target_guid', 8),
    ('target_exists', 1), ('target_attackable', 1), ('target_dead', 1),
    ('pos_x', 2), ('pos_y', 2), ('facing', 2), ('event_serial', 2),
    ('cast_started', 2), ('cast_succeeded', 2), ('cast_failed', 2),
    ('ui_errors', 2), ('last_kind', 1), ('last_spell', 2), ('last_at', 4),
    ('last_reason', 1), ('last_error_reason', 1), ('spell_bits', 2),
    ('frost_armor', 1), ('chat_open', 1), ('target_distance', 2),
    ('event_queue', 40), ('checksum', 1), ('weighted', 1),
]


# Protocol v7: adds target_class, the classification of the selected
# creature. One is an ordinary creature, two an elite, three a rare elite
# and four a world boss. An elite creature resists the spells of a low
# character, so the driver has to know the difference.
V7_LAYOUT = [
    ('protocol', 1), ('length', 1), ('sequence', 2), ('game_ms', 4),
    ('health', 2), ('max_health', 2), ('power', 2), ('combat', 1), ('dead', 1),
    ('target_health', 2), ('target_max_health', 2), ('spell_range', 1),
    ('spell_learned', 1), ('casting', 1), ('speed', 2), ('target_guid', 8),
    ('target_exists', 1), ('target_attackable', 1), ('target_dead', 1),
    ('pos_x', 2), ('pos_y', 2), ('facing', 2), ('event_serial', 2),
    ('cast_started', 2), ('cast_succeeded', 2), ('cast_failed', 2),
    ('ui_errors', 2), ('last_kind', 1), ('last_spell', 2), ('last_at', 4),
    ('last_reason', 1), ('last_error_reason', 1), ('spell_bits', 2),
    ('target_class', 1), ('frost_armor', 1), ('chat_open', 1),
    ('target_distance', 2), ('event_queue', 40), ('checksum', 1),
    ('weighted', 1),
]

# Protocol v8: adds the heading of the character and the spot of its corpse.
# The driver needs both to walk to the corpse after a death, because the
# character cannot be turned towards it without a facing readout.
V8_LAYOUT = [
    ('protocol', 1), ('length', 1), ('sequence', 2), ('game_ms', 4),
    ('health', 2), ('max_health', 2), ('power', 2), ('combat', 1), ('dead', 1),
    ('target_health', 2), ('target_max_health', 2), ('spell_range', 1),
    ('spell_learned', 1), ('casting', 1), ('speed', 2), ('target_guid', 8),
    ('target_exists', 1), ('target_attackable', 1), ('target_dead', 1),
    ('pos_x', 2), ('pos_y', 2), ('facing', 2), ('corpse_x', 2),
    ('corpse_y', 2), ('corpse_exists', 1), ('event_serial', 2),
    ('cast_started', 2), ('cast_succeeded', 2), ('cast_failed', 2),
    ('ui_errors', 2), ('last_kind', 1), ('last_spell', 2), ('last_at', 4),
    ('last_reason', 1), ('last_error_reason', 1), ('spell_bits', 2),
    ('target_class', 1), ('frost_armor', 1), ('chat_open', 1),
    ('target_distance', 2), ('event_queue', 40), ('checksum', 1),
    ('weighted', 1),
]

# Protocol v9: adds the GUID of the player and the name of the target.
# The records of a run have to name the character that made them, and the
# driver has to be able to lock a creature by its name; the name travels
# as a hash, because the byte strip of the panel carries numbers only.
V9_LAYOUT = [
    ('protocol', 1), ('length', 1), ('sequence', 2), ('game_ms', 4),
    ('health', 2), ('max_health', 2), ('power', 2), ('combat', 1), ('dead', 1),
    ('target_health', 2), ('target_max_health', 2), ('spell_range', 1),
    ('spell_learned', 1), ('casting', 1), ('speed', 2), ('target_guid', 8),
    ('target_exists', 1), ('target_attackable', 1), ('target_dead', 1),
    ('pos_x', 2), ('pos_y', 2), ('facing', 2), ('corpse_x', 2),
    ('corpse_y', 2), ('corpse_exists', 1), ('event_serial', 2),
    ('cast_started', 2), ('cast_succeeded', 2), ('cast_failed', 2),
    ('ui_errors', 2), ('last_kind', 1), ('last_spell', 2), ('last_at', 4),
    ('last_reason', 1), ('last_error_reason', 1), ('spell_bits', 2),
    ('target_class', 1), ('frost_armor', 1), ('chat_open', 1),
    ('target_distance', 2), ('event_queue', 40), ('player_guid', 8),
    ('target_name_hash', 2), ('checksum', 1), ('weighted', 1),
]

# Protocol v10: adds the threat situation of the player. The client does
# not offer the exact threat, but the situation tells whether a creature
# still has the character on its list, which the driver needs to tell a
# cleared fight from a stopped one.
V10_LAYOUT = [
    ('protocol', 1), ('length', 1), ('sequence', 2), ('game_ms', 4),
    ('health', 2), ('max_health', 2), ('power', 2), ('combat', 1), ('dead', 1),
    ('target_health', 2), ('target_max_health', 2), ('spell_range', 1),
    ('spell_learned', 1), ('casting', 1), ('speed', 2), ('target_guid', 8),
    ('target_exists', 1), ('target_attackable', 1), ('target_dead', 1),
    ('pos_x', 2), ('pos_y', 2), ('facing', 2), ('corpse_x', 2),
    ('corpse_y', 2), ('corpse_exists', 1), ('event_serial', 2),
    ('cast_started', 2), ('cast_succeeded', 2), ('cast_failed', 2),
    ('ui_errors', 2), ('last_kind', 1), ('last_spell', 2), ('last_at', 4),
    ('last_reason', 1), ('last_error_reason', 1), ('spell_bits', 2),
    ('target_class', 1), ('frost_armor', 1), ('chat_open', 1),
    ('target_distance', 2), ('event_queue', 40), ('player_guid', 8),
    ('target_name_hash', 2), ('threat', 1), ('checksum', 1), ('weighted', 1),
]

# Protocol v11: adds the level of the character and its experience. A run
# that is about the level can be checked without reading the text of the
# panel.
V11_LAYOUT = [
    ('protocol', 1), ('length', 1), ('sequence', 2), ('game_ms', 4),
    ('health', 2), ('max_health', 2), ('power', 2), ('combat', 1), ('dead', 1),
    ('target_health', 2), ('target_max_health', 2), ('spell_range', 1),
    ('spell_learned', 1), ('casting', 1), ('speed', 2), ('target_guid', 8),
    ('target_exists', 1), ('target_attackable', 1), ('target_dead', 1),
    ('pos_x', 2), ('pos_y', 2), ('facing', 2), ('corpse_x', 2),
    ('corpse_y', 2), ('corpse_exists', 1), ('event_serial', 2),
    ('cast_started', 2), ('cast_succeeded', 2), ('cast_failed', 2),
    ('ui_errors', 2), ('last_kind', 1), ('last_spell', 2), ('last_at', 4),
    ('last_reason', 1), ('last_error_reason', 1), ('spell_bits', 2),
    ('target_class', 1), ('frost_armor', 1), ('chat_open', 1),
    ('target_distance', 2), ('event_queue', 40), ('player_guid', 8),
    ('target_name_hash', 2), ('threat', 1), ('level', 1), ('xp', 3),
    ('xp_max', 3), ('checksum', 1), ('weighted', 1),
]

# Protocol v12: adds the money of the character, the number of items in the
# bags and the name of the creature under the cursor. With them a trade with
# a merchant can be made and checked: the money has to change, and the
# merchant is found by the name of the creature under the cursor.
V12_LAYOUT = [
    ('protocol', 1), ('length', 1), ('sequence', 2), ('game_ms', 4),
    ('health', 2), ('max_health', 2), ('power', 2), ('combat', 1), ('dead', 1),
    ('target_health', 2), ('target_max_health', 2), ('spell_range', 1),
    ('spell_learned', 1), ('casting', 1), ('speed', 2), ('target_guid', 8),
    ('target_exists', 1), ('target_attackable', 1), ('target_dead', 1),
    ('pos_x', 2), ('pos_y', 2), ('facing', 2), ('corpse_x', 2),
    ('corpse_y', 2), ('corpse_exists', 1), ('event_serial', 2),
    ('cast_started', 2), ('cast_succeeded', 2), ('cast_failed', 2),
    ('ui_errors', 2), ('last_kind', 1), ('last_spell', 2), ('last_at', 4),
    ('last_reason', 1), ('last_error_reason', 1), ('spell_bits', 2),
    ('target_class', 1), ('frost_armor', 1), ('chat_open', 1),
    ('target_distance', 2), ('event_queue', 40), ('player_guid', 8),
    ('target_name_hash', 2), ('threat', 1), ('level', 1), ('xp', 3),
    ('xp_max', 3), ('money', 4), ('bag_items', 1), ('npc_name_hash', 2),
    ('checksum', 1), ('weighted', 1),
]

# Protocol v13: the name of the unit under the cursor. The token "npc" of
# 3.3.5a does not answer on this client, but "mouseover" names the unit
# under the cursor, whoever it is. A merchant is found that way.
V13_LAYOUT = [
    ('protocol', 1), ('length', 1), ('sequence', 2), ('game_ms', 4),
    ('health', 2), ('max_health', 2), ('power', 2), ('combat', 1), ('dead', 1),
    ('target_health', 2), ('target_max_health', 2), ('spell_range', 1),
    ('spell_learned', 1), ('casting', 1), ('speed', 2), ('target_guid', 8),
    ('target_exists', 1), ('target_attackable', 1), ('target_dead', 1),
    ('pos_x', 2), ('pos_y', 2), ('facing', 2), ('corpse_x', 2),
    ('corpse_y', 2), ('corpse_exists', 1), ('event_serial', 2),
    ('cast_started', 2), ('cast_succeeded', 2), ('cast_failed', 2),
    ('ui_errors', 2), ('last_kind', 1), ('last_spell', 2), ('last_at', 4),
    ('last_reason', 1), ('last_error_reason', 1), ('spell_bits', 2),
    ('target_class', 1), ('frost_armor', 1), ('chat_open', 1),
    ('target_distance', 2), ('event_queue', 40), ('player_guid', 8),
    ('target_name_hash', 2), ('threat', 1), ('level', 1), ('xp', 3),
    ('xp_max', 3), ('money', 4), ('bag_items', 1), ('cursor_name_hash', 2),
    ('checksum', 1), ('weighted', 1),
]

# Protocol v14: adds the zone and the subzone of the character and the map
# it is on. The names travel as hashes, because the byte strip of the panel
# carries numbers only. The driver needs them, because the coordinates of
# the probe belong to the area the character is in.
V14_LAYOUT = [
    ('protocol', 1), ('length', 1), ('sequence', 2), ('game_ms', 4),
    ('health', 2), ('max_health', 2), ('power', 2), ('combat', 1), ('dead', 1),
    ('target_health', 2), ('target_max_health', 2), ('spell_range', 1),
    ('spell_learned', 1), ('casting', 1), ('speed', 2), ('target_guid', 8),
    ('target_exists', 1), ('target_attackable', 1), ('target_dead', 1),
    ('pos_x', 2), ('pos_y', 2), ('facing', 2), ('corpse_x', 2),
    ('corpse_y', 2), ('corpse_exists', 1), ('event_serial', 2),
    ('cast_started', 2), ('cast_succeeded', 2), ('cast_failed', 2),
    ('ui_errors', 2), ('last_kind', 1), ('last_spell', 2), ('last_at', 4),
    ('last_reason', 1), ('last_error_reason', 1), ('spell_bits', 2),
    ('target_class', 1), ('frost_armor', 1), ('chat_open', 1),
    ('target_distance', 2), ('event_queue', 40), ('player_guid', 8),
    ('target_name_hash', 2), ('threat', 1), ('level', 1), ('xp', 3),
    ('xp_max', 3), ('money', 4), ('bag_items', 1), ('cursor_name_hash', 2),
    ('zone_hash', 2), ('subzone_hash', 2), ('map_id', 2), ('checksum', 1),
    ('weighted', 1),
]

CURRENT_LAYOUT = V14_LAYOUT

EXPRESSION_NAMES = {
    'PROTOCOL': 'protocol',
    '103': 'length',
    '106': 'length',
    '107': 'length',
    '109': 'length',
    '110': 'length',
    '115': 'length',
    'DATA_BYTES': 'length',
    'sequence': 'sequence',
    'math.floor(GetTime() * 1000) % 4294967296': 'game_ms',
    'UnitHealth("player")': 'health',
    'UnitHealthMax("player")': 'max_health',
    'UnitPower("player")': 'power',
    'UnitAffectingCombat("player") and 1 or 0': 'combat',
    'UnitIsDeadOrGhost("player") and 1 or 0': 'dead',
    'UnitHealth("target")': 'target_health',
    'UnitHealthMax("target")': 'target_max_health',
    'range == 1 and 1 or (range == 0 and 0 or 2)': 'spell_range',
    'learned': 'spell_learned',
    'casting and 1 or 0': 'casting',
    'math.floor(GetUnitSpeed("player") * 100)': 'speed',
    'UnitExists("target") and 1 or 0': 'target_exists',
    'UnitCanAttack("player", "target") and 1 or 0': 'target_attackable',
    'UnitIsDeadOrGhost("target") and 1 or 0': 'target_dead',
    'math.floor((x or 0) * 65535)': 'pos_x',
    'math.floor((y or 0) * 65535)': 'pos_y',
    'math.floor(facing * 10430)': 'facing',
    'math.floor(corpse_x * 65535)': 'corpse_x',
    'math.floor(corpse_y * 65535)': 'corpse_y',
    'corpse_exists': 'corpse_exists',
    'events.serial': 'event_serial',
    'events.started': 'cast_started',
    'events.succeeded': 'cast_succeeded',
    'events.failed': 'cast_failed',
    'events.errors': 'ui_errors',
    'last.kind': 'last_kind',
    'last.spell': 'last_spell',
    'last.at': 'last_at',
    'last.reason': 'last_reason',
    'last.error_reason': 'last_error_reason',
    'math.floor(spell_bits)': 'spell_bits',
    'classification': 'target_class',
    'UnitBuff("player", GetSpellInfo(168)) and 1 or 0': 'frost_armor',
    'chat_open()': 'chat_open',
    'name_hash(UnitName("target") or "")': 'target_name_hash',
    'threat_situation()': 'threat',
    'UnitLevel("player") or 0': 'level',
    'math.floor(UnitXP("player") or 0)': 'xp',
    'math.floor(UnitXPMax("player") or 0)': 'xp_max',
    'math.floor(GetMoney and GetMoney() or 0)': 'money',
    'bag_count': 'bag_items',
    'name_hash(UnitName("mouseover") or "")': 'cursor_name_hash',
    'zone_hash()': 'zone_hash',
    'subzone_hash()': 'subzone_hash',
    'map_id()': 'map_id',
    'math.floor(target_distance() * 10)': 'target_distance',
    'checksum': 'checksum',
    'weighted % 256': 'weighted',
}

GUID_LOOP = re.compile(r'for j = 3, 18, 2 do.*?end', re.S)
QUEUE_LOOP = re.compile(r'for index = 1, QUEUE do.*?end', re.S)
NUMBER_CALL = re.compile(r'number\((.+?),\s*(\d+)\)')


def parse_lua_layout(source=None):
    """Return the (name, size) order actually written by the Lua encoder."""
    text = source if source is not None else PROBE.read_text(encoding='utf-8')
    body = text[text.index('local function update()'):]
    body = body[:body.index('frame:SetScript("OnUpdate"')]
    body = GUID_LOOP.sub('\x00GUID\x00', body)
    body = QUEUE_LOOP.sub('\x00QUEUE\x00', body)
    layout = []
    guid_count = 0
    for chunk in re.split(r'[\x00]', body):
        if chunk == 'GUID':
            # The first GUID is the target, the second one the player.
            guid_count += 1
            layout.append(('target_guid' if guid_count == 1 else 'player_guid', 8))
            continue
        if chunk == 'QUEUE':
            layout.append(('event_queue', 40))
            continue
        for match in NUMBER_CALL.finditer(chunk):
            expression, size = match.group(1).strip(), int(match.group(2))
            name = EXPRESSION_NAMES.get(expression)
            if name is None:
                raise ValueError('unmapped Lua field expression: ' + expression)
            layout.append((name, size))
    return layout


def offsets(layout=None):
    """Return {name: (offset, size)} and the total byte count."""
    layout = layout or CURRENT_LAYOUT
    result = {}
    position = 0
    for name, size in layout:
        result[name] = (position, size)
        position += size
    return result, position
