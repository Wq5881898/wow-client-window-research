"""Unit checks for the combat loop helper functions."""
import unittest
from client_combat_controller import CombatController
import lab_client_combat_loop as loop


class CombatLoopTests(unittest.TestCase):
    def test_hold_duration_is_bounded(self):
        with self.assertRaises(ValueError):
            loop.hold(loop.VK_BACK, 0)
        with self.assertRaises(ValueError):
            loop.hold(loop.VK_BACK, 2.5)

    def test_target_binding_requires_hostile(self):
        controller = CombatController('0xABC', loop.FIREBALL)
        self.assertEqual(controller.bind_target(
            dict(target_exists=True, target_guid='0xABC', target_attackable=False,
                 target_dead=False, target_health=10))['reason'], 'target_not_attackable')
        self.assertEqual(controller.bind_target(
            dict(target_exists=True, target_guid='0xOTHER', target_attackable=True,
                 target_dead=False, target_health=10))['reason'],
            'target_identity_mismatch')

    def test_distinct_movement_keys(self):
        self.assertNotEqual(loop.VK_FORWARD, loop.VK_BACK)
        self.assertEqual(loop.FIREBALL, 133)

    def test_loop_is_bounded(self):
        controller = CombatController('0xABC', loop.FIREBALL)
        self.assertEqual(controller.max_attempts, 4)
        self.assertEqual(controller.target_guid, '0xABC')


if __name__ == '__main__':
    unittest.main()
