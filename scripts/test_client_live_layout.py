"""The Lua encoder and the Python decoder must agree on field order."""
import unittest
from client_live_layout import (
    CURRENT_LAYOUT, V3_LAYOUT, V4_LAYOUT, parse_lua_layout, offsets)
import client_live_state


class LayoutTests(unittest.TestCase):
    def test_lua_order_matches_current_layout(self):
        self.assertEqual(parse_lua_layout(), CURRENT_LAYOUT)

    def test_total_length_matches_declared_constants(self):
        positions, total = offsets(CURRENT_LAYOUT)
        self.assertEqual(total, client_live_state.V4_DATA_BYTES)
        self.assertEqual(client_live_state.V4_TOTAL, total)
        _, v3_total = offsets(V3_LAYOUT)
        self.assertEqual(v3_total, client_live_state.V3_DATA_BYTES)

    def test_decoder_uses_shared_offsets(self):
        self.assertEqual(client_live_state.V3_OFFSETS['health'][0], 8)
        self.assertEqual(client_live_state.V3_OFFSETS['event_queue'][0], 61)
        self.assertEqual(client_live_state.V3_OFFSETS['checksum'][0], 101)
        self.assertEqual(client_live_state.V4_OFFSETS['chat_open'][0], 61)
        self.assertEqual(client_live_state.V4_OFFSETS['target_distance'][0], 62)
        self.assertEqual(client_live_state.V4_OFFSETS['event_queue'][0], 64)
        self.assertEqual(client_live_state.V4_OFFSETS['checksum'][0], 104)

    def test_trailer_offset_matches_cell_count(self):
        self.assertEqual(client_live_state.V3_TRAILER_OFFSET,
                         client_live_state.V3_CELLS - 1)
        self.assertEqual(client_live_state.V3_CELLS,
                         3 + client_live_state.V3_DATA_BYTES + 1)
        self.assertEqual(client_live_state.V4_CELLS,
                         3 + client_live_state.V4_DATA_BYTES + 1)

    def test_unknown_lua_expression_is_rejected(self):
        source = ('local function update()\n'
                  '  number(PROTOCOL, 1)\n'
                  '  number(some_unknown_field, 2)\n'
                  'end\n')
        with self.assertRaises(ValueError):
            parse_lua_layout(source)


if __name__ == '__main__':
    unittest.main()
