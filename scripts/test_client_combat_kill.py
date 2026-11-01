"""Kill detection and recovery semantics of the combat controller."""
import unittest
from client_combat_controller import CombatController, KILL_HEALTH_THRESHOLD


def state(**changes):
    result = dict(sequence=1, game_ms=100, health=52, max_health=52, power=165,
                  combat=False, dead=False, target_exists=True,
                  target_guid='0xWOLF', target_dead=False, target_health=30,
                  target_attackable=True, casting=False, spell_learned=True,
                  spell_range=1, speed=0.0, pos_x=0.5, pos_y=0.5, facing=0.0,
                  events=[])
    result.update(changes)
    return result


def success(serial):
    return dict(serial=serial, kind=2, spell=133, at=1000 + serial, reason=0)


class KillDetectionTests(unittest.TestCase):
    def test_vanishing_target_after_lethal_hit_is_a_kill(self):
        controller = CombatController('0xWOLF', 133)
        controller.bind_target(state())
        controller.observe(state(events=[success(1)]), 0)
        controller.observe(state(sequence=2, game_ms=200, target_health=1), 0.2)
        decision = controller.observe(state(sequence=3, game_ms=300, target_exists=False), 0.4)
        self.assertEqual(decision['decision'], 'VERIFY_SURVIVAL')
        self.assertEqual(decision['reason'], 'target_gone_after_hit')
        self.assertTrue(controller.finished)

    def test_vanishing_target_without_a_hit_is_a_loss(self):
        controller = CombatController('0xWOLF', 133)
        controller.bind_target(state())
        decision = controller.observe(state(target_exists=False), 0)
        self.assertEqual(decision['decision'], 'RECOVER')
        self.assertEqual(decision['reason'], 'target_lost')

    def test_vanishing_target_after_any_hit_is_a_kill(self):
        controller = CombatController('0xWOLF', 133)
        controller.bind_target(state())
        controller.observe(state(events=[success(1)]), 0)
        decision = controller.observe(state(sequence=2, game_ms=200, target_exists=False), 0.2)
        self.assertEqual(decision['decision'], 'VERIFY_SURVIVAL')

    def test_threshold_is_the_documented_value(self):
        self.assertEqual(KILL_HEALTH_THRESHOLD, 5)


if __name__ == '__main__':
    unittest.main()
