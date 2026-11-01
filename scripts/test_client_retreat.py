import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import client_retreat


class BreakEngagementTest(unittest.TestCase):
    """The retreat primitive must not report an escape it did not observe."""

    def _patch(self, states):
        calls = []
        steps = []

        def fake_hold(vk, seconds, hwnd=None):
            calls.append(('hold', vk, seconds))

        def fake_sampler():
            index = min(len(steps), len(states) - 1)
            steps.append(index)
            return states[index]

        client_retreat.hold = fake_hold
        client_retreat.d.ensure_foreground = lambda hwnd: None
        client_retreat.window_observable = lambda hwnd: True
        return calls, steps, fake_sampler

    def setUp(self):
        self.original_hold = client_retreat.hold
        self.original_ensure = client_retreat.d.ensure_foreground
        self.original_window = client_retreat.window_observable
        self.original_focus = client_retreat.ensure_focus
        client_retreat.ensure_focus = lambda hwnd: True

    def tearDown(self):
        client_retreat.hold = self.original_hold
        client_retreat.d.ensure_foreground = self.original_ensure
        client_retreat.window_observable = self.original_window
        client_retreat.ensure_focus = self.original_focus

    def test_turns_before_running(self):
        calls, steps, sampler = self._patch([
            {'health': 30, 'combat': False, 'pos_x': 1.0, 'pos_y': 2.0},
        ])
        records = client_retreat.break_engagement(1, sampler, steps=4)
        self.assertEqual(len(records), 1)
        self.assertFalse(records[0]['combat'])
        keys = [entry[1] for entry in calls]
        self.assertEqual(keys[0], client_retreat.VK_TURN_LEFT)
        self.assertEqual(keys[1], client_retreat.VK_FORWARD)

    def test_reports_position_change(self):
        calls, steps, sampler = self._patch([
            {'health': 30, 'combat': True, 'pos_x': 1.0, 'pos_y': 2.0},
            {'health': 29, 'combat': False, 'pos_x': 1.5, 'pos_y': 2.5},
        ])
        records = client_retreat.break_engagement(1, sampler, steps=4)
        self.assertEqual(len(records), 2)
        self.assertTrue(records[1]['moved'])

    def test_unproven_escape_raises(self):
        calls, steps, sampler = self._patch([
            {'health': 30, 'combat': True, 'pos_x': 1.0, 'pos_y': 2.0},
        ])
        with self.assertRaises(ValueError):
            client_retreat.break_engagement(1, sampler, steps=3)

    def test_backward_hold_is_not_used(self):
        calls, steps, sampler = self._patch([
            {'health': 30, 'combat': False, 'pos_x': 1.0, 'pos_y': 2.0},
        ])
        client_retreat.break_engagement(1, sampler, steps=2)
        self.assertNotIn(client_retreat.VK_BACK, [entry[1] for entry in calls])


if __name__ == '__main__':
    unittest.main()
