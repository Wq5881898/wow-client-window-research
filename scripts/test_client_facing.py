import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import client_facing


class CastProbeTest(unittest.TestCase):
    """The sweep must stop at the first successful cast."""

    def setUp(self):
        self.original_hold = client_facing.hold
        self.turns = []

    def tearDown(self):
        client_facing.hold = self.original_hold

    def _install(self, outcomes):
        """Build a probe whose attempts follow the given outcome list.

        The reader returns the state that is current, and an attempt moves
        the probe to the next state, which is how the real client behaves.
        """
        self.turns = []
        client_facing.hold = lambda vk, seconds: self.turns.append(vk)
        state = {'current': dict(outcomes[0]), 'outcomes': outcomes,
                 'index': 0}

        def reader():
            return state['current']

        def attempt():
            state['index'] = min(state['index'] + 1, len(outcomes) - 1)
            state['current'] = outcomes[state['index']]
            return state['current']

        return reader, attempt

    def _probe(self, reader, attempt):
        return client_facing.CastProbe(attempt, reader)

    def test_turns_until_the_cast_succeeds(self):
        outcomes = [
            {'cast_failed': 0, 'cast_succeeded': 0, 'last_error_reason': 0},
            {'cast_failed': 1, 'cast_succeeded': 0, 'last_error_reason': 1},
            {'cast_failed': 2, 'cast_succeeded': 0, 'last_error_reason': 1},
            {'cast_failed': 2, 'cast_succeeded': 1, 'last_error_reason': 0},
        ]
        reader, attempt = self._install(outcomes)
        probe = self._probe(reader, attempt)
        steps, state = client_facing.sweep_toward(probe)
        self.assertEqual(steps, 2)
        self.assertEqual(len(self.turns), 2)

    def test_gives_up_after_the_step_budget(self):
        outcomes = [
            {'cast_failed': 0, 'cast_succeeded': 0, 'last_error_reason': 0},
            {'cast_failed': 1, 'cast_succeeded': 0, 'last_error_reason': 1},
        ]
        reader, attempt = self._install(outcomes)
        probe = self._probe(reader, attempt)
        steps, state = client_facing.sweep_toward(probe, max_steps=5)
        self.assertEqual(steps, 5)

    def test_does_not_turn_when_the_first_cast_worked(self):
        outcomes = [
            {'cast_failed': 0, 'cast_succeeded': 0, 'last_error_reason': 0},
            {'cast_failed': 0, 'cast_succeeded': 1, 'last_error_reason': 0},
        ]
        reader, attempt = self._install(outcomes)
        probe = self._probe(reader, attempt)
        steps, state = client_facing.sweep_toward(probe)
        self.assertEqual(steps, 0)
        self.assertEqual(self.turns, [])

    def test_mana_failure_is_not_fixed_by_turning(self):
        outcomes = [
            {'cast_failed': 0, 'cast_succeeded': 0, 'last_error_reason': 0},
            {'cast_failed': 1, 'cast_succeeded': 0, 'last_error_reason': 2},
        ]
        reader, attempt = self._install(outcomes)
        probe = self._probe(reader, attempt)
        steps, state = client_facing.sweep_toward(probe, max_steps=5)
        self.assertEqual(steps, 0)

    def test_turn_direction_is_honoured(self):
        outcomes = [
            {'cast_failed': 0, 'cast_succeeded': 0, 'last_error_reason': 0},
            {'cast_failed': 1, 'cast_succeeded': 0, 'last_error_reason': 1},
            {'cast_failed': 1, 'cast_succeeded': 1, 'last_error_reason': 0},
        ]
        reader, attempt = self._install(outcomes)
        probe = self._probe(reader, attempt)
        client_facing.sweep_toward(probe, direction='right')
        self.assertEqual(self.turns, [client_facing.VK_RIGHT])


class CastOutcomeTest(unittest.TestCase):
    def test_success_is_detected_from_the_delta(self):
        before = {'cast_failed': 2, 'cast_succeeded': 1}
        after = {'cast_failed': 2, 'cast_succeeded': 2}
        self.assertEqual(client_facing.cast_outcome(after, before), 'success')

    def test_failure_is_detected_from_the_delta(self):
        before = {'cast_failed': 2, 'cast_succeeded': 1}
        after = {'cast_failed': 3, 'cast_succeeded': 1}
        self.assertEqual(client_facing.cast_outcome(after, before), 'failure')

    def test_no_change_is_unknown(self):
        before = {'cast_failed': 2, 'cast_succeeded': 1}
        after = {'cast_failed': 2, 'cast_succeeded': 1}
        self.assertEqual(client_facing.cast_outcome(after, before), 'unknown')


if __name__ == '__main__':
    unittest.main()
