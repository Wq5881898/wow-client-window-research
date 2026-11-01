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

CURRENT_LAYOUT = V7_LAYOUT

EXPRESSION_NAMES = {
    'PROTOCOL': 'protocol',
    '103': 'length',
    '106': 'length',
    '107': 'length',
    '109': 'length',
    '110': 'length',
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
    for chunk in re.split(r'[\x00]', body):
        if chunk == 'GUID':
            layout.append(('target_guid', 8))
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
