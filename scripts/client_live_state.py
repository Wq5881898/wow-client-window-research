"""Decode read-only pixel telemetry; reject damaged, absent and frozen frames."""
import time
from PIL import Image
from client_live_layout import (V3_LAYOUT, V4_LAYOUT, V5_LAYOUT, V6_LAYOUT,
                                 V7_LAYOUT, V8_LAYOUT, V9_LAYOUT,
                                 V10_LAYOUT, V11_LAYOUT, V12_LAYOUT,
                                 V13_LAYOUT, offsets)

UI_BASE_HEIGHT = 768
LEGACY_CELL_UNITS = 12
V3_CELL_UNITS = 8
V3_DATA_BYTES = 103
V4_DATA_BYTES = 106
V5_DATA_BYTES = 107
V6_DATA_BYTES = 109
V7_DATA_BYTES = 110
V8_DATA_BYTES = 115
V9_DATA_BYTES = 125
V10_DATA_BYTES = 126
V11_DATA_BYTES = 133
V12_DATA_BYTES = 140
V13_DATA_BYTES = 140
V3_CELLS = 107            # 3 markers + payload + end marker
V4_CELLS = 110
V5_CELLS = 111
V6_CELLS = 113
V7_CELLS = 114
V8_CELLS = 119
V9_CELLS = 129
V10_CELLS = 130
V11_CELLS = 137
V12_CELLS = 144
V13_CELLS = 144
V3_TRAILER_OFFSET = 106   # cells between the first marker and the end marker
V4_TRAILER_OFFSET = 109
V5_TRAILER_OFFSET = 110
V6_TRAILER_OFFSET = 112
V7_TRAILER_OFFSET = 113
V8_TRAILER_OFFSET = 118
V9_TRAILER_OFFSET = 128
V10_TRAILER_OFFSET = 129
V11_TRAILER_OFFSET = 136
V12_TRAILER_OFFSET = 143
V13_TRAILER_OFFSET = 143
V3_OFFSETS, V3_TOTAL = offsets(V3_LAYOUT)
V4_OFFSETS, V4_TOTAL = offsets(V4_LAYOUT)
V5_OFFSETS, V5_TOTAL = offsets(V5_LAYOUT)
V6_OFFSETS, V6_TOTAL = offsets(V6_LAYOUT)
V7_OFFSETS, V7_TOTAL = offsets(V7_LAYOUT)
V8_OFFSETS, V8_TOTAL = offsets(V8_LAYOUT)
V9_OFFSETS, V9_TOTAL = offsets(V9_LAYOUT)
V10_OFFSETS, V10_TOTAL = offsets(V10_LAYOUT)
V11_OFFSETS, V11_TOTAL = offsets(V11_LAYOUT)
V12_OFFSETS, V12_TOTAL = offsets(V12_LAYOUT)
V13_OFFSETS, V13_TOTAL = offsets(V13_LAYOUT)

# The spells the probe reports in the spell_bits field.
SPELL_BITS = {
    123: 'Frostbolt',
    116: 'Frost Nova',
    120: 'Frost Ward',
    122: 'Frost Shock',
    133: 'Fireball',
    168: 'Frost Armor',
    213: 'Fireball rank 2',
    212: 'Fireball rank 3',
}

# The classification of the target as reported by the client.
TARGET_CLASSES = {
    0: 'no target',
    1: 'ordinary',
    2: 'elite',
    3: 'rare elite',
    4: 'world boss',
    5: 'rare',
    6: 'trivial',
    7: 'quest',
}


def _marker(pixel, index):
    r, g, b = pixel
    if index == 0:
        return r > 190 and g < 60 and b < 60
    if index == 1:
        return g > 190 and r < 60 and b < 60
    if index == 2:
        return b > 190 and r < 60 and g < 60
    return r > 190 and b > 190 and g < 60


def _row_strips(pixels, image):
    """Yield (y, x, blue_x) for red/green/blue marker triples on a row.

    The probe panel was moved to the bottom left so that it no longer covers
    the target frame, the unit nameplates or the resurrection NPC menu, so
    the whole screen height is searched.
    """
    width, height = image.width, image.height
    for y in range(10, height - 10):
        x = 0
        while x < min(width, 700):
            if not _marker(pixels[x, y], 0):
                x += 1
                continue
            green = blue = None
            for xx in range(x + 1, min(width, x + 80)):
                if green is None and _marker(pixels[xx, y], 1):
                    green = xx
                elif green is not None and _marker(pixels[xx, y], 2):
                    blue = xx
                    break
            if green is not None and blue is not None:
                yield y, x, blue
            x += 1


def _yellow_runs(pixels, y, start, image_width):
    """Left edges of pure magenta runs to the right of the marker triple."""
    runs = []
    index = start
    while index < image_width:
        if _marker(pixels[index, y], 3):
            left = index
            while left > 0 and _marker(pixels[left - 1, y], 3):
                left -= 1
            runs.append(left)
            index = left
            while index < image_width and _marker(pixels[index, y], 3):
                index += 1
        else:
            index += 1
    return runs


def _read_cells(pixels, y, x0, pitch, count, image_width):
    data = bytearray()
    for index in range(count):
        center = int(round(x0 + (3 + index) * pitch + pitch / 2))
        if center >= image_width:
            return None
        r, g, b = pixels[center, y]
        if max(r, g, b) - min(r, g, b) > 12:
            return None
        data.append(r)
    return bytes(data)


def _decode_v1(data):
    def n(start, size):
        return int.from_bytes(data[start:start + size], 'little')
    return dict(sequence=n(1, 2), game_ms=n(3, 4), health=n(7, 2),
                max_health=n(9, 2), power=n(11, 2), combat=bool(data[13]),
                dead=bool(data[14]), target_health=n(15, 2),
                target_max_health=n(17, 2), spell_range=data[19],
                spell_learned=bool(data[20]), casting=bool(data[21]),
                speed=n(22, 2) / 100,
                target_guid='0x' + data[24:32].hex().upper(),
                target_exists=bool(data[32]), target_attackable=bool(data[33]),
                target_dead=bool(data[34]))


def _decode_v2(data):
    result = _decode_v1(data)
    def n(start, size):
        return int.from_bytes(data[start:start + size], 'little')
    result.update(event_serial=n(36, 2), cast_started=n(38, 2),
                  cast_succeeded=n(40, 2), cast_failed=n(42, 2),
                  ui_errors=n(44, 2), event_spell=n(46, 2),
                  event_kind=data[48], event_ms=n(49, 4),
                  frost_armor=bool(data[53]))
    return result


def _base_state(data, table):
    def n(name):
        offset, size = table[name]
        return int.from_bytes(data[offset:offset + size], 'little')
    def flag(name):
        return bool(data[table[name][0]])
    result = dict(sequence=n('sequence'), game_ms=n('game_ms'),
                  health=n('health'), max_health=n('max_health'),
                  power=n('power'), combat=flag('combat'), dead=flag('dead'),
                  target_health=n('target_health'),
                  target_max_health=n('target_max_health'),
                  spell_range=data[table['spell_range'][0]],
                  spell_learned=flag('spell_learned'), casting=flag('casting'),
                  speed=n('speed') / 100,
                  target_guid='0x' + data[table['target_guid'][0]:
                                          table['target_guid'][0] + 8].hex().upper(),
                  target_exists=flag('target_exists'),
                  target_attackable=flag('target_attackable'),
                  target_dead=flag('target_dead'),
                  pos_x=n('pos_x') / 65535, pos_y=n('pos_y') / 65535,
                  facing=n('facing') / 10430,
                  event_serial=n('event_serial'), cast_started=n('cast_started'),
                  cast_succeeded=n('cast_succeeded'), cast_failed=n('cast_failed'),
                  ui_errors=n('ui_errors'),
                  event_kind=data[table['last_kind'][0]],
                  event_spell=n('last_spell'), event_ms=n('last_at'),
                  last_reason=data[table['last_reason'][0]],
                  frost_armor=flag('frost_armor'))
    queue_base, queue_size = table['event_queue']
    events = []
    for index in range(queue_size // 10):
        base = queue_base + index * 10
        events.append(dict(serial=int.from_bytes(data[base:base + 2], 'little'),
                           kind=data[base + 2],
                           spell=int.from_bytes(data[base + 3:base + 5], 'little'),
                           at=int.from_bytes(data[base + 5:base + 9], 'little'),
                           reason=data[base + 9]))
    result['events'] = events
    return result


def _decode_v3(data):
    return _base_state(data, V3_OFFSETS)


def _decode_v4(data):
    result = _base_state(data, V4_OFFSETS)
    result['chat_open'] = bool(data[V4_OFFSETS['chat_open'][0]])
    offset, size = V4_OFFSETS['target_distance']
    result['target_distance'] = int.from_bytes(data[offset:offset + size], 'little') / 10
    return result


def _decode_v5(data):
    result = _base_state(data, V5_OFFSETS)
    result['chat_open'] = bool(data[V5_OFFSETS['chat_open'][0]])
    offset, size = V5_OFFSETS['target_distance']
    result['target_distance'] = int.from_bytes(data[offset:offset + size], 'little') / 10
    result['last_error_reason'] = data[V5_OFFSETS['last_error_reason'][0]]
    return result


def _decode_v6(data):
    result = _base_state(data, V6_OFFSETS)
    result['chat_open'] = bool(data[V6_OFFSETS['chat_open'][0]])
    offset, size = V6_OFFSETS['target_distance']
    result['target_distance'] = int.from_bytes(data[offset:offset + size], 'little') / 10
    result['last_error_reason'] = data[V6_OFFSETS['last_error_reason'][0]]
    offset, size = V6_OFFSETS['spell_bits']
    bits = int.from_bytes(data[offset:offset + size], 'little')
    result['spell_bits'] = bits
    result['known_spells'] = sorted(
        spell_id for spell_id in SPELL_BITS if bits & (1 << _spell_bit(spell_id)))
    return result


def _decode_v7(data):
    result = _base_state(data, V7_OFFSETS)
    result['chat_open'] = bool(data[V7_OFFSETS['chat_open'][0]])
    offset, size = V7_OFFSETS['target_distance']
    result['target_distance'] = int.from_bytes(data[offset:offset + size], 'little') / 10
    result['last_error_reason'] = data[V7_OFFSETS['last_error_reason'][0]]
    offset, size = V7_OFFSETS['spell_bits']
    bits = int.from_bytes(data[offset:offset + size], 'little')
    result['spell_bits'] = bits
    result['known_spells'] = sorted(
        spell_id for spell_id in SPELL_BITS if bits & (1 << _spell_bit(spell_id)))
    result['target_class'] = data[V7_OFFSETS['target_class'][0]]
    result['target_class_name'] = TARGET_CLASSES.get(result['target_class'], 'unknown')
    return result


def _spell_bit(spell_id):
    """The bit position of a spell inside the spell_bits field."""
    order = [123, 116, 120, 122, 133, 168, 213, 212]
    return order.index(spell_id)


def _decode_v8(data):
    result = _base_state(data, V8_OFFSETS)
    result['chat_open'] = bool(data[V8_OFFSETS['chat_open'][0]])
    offset, size = V8_OFFSETS['target_distance']
    result['target_distance'] = int.from_bytes(data[offset:offset + size], 'little') / 10
    result['last_error_reason'] = data[V8_OFFSETS['last_error_reason'][0]]
    offset, size = V8_OFFSETS['spell_bits']
    bits = int.from_bytes(data[offset:offset + size], 'little')
    result['spell_bits'] = bits
    result['known_spells'] = sorted(
        spell_id for spell_id in SPELL_BITS if bits & (1 << _spell_bit(spell_id)))
    result['target_class'] = data[V8_OFFSETS['target_class'][0]]
    result['target_class_name'] = TARGET_CLASSES.get(result['target_class'], 'unknown')
    # The heading of the character and the spot of its corpse.
    offset, size = V8_OFFSETS['corpse_x']
    result['corpse_x'] = int.from_bytes(data[offset:offset + size], 'little') / 65535
    offset, size = V8_OFFSETS['corpse_y']
    result['corpse_y'] = int.from_bytes(data[offset:offset + size], 'little') / 65535
    result['corpse_exists'] = bool(data[V8_OFFSETS['corpse_exists'][0]])
    return result


def name_hash(text):
    """The hash of a name, the same way the probe computes it."""
    digest = 5381
    for value in text.encode('utf-8'):
        digest = (digest * 33 + value) % 65536
    return digest


def _decode_v9(data):
    result = _decode_v8(data)
    offset, size = V9_OFFSETS['player_guid']
    parts = []
    for index in range(offset, offset + size):
        parts.append('%02X' % data[index])
    result['player_guid'] = '0x' + ''.join(parts)
    offset, size = V9_OFFSETS['target_name_hash']
    result['target_name_hash'] = int.from_bytes(data[offset:offset + size],
                                                 'little')
    return result


def _decode_v10(data):
    result = _decode_v9(data)
    result['threat'] = data[V10_OFFSETS['threat'][0]]
    return result


def _decode_v11(data):
    result = _decode_v10(data)
    result['level'] = data[V11_OFFSETS['level'][0]]
    offset, size = V11_OFFSETS['xp']
    result['xp'] = int.from_bytes(data[offset:offset + size], 'little')
    offset, size = V11_OFFSETS['xp_max']
    result['xp_max'] = int.from_bytes(data[offset:offset + size], 'little')
    return result


def _decode_v12(data):
    result = _decode_v11(data)
    offset, size = V12_OFFSETS['money']
    result['money'] = int.from_bytes(data[offset:offset + size], 'little')
    result['bag_items'] = data[V12_OFFSETS['bag_items'][0]]
    offset, size = V12_OFFSETS['npc_name_hash']
    result['npc_name_hash'] = int.from_bytes(data[offset:offset + size], 'little')
    return result


def _decode_v13(data):
    result = _decode_v12(data)
    offset, size = V13_OFFSETS['cursor_name_hash']
    result['cursor_name_hash'] = int.from_bytes(data[offset:offset + size],
                                                'little')
    return result


def _checksum_ok(data, length):
    if sum(data[:length - 2]) % 256 != data[length - 2]:
        return False
    weighted = sum((index + 1) * value for index, value
                   in enumerate(data[:length - 2])) % 65521
    return weighted % 256 == data[length - 1]


def _attempt(pixels, image, y, x, pitch):
    header = _read_cells(pixels, y, x, pitch, 2, image.width)
    if header is None:
        return None
    version = header[0]
    if version == 1:
        data = _read_cells(pixels, y, x, pitch, 36, image.width)
        if data is None or sum(data[:35]) % 256 != data[35]:
            return None
        return version, _decode_v1(data)
    if version == 2:
        data = _read_cells(pixels, y, x, pitch, 60, image.width)
        if data is None:
            return None
        if sum(data[:35]) % 256 != data[35] or sum(data[:59]) % 256 != data[59]:
            return None
        return version, _decode_v2(data)
    if version == 3:
        if header[1] != V3_DATA_BYTES:
            return None
        data = _read_cells(pixels, y, x, pitch, V3_DATA_BYTES, image.width)
        if data is None or not _checksum_ok(data, V3_DATA_BYTES):
            return None
        return version, _decode_v3(data)
    if version == 4:
        if header[1] != V4_DATA_BYTES:
            return None
        data = _read_cells(pixels, y, x, pitch, V4_DATA_BYTES, image.width)
        if data is None or not _checksum_ok(data, V4_DATA_BYTES):
            return None
        return version, _decode_v4(data)
    if version == 5:
        if header[1] != V5_DATA_BYTES:
            return None
        data = _read_cells(pixels, y, x, pitch, V5_DATA_BYTES, image.width)
        if data is None or not _checksum_ok(data, V5_DATA_BYTES):
            return None
        return version, _decode_v5(data)
    if version == 6:
        if header[1] != V6_DATA_BYTES:
            return None
        data = _read_cells(pixels, y, x, pitch, V6_DATA_BYTES, image.width)
        if data is None or not _checksum_ok(data, V6_DATA_BYTES):
            return None
        return version, _decode_v6(data)
    if version == 7:
        if header[1] != V7_DATA_BYTES:
            return None
        data = _read_cells(pixels, y, x, pitch, V7_DATA_BYTES, image.width)
        if data is None or not _checksum_ok(data, V7_DATA_BYTES):
            return None
        return version, _decode_v7(data)
    if version == 8:
        if header[1] != V8_DATA_BYTES:
            return None
        data = _read_cells(pixels, y, x, pitch, V8_DATA_BYTES, image.width)
        if data is None or not _checksum_ok(data, V8_DATA_BYTES):
            return None
        return version, _decode_v8(data)
    if version == 9:
        if header[1] != V9_DATA_BYTES:
            return None
        data = _read_cells(pixels, y, x, pitch, V9_DATA_BYTES, image.width)
        if data is None or not _checksum_ok(data, V9_DATA_BYTES):
            return None
        return version, _decode_v9(data)
    if version == 10:
        if header[1] != V10_DATA_BYTES:
            return None
        data = _read_cells(pixels, y, x, pitch, V10_DATA_BYTES, image.width)
        if data is None or not _checksum_ok(data, V10_DATA_BYTES):
            return None
        return version, _decode_v10(data)
    if version == 11:
        if header[1] != V11_DATA_BYTES:
            return None
        data = _read_cells(pixels, y, x, pitch, V11_DATA_BYTES, image.width)
        if data is None or not _checksum_ok(data, V11_DATA_BYTES):
            return None
        return version, _decode_v11(data)
    if version == 12:
        if header[1] != V12_DATA_BYTES:
            return None
        data = _read_cells(pixels, y, x, pitch, V12_DATA_BYTES, image.width)
        if data is None or not _checksum_ok(data, V12_DATA_BYTES):
            return None
        return version, _decode_v12(data)
    if version == 13:
        if header[1] != V13_DATA_BYTES:
            return None
        data = _read_cells(pixels, y, x, pitch, V13_DATA_BYTES, image.width)
        if data is None or not _checksum_ok(data, V13_DATA_BYTES):
            return None
        return version, _decode_v13(data)
    return None


def decode(image):
    image = image.convert('RGB')
    pixels = image.load()
    for y, x, blue in _row_strips(pixels, image):
        trio_pitch = (blue - x) / 2
        # The trailing marker fixes the exact cell pitch for the whole strip.
        for trailer_left in _yellow_runs(pixels, y, blue, image.width):
            for offset in (V13_TRAILER_OFFSET, V12_TRAILER_OFFSET,
                           V11_TRAILER_OFFSET,
                           V10_TRAILER_OFFSET,
                           V9_TRAILER_OFFSET,
                           V8_TRAILER_OFFSET,
                           V7_TRAILER_OFFSET, V6_TRAILER_OFFSET,
                           V5_TRAILER_OFFSET, V4_TRAILER_OFFSET,
                           V3_TRAILER_OFFSET):
                measured = (trailer_left - x) / offset
                if abs(measured - trio_pitch) > 1.0:
                    continue
                attempt = _attempt(pixels, image, y, x, measured)
                if attempt is not None:
                    version, result = attempt
                    result['protocol'] = version
                    return result
        # Without a usable trailer, fall back to the scale-derived pitch.
        scale = image.height / UI_BASE_HEIGHT
        for pitch in (V3_CELL_UNITS * scale, LEGACY_CELL_UNITS * scale):
            attempt = _attempt(pixels, image, y, x, pitch)
            if attempt is not None:
                version, result = attempt
                result['protocol'] = version
                return result
    raise ValueError('live telemetry absent or invalid')


class SessionUnavailable(RuntimeError):
    """Raised when the desktop capture path cannot deliver real pixels."""


def assert_real_frame(image):
    """Reject blank frames produced while the interactive session is disconnected."""
    rgb = image.convert('RGB')
    corners = [rgb.getpixel((0, 0)), rgb.getpixel((rgb.width - 1, 0)),
               rgb.getpixel((0, rgb.height - 1)),
               rgb.getpixel((rgb.width - 1, rgb.height - 1)),
               rgb.getpixel((rgb.width // 2, rgb.height // 2))]
    if len(set(corners)) == 1 and corners[0] == (0, 0, 0):
        raise SessionUnavailable('desktop capture is blank; interactive session is not rendering')
    return image


class Freshness:
    def __init__(self, timeout=1.0):
        self.timeout = timeout
        self.token = None
        self.changed_at = None
        self.advancing = False
        self.failed = False

    def reset(self):
        """Accept a new baseline.

        The driver pauses the sampling on purpose in a few places, for
        example while it looks for another target. The gap is then known
        and does not mean that the panel of the client is stuck.
        """
        self.token = None
        self.changed_at = None
        self.advancing = False
        self.failed = False

    def observe(self, state, now=None):
        now = time.monotonic() if now is None else now
        if self.failed:
            raise ValueError('live telemetry session rejected; explicit rebaseline required')
        token = state['sequence'], state['game_ms']
        if self.token is not None:
            seq_delta = (token[0] - self.token[0]) % 65536
            time_delta = (token[1] - self.token[1]) % 4294967296
            if now < self.changed_at or now - self.changed_at > self.timeout:
                self.failed = True
                raise ValueError('live telemetry stale or host time reversed')
            if token != self.token and not (0 < seq_delta < 32768 and 0 < time_delta < 2147483648):
                self.failed = True
                raise ValueError('live telemetry replay or session discontinuity')
        if token != self.token:
            self.advancing = self.token is not None
            self.token, self.changed_at = token, now
            return self.advancing
        if now - self.changed_at > self.timeout:
            self.failed = True
            raise ValueError('live telemetry stale')
        return self.advancing


if __name__ == '__main__':
    import json
    import sys
    print(json.dumps(decode(Image.open(sys.argv[1])), indent=2))
