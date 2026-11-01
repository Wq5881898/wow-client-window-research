"""Telemetry corruption, protocol layout and frozen/replayed frame regression checks."""
import unittest
from PIL import Image
from client_live_state import decode, Freshness, assert_real_frame, SessionUnavailable


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
    data[1], data[2] = 7, 0
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


def v3_payload():
    data = bytearray(103)
    data[0] = 3
    data[1] = 103
    data[2], data[3] = 7, 0
    data[4:8] = (123456).to_bytes(4, 'little')
    data[8], data[9] = 52, 0
    data[10], data[11] = 52, 0
    data[20] = 2
    data[21] = 1
    data[36:38] = (40000).to_bytes(2, 'little')
    data[38:40] = (30000).to_bytes(2, 'little')
    data[42], data[43] = 2, 0
    data[46], data[47] = 1, 0
    data[52] = 2
    data[53:55] = (168).to_bytes(2, 'little')
    data[55:59] = (987654).to_bytes(4, 'little')
    data[60] = 1
    base = 61
    data[base], data[base + 1] = 2, 0
    data[base + 2] = 2
    data[base + 3:base + 5] = (168).to_bytes(2, 'little')
    data[base + 5:base + 9] = (987654).to_bytes(4, 'little')
    data[101] = sum(data[:101]) % 256
    data[102] = sum((index + 1) * value for index, value in enumerate(data[:101])) % 65521 % 256
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
        state = decode(build_strip(v3_payload(), pitch=11.25, trailer=True))
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
        self.assertEqual(state['events'][0]['kind'], 2)
        self.assertEqual(state['events'][0]['spell'], 168)
        self.assertEqual(state['events'][0]['serial'], 2)
        self.assertEqual(state['events'][0]['at'], 987654)

    def test_v3_corruption_and_truncation(self):
        broken = build_strip(v3_payload(), pitch=11.25, trailer=True)
        broken.paste((201, 201, 201), (round(28.125 + 5 * 11.25), 150,
                                    round(28.125 + 6 * 11.25), 166))
        with self.assertRaises(ValueError):
            decode(broken)
        short = bytearray(v3_payload())
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
