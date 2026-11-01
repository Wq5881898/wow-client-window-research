"""Decision checks for the bounded movement primitive."""
import unittest
from client_control_guard import ControlGuard
from client_window_state import window_observable
import lab_client_move as move


def state(**changes):
    result = dict(sequence=1, game_ms=100, health=52, max_health=52, power=165,
                  combat=False, dead=False, target_exists=False,
                  target_guid='0x0000000000000000', target_dead=False,
                  target_health=0, target_attackable=False, casting=False,
                  spell_learned=True, spell_range=1, speed=0.0,
                  pos_x=0.5, pos_y=0.5, facing=3.0)
    result.update(changes)
    return result


class MoveTests(unittest.TestCase):
    def test_displacement_and_facing(self):
        before = state()
        after = state(pos_x=0.5005, pos_y=0.4998, facing=3.05)
        self.assertGreater(move.displacement(before, after), 1e-6)
        self.assertLess(move.displacement(before, state()), 1e-6)
        self.assertAlmostEqual(move.facing_delta(before, after), 0.05, places=6)

    def test_facing_wrap(self):
        before = state(facing=0.05)
        after = state(facing=6.2)
        self.assertLess(move.facing_delta(before, after), 0.2)

    def test_guard_rejects_unsafe_baselines(self):
        # The guard rejects combat and death; a stray target is the driver's concern.
        for changes in [{'combat': True}, {'dead': True}]:
            guard = ControlGuard()
            decision = guard.observe(state(**changes), 0)
            self.assertEqual(decision['decision'], 'RECOVERY_REQUIRED')
        self.assertEqual(ControlGuard().observe(state(target_exists=True), 0)['decision'],
                         'WAIT')

    def test_guard_accepts_idle_noncombat(self):
        guard = ControlGuard()
        decision = guard.observe(state(), 0)
        self.assertNotEqual(decision['decision'], 'RECOVERY_REQUIRED')


if __name__ == '__main__':
    unittest.main()
