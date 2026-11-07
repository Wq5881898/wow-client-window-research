import unittest
from client_cursor_controller import CursorController
from client_live_state import name_hash


def state(**changes):
    s = dict(protocol=15, sequence=1, dead=False, combat=False,
             ui_cursor_x=640, ui_cursor_y=302,
             mouse_focus_hash=name_hash('GameMenuButtonContinue'))
    s.update(changes)
    return s


class CursorTests(unittest.TestCase):
    def test_aligned_axis_stays_still_while_other_axis_moves(self):
        c = CursorController((640, 302), 'GameMenuButtonContinue')
        a = c.observe(state(ui_cursor_x=600, ui_cursor_y=301))
        self.assertEqual(a['dy'], 0)
        self.assertGreater(a['dx'], 0)

    def test_wrong_hover_at_right_coordinates_cannot_click(self):
        c = CursorController((640, 302), 'GameMenuButtonContinue')
        self.assertEqual(c.observe(state(mouse_focus_hash=5381))['action'], 'STOP')

    def test_ready_requires_position_and_hover(self):
        c = CursorController((640, 302), 'GameMenuButtonContinue')
        self.assertEqual(c.observe(state())['action'], 'READY')

    def test_out_of_bounds_produces_only_small_impulses(self):
        c = CursorController((640, 302), 'GameMenuButtonContinue', max_steps=1)
        s = state(ui_cursor_x=8192, ui_cursor_y=-17060)
        a = c.observe(s)
        self.assertEqual((a['dx'], a['dy']), (-3, -3))
        self.assertEqual(c.observe(s)['action'], 'WAIT')
        self.assertEqual(c.observe(dict(s, sequence=2))['reason'], 'step_budget')
