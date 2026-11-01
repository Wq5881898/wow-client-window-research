"""Decode read-only pixel telemetry; reject damaged, absent and frozen frames."""
import time
from PIL import Image
from client_live_layout import V3_LAYOUT, V4_LAYOUT, V5_LAYOUT, offsets

UI_BASE_HEIGHT = 768
LEGACY_CELL_UNITS = 12
V3_CELL_UNITS = 8
V3_DATA_BYTES = 103
V4_DATA_BYTES = 106
V5_DATA_BYTES = 107
V3_CELLS = 107            # 3 markers + payload + end marker
V4_CELLS = 110
V5_CELLS = 111
V3_TRAILER_OFFSET = 106   # cells between the first marker and the end marker
V4_TRAILER_OFFSET = 109
V5_TRAILER_OFFSET = 110
V3_OFFSETS, V3_TOTAL = offsets(V3_LAYOUT)
V4_OFFSETS, V4_TOTAL = offsets(V4_LAYOUT)
V5_OFFSETS, V5_TOTAL = offsets(V5_LAYOUT)


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
    return None


def decode(image):
    image = image.convert('RGB')
    pixels = image.load()
    for y, x, blue in _row_strips(pixels, image):
        trio_pitch = (blue - x) / 2
        # The trailing marker fixes the exact cell pitch for the whole strip.
        for trailer_left in _yellow_runs(pixels, y, blue, image.width):
            for offset in (V5_TRAILER_OFFSET, V4_TRAILER_OFFSET, V3_TRAILER_OFFSET):
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
