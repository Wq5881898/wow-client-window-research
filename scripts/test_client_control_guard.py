import unittest
from client_control_guard import ControlGuard
from client_window_state import window_observable
from client_live_state import Freshness


def state(seq=1, **changes):
    result = dict(sequence=seq, game_ms=seq * 100, health=52, max_health=52,
                  dead=False, combat=False, target_exists=True, target_guid='wolf-a',
                  target_dead=False, target_health=3, target_attackable=True,
                  casting=False, spell_learned=True, spell_range=1)
    result.update(changes)
    return result


class GuardTests(unittest.TestCase):
    def test_replay_latches(self):
        guard = ControlGuard()
        guard.observe(state(10), 0)
        self.assertEqual(guard.observe(state(9), .1)['decision'], 'RECOVERY_REQUIRED')
        self.assertEqual(guard.observe(state(11), .2)['decision'], 'RECOVERY_REQUIRED')

    def test_new_frame_after_gap_not_accepted(self):
        tracker = Freshness()
        tracker.observe(state(), 0)
        with self.assertRaisesRegex(ValueError, 'stale'):
            tracker.observe(state(2), 1.1)
        with self.assertRaises(ValueError):
            tracker.observe(state(3), 1.2)

    def test_counter_wrap(self):
        tracker = Freshness()
        tracker.observe(dict(sequence=65535, game_ms=4294967290), 0)
        self.assertTrue(tracker.observe(dict(sequence=0, game_ms=90), .1))

    def test_low_health_identity_window_and_missing(self):
        for changes, reason in [({'health': 36}, 'low_health'),
                                ({'target_guid': 'wolf-b'}, 'target_identity_changed'),
                                ({'dead': True}, 'player_dead')]:
            guard = ControlGuard('wolf-a')
            self.assertEqual(guard.observe(state(**changes), 0)['reason'], reason)
        self.assertEqual(ControlGuard().observe(state(), 0, False)['reason'],
                         'window_not_visible')
        self.assertEqual(ControlGuard().unavailable()['decision'], 'RECOVERY_REQUIRED')

    def test_three_hp_is_not_success(self):
        guard = ControlGuard('wolf-a')
        guard.observe(state(), 0)
        self.assertEqual(guard.observe(state(2), .1)['decision'], 'ACTION_GATE_PENDING')
        self.assertEqual(guard.observe(state(3, target_dead=True, combat=True), .2)['decision'], 'WAIT')
        self.assertEqual(guard.observe(state(4, target_dead=True), .3)['decision'], 'VERIFY_SURVIVAL')

    def test_unknown_range_rejected(self):
        guard = ControlGuard('wolf-a')
        guard.observe(state(), 0)
        self.assertEqual(guard.observe(state(2, spell_range=2), .1)['decision'], 'RECOVERY_REQUIRED')


if __name__ == '__main__':
    unittest.main()
