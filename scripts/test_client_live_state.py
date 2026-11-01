"""Telemetry corruption, protocol layout and frozen/replayed frame regression checks."""
import unittest
from PIL import Image
from client_live_state import decode, Freshness, assert_real_frame, SessionUnavailable
from client_live_layout import V3_LAYOUT, V4_LAYOUT, offsets


def build_strip(data, pitch=16.875, origin=28.125, top=150, height=16, trailer=False):
    """Render the marker trio plus payload cells the way the probe draws them."""
    image = Image.new('RGB', (1920, 1080), (25, 36, 40))
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    colors += [(value, value, value) for value in data]
    if trailer:
        colors.append((255, 0, 255))
    for index, color in enumerate(colors):
        left = round(origin + index * pitch)
        image.paste(color, (left, top, round(origin + (index + 1) * pitch), top + height))
    return image


def build_payload(layout, values):
    """Build a payload from a field map using the layout offsets."""
    table, total = offsets(layout)
    data = bytearray(total)
    for name, value in values.items():
        offset, size = table[name]
        data[offset:offset + size] = int(value).to_bytes(size, 'little')
    data[table['checksum'][0]] = sum(data[:total - 2]) % 256
    data[table['weighted'][0]] = sum(
        (index + 1) * value for index, value in enumerate(data[:total - 2])) % 65521 % 256
    return bytes(data)


def v1_payload():
    data = bytearray(36)
    data[0] = 1
    data[1], data[2] = 200, 0
    data[7], data[8] = 52, 0
    data[9], data[10] = 52, 0
    data[19] = 2
    data[20] = 1
    data[35] = sum(data[:35]) % 256
    return bytes(data)


def v2_payload():
    data = bytearray(60)
    data[0] = 2
    data[7], data[8] = 52, 0
    data[9], data[10] = 52, 0
    data[19] = 2
    data[20] = 1
    data[35] = sum(data[:35]) % 256
    data[40], data[41] = 1, 0
    data[46], data[47] = 168, 0
    data[48] = 2
    data[53] = 1
    data[59] = sum(data[:59]) % 256
    return bytes(data)


class LiveStateTests(unittest.TestCase):
    def test_freeze_and_advancement(self):
        tracker = Freshness()
        a = dict(sequence=1, game_ms=100)
        b = dict(sequence=2, game_ms=200)
        self.assertFalse(tracker.observe(a, 0))
        self.assertTrue(tracker.observe(b, 0.1))
        self.assertTrue(tracker.observe(b, 0.5))
        with self.assertRaisesRegex(ValueError, 'stale'):
            tracker.observe(b, 1.11)

    def test_v1_packet_and_corruption(self):
        state = decode(build_strip(v1_payload()))
        self.assertEqual(state['health'], 52)
        self.assertEqual(state['protocol'], 1)
        broken = build_strip(v1_payload())
        broken.paste((55, 55, 55), (round(28.125 + 10 * 16.875), 150,
                                   round(28.125 + 11 * 16.875), 166))
        with self.assertRaises(ValueError):
            decode(broken)

    def test_v2_event_packet(self):
        state = decode(build_strip(v2_payload()))
        self.assertEqual(state['event_spell'], 168)
        self.assertEqual(state['cast_succeeded'], 1)
        self.assertTrue(state['frost_armor'])
        self.assertEqual(state['protocol'], 2)

    def test_v3_layout_positions_and_queue(self):
        data = build_payload(V3_LAYOUT, {
            'protocol': 3, 'length': 103, 'sequence': 7, 'game_ms': 123456,
            'health': 52, 'max_health': 52, 'power': 165, 'spell_range': 2,
            'spell_learned': 1, 'pos_x': 40000, 'pos_y': 30000,
            'event_serial': 2, 'cast_succeeded': 1, 'last_kind': 2,
            'last_spell': 168, 'last_at': 987654, 'frost_armor': 1,
        })
        state = decode(build_strip(data, pitch=11.25, trailer=True))
        self.assertEqual(state['protocol'], 3)
        self.assertEqual(state['health'], 52)
        self.assertEqual(state['sequence'], 7)
        self.assertEqual(state['game_ms'], 123456)
        self.assertAlmostEqual(state['pos_x'], 40000 / 65535, places=6)
        self.assertAlmostEqual(state['pos_y'], 30000 / 65535, places=6)
        self.assertEqual(state['event_spell'], 168)
        self.assertEqual(state['event_kind'], 2)
        self.assertEqual(state['event_serial'], 2)
        self.assertEqual(state['cast_succeeded'], 1)
        self.assertTrue(state['frost_armor'])
        self.assertEqual(len(state['events']), 4)

    def test_v4_adds_chat_and_distance(self):
        data = build_payload(V4_LAYOUT, {
            'protocol': 4, 'length': 106, 'sequence': 9, 'game_ms': 555,
            'health': 40, 'max_health': 52, 'power': 100, 'combat': 1,
            'target_health': 7, 'target_max_health': 30, 'target_exists': 1,
            'target_attackable': 1, 'chat_open': 1, 'target_distance': 235,
            'pos_x': 1000, 'pos_y': 2000, 'spell_range': 1, 'spell_learned': 1,
        })
        state = decode(build_strip(data, pitch=11.25, trailer=True))
        self.assertEqual(state['protocol'], 4)
        self.assertTrue(state['chat_open'])
        self.assertEqual(state['target_distance'], 23.5)
        self.assertTrue(state['combat'])
        self.assertEqual(state['target_health'], 7)
        self.assertEqual(state['health'], 40)

    def test_v3_and_v4_offsets_do_not_collide(self):
        v3, total_v3 = offsets(V3_LAYOUT)
        v4, total_v4 = offsets(V4_LAYOUT)
        self.assertEqual(total_v3, 103)
        self.assertEqual(total_v4, 106)
        self.assertNotEqual(v3['event_queue'], v4['event_queue'])
        self.assertEqual(v3['event_queue'][0], 61)
        self.assertEqual(v4['event_queue'][0], 64)

    def test_v4_corruption_and_truncation(self):
        data = build_payload(V4_LAYOUT, {
            'protocol': 4, 'length': 106, 'health': 52, 'max_health': 52,
            'spell_learned': 1, 'pos_x': 100, 'pos_y': 200, 'chat_open': 1,
        })
        broken = build_strip(data, pitch=11.25, trailer=True)
        broken.paste((201, 201, 201), (round(28.125 + 5 * 11.25), 150,
                                    round(28.125 + 6 * 11.25), 166))
        with self.assertRaises(ValueError):
            decode(broken)
        short = bytearray(data)
        short[1] = 40
        with self.assertRaises(ValueError):
            decode(build_strip(short, pitch=11.25, trailer=True))

    def test_blank_frame_is_rejected(self):
        blank = Image.new('RGB', (1920, 1080), (0, 0, 0))
        with self.assertRaises(SessionUnavailable):
            assert_real_frame(blank)

    def test_busy_frame_is_accepted(self):
        busy = Image.new('RGB', (1920, 1080), (12, 34, 56))
        busy.paste((200, 30, 40), (10, 10, 40, 40))
        self.assertIs(assert_real_frame(busy), busy)

    def test_absent_panel(self):
        with self.assertRaises(ValueError):
            decode(Image.new('RGB', (1920, 1080)))


if __name__ == '__main__':
    unittest.main()
