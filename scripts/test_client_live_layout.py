"""The Lua encoder and the Python decoder must agree on field order."""
import unittest
from client_live_layout import (
    CURRENT_LAYOUT, V3_LAYOUT, V4_LAYOUT, V5_LAYOUT, V6_LAYOUT, V7_LAYOUT,
    V8_LAYOUT, V9_LAYOUT, parse_lua_layout, offsets)
import client_live_state
from client_live_layout import PROBE


class LayoutTests(unittest.TestCase):
    def test_lua_order_matches_current_layout(self):
        self.assertEqual(parse_lua_layout(), CURRENT_LAYOUT)

    def test_total_length_matches_declared_constants(self):
        positions, total = offsets(CURRENT_LAYOUT)
        self.assertEqual(total, client_live_state.V9_DATA_BYTES)
        self.assertEqual(client_live_state.V9_TOTAL, total)
        for layout, name in ((V3_LAYOUT, 'V3'), (V4_LAYOUT, 'V4'),
                             (V5_LAYOUT, 'V5'), (V6_LAYOUT, 'V6'),
                             (V7_LAYOUT, 'V7')):
            _, layout_total = offsets(layout)
            self.assertEqual(layout_total,
                             getattr(client_live_state, name + '_DATA_BYTES'))

    def test_the_bytes_the_probe_writes_match_the_layout(self):
        # The length byte of the probe is written from its own constant, so
        # the constant and the layout have to agree.
        source = PROBE.read_text(encoding='utf-8')
        declared = int(source.split('local DATA_BYTES = ')[1].split('\n')[0])
        _, total = offsets(CURRENT_LAYOUT)
        self.assertEqual(declared, total)

    def test_the_ninth_protocol_adds_the_player_and_the_target_name(self):
        positions, total = offsets(V9_LAYOUT)
        self.assertEqual(client_live_state.V9_DATA_BYTES, total)
        self.assertEqual(positions['player_guid'][0], 113)
        self.assertEqual(positions['target_name_hash'][0], 121)
        self.assertEqual(positions['checksum'][0], 123)
        self.assertEqual(positions['weighted'][0], 124)

    def test_the_hash_of_a_name_is_the_same_in_both_languages(self):
        # The probe computes the hash in Lua, the driver in Python.
        self.assertEqual(client_live_state.name_hash(''), 5381)
        self.assertEqual(client_live_state.name_hash('a'),
                         (5381 * 33 + 97) % 65536)
        self.assertEqual(client_live_state.name_hash('Probehuman'), 7254)

    def test_decoder_uses_shared_offsets(self):
        self.assertEqual(client_live_state.V3_OFFSETS['health'][0], 8)
        self.assertEqual(client_live_state.V3_OFFSETS['event_queue'][0], 61)
        self.assertEqual(client_live_state.V3_OFFSETS['checksum'][0], 101)
        self.assertEqual(client_live_state.V4_OFFSETS['chat_open'][0], 61)
        self.assertEqual(client_live_state.V4_OFFSETS['target_distance'][0], 62)
        self.assertEqual(client_live_state.V4_OFFSETS['event_queue'][0], 64)
        self.assertEqual(client_live_state.V4_OFFSETS['checksum'][0], 104)
        self.assertEqual(client_live_state.V5_OFFSETS['last_error_reason'][0], 60)
        self.assertEqual(client_live_state.V5_OFFSETS['event_queue'][0], 65)
        self.assertEqual(client_live_state.V5_OFFSETS['checksum'][0], 105)
        self.assertEqual(client_live_state.V6_OFFSETS['last_error_reason'][0], 60)
        self.assertEqual(client_live_state.V6_OFFSETS['spell_bits'][0], 61)
        self.assertEqual(client_live_state.V6_OFFSETS['event_queue'][0], 67)
        self.assertEqual(client_live_state.V6_OFFSETS['checksum'][0], 107)
        self.assertEqual(client_live_state.V7_OFFSETS['last_error_reason'][0], 60)
        self.assertEqual(client_live_state.V7_OFFSETS['spell_bits'][0], 61)
        self.assertEqual(client_live_state.V7_OFFSETS['target_class'][0], 63)
        self.assertEqual(client_live_state.V7_OFFSETS['event_queue'][0], 68)
        self.assertEqual(client_live_state.V7_OFFSETS['checksum'][0], 108)
        self.assertEqual(client_live_state.V8_OFFSETS['facing'][0], 40)
        self.assertEqual(client_live_state.V8_OFFSETS['corpse_x'][0], 42)
        self.assertEqual(client_live_state.V8_OFFSETS['corpse_y'][0], 44)
        self.assertEqual(client_live_state.V8_OFFSETS['corpse_exists'][0], 46)
        self.assertEqual(client_live_state.V8_OFFSETS['event_queue'][0], 73)
        self.assertEqual(client_live_state.V8_OFFSETS['checksum'][0], 113)

    def test_trailer_offset_matches_cell_count(self):
        self.assertEqual(client_live_state.V3_TRAILER_OFFSET,
                         client_live_state.V3_CELLS - 1)
        self.assertEqual(client_live_state.V3_CELLS,
                         3 + client_live_state.V3_DATA_BYTES + 1)
        self.assertEqual(client_live_state.V4_CELLS,
                         3 + client_live_state.V4_DATA_BYTES + 1)
        self.assertEqual(client_live_state.V5_CELLS,
                         3 + client_live_state.V5_DATA_BYTES + 1)
        self.assertEqual(client_live_state.V6_CELLS,
                         3 + client_live_state.V6_DATA_BYTES + 1)
        self.assertEqual(client_live_state.V5_TRAILER_OFFSET,
                         client_live_state.V5_CELLS - 1)
        self.assertEqual(client_live_state.V6_TRAILER_OFFSET,
                         client_live_state.V6_CELLS - 1)

    def test_v6_only_inserts_after_the_v5_fields(self):
        """The v6 packet must keep every v5 field at the same offset."""
        v5_names = [name for name, _ in V5_LAYOUT]
        v6_names = [name for name, _ in V6_LAYOUT]
        for name in v5_names:
            if name in ('frost_armor', 'chat_open', 'target_distance',
                        'event_queue', 'checksum', 'weighted'):
                continue
            self.assertEqual(v6_names.index(name), v5_names.index(name), name)

    def test_unknown_lua_expression_is_rejected(self):
        source = ('local function update()\n'
                  '  number(PROTOCOL, 1)\n'
                  '  number(some_unknown_field, 2)\n'
                  'end\n')
        with self.assertRaises(ValueError):
            parse_lua_layout(source)


if __name__ == '__main__':
    unittest.main()
