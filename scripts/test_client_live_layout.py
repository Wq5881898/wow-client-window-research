"""The Lua encoder and the Python decoder must agree on field order."""
import unittest
from client_live_layout import V3_LAYOUT, parse_lua_layout, offsets
import client_live_state


class LayoutTests(unittest.TestCase):
    def test_lua_order_matches_python_layout(self):
        self.assertEqual(parse_lua_layout(), V3_LAYOUT)

    def test_total_length_matches_declared_constants(self):
        positions, total = offsets()
        self.assertEqual(total, client_live_state.V3_DATA_BYTES)
        self.assertEqual(client_live_state.V3_TOTAL, total)

    def test_decoder_uses_shared_offsets(self):
        self.assertEqual(client_live_state.V3_OFFSETS['health'][0], 8)
        self.assertEqual(client_live_state.V3_OFFSETS['pos_x'][0], 36)
        self.assertEqual(client_live_state.V3_OFFSETS['event_queue'][0], 61)
        self.assertEqual(client_live_state.V3_OFFSETS['checksum'][0], 101)
        self.assertEqual(client_live_state.V3_OFFSETS['weighted'][0], 102)

    def test_trailer_offset_matches_cell_count(self):
        self.assertEqual(client_live_state.V3_TRAILER_OFFSET,
                         client_live_state.V3_CELLS - 1)
        self.assertEqual(client_live_state.V3_CELLS,
                         3 + client_live_state.V3_DATA_BYTES + 1)

    def test_unknown_lua_expression_is_rejected(self):
        source = ('local function update()\n'
                  '  number(PROTOCOL, 1)\n'
                  '  number(some_unknown_field, 2)\n'
                  'end\n')
        with self.assertRaises(ValueError):
            parse_lua_layout(source)


if __name__ == '__main__':
    unittest.main()
