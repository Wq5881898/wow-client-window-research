import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import client_facing


class FacingSweepTest(unittest.TestCase):
    """The turn-and-retry loop must stop as soon as the facing error ends."""

    def setUp(self):
        self.original_hold = client_facing.hold
        self.turns = []

    def tearDown(self):
        client_facing.hold = self.original_hold

    def _install(self, states):
        self.turns = []
        client_facing.hold = lambda vk, seconds: self.turns.append(vk)
        index = {'n': 0}

        def cast():
            position = min(index['n'], len(states) - 1)
            index['n'] += 1
            return states[position]

        return cast

    def test_turns_until_the_facing_error_clears(self):
        cast = self._install([
            {'last_error_reason': 5},
            {'last_error_reason': 5},
            {'last_error_reason': 0},
        ])
        steps, state = client_facing.sweep_toward(cast)
        self.assertEqual(steps, 2)
        self.assertEqual(state['last_error_reason'], 0)
        self.assertEqual(len(self.turns), 2)

    def test_gives_up_after_the_step_budget(self):
        cast = self._install([{'last_error_reason': 5}])
        steps, state = client_facing.sweep_toward(cast, max_steps=5)
        self.assertEqual(steps, 5)
        self.assertEqual(state['last_error_reason'], 5)

    def test_does_not_turn_when_the_cast_was_fine(self):
        cast = self._install([{'last_error_reason': 0}])
        steps, state = client_facing.sweep_toward(cast)
        self.assertEqual(steps, 0)
        self.assertEqual(self.turns, [])

    def test_turn_direction_is_honoured(self):
        cast = self._install([{'last_error_reason': 5}, {'last_error_reason': 0}])
        client_facing.sweep_toward(cast, direction='right')
        self.assertEqual(self.turns, [client_facing.VK_RIGHT])

    def test_the_general_last_reason_is_not_used(self):
        """A spell event clears last_reason, so only the error field counts."""
        cast = self._install([
            {'last_reason': 0, 'last_error_reason': 5},
            {'last_reason': 0, 'last_error_reason': 0},
        ])
        steps, state = client_facing.sweep_toward(cast)
        self.assertEqual(steps, 1)


if __name__ == '__main__':
    unittest.main()
