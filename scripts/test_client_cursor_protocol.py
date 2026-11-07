import unittest
from client_live_layout import V15_LAYOUT, offsets
from client_live_state import _decode_v15, V15_DATA_BYTES, name_hash


class CursorProtocolTests(unittest.TestCase):
    def test_signed_out_of_bounds_coordinates_are_not_clamped(self):
        table, total = offsets(V15_LAYOUT)
        self.assertEqual(total, V15_DATA_BYTES)
        data = bytearray(total)
        values = {'ui_cursor_x': 8192, 'ui_cursor_y': -17060,
                  'ui_width': 1517, 'ui_height': 853,
                  'mouse_focus_hash': name_hash('WorldFrame'), 'game_menu': 1}
        for name, value in values.items():
            start, size = table[name]
            data[start:start + size] = value.to_bytes(
                size, 'little', signed=name in ('ui_cursor_x', 'ui_cursor_y'))
        decoded = _decode_v15(data)
        for name, value in values.items():
            self.assertEqual(decoded[name], value)


if __name__ == '__main__':
    unittest.main()
