"""The guard that stops an action of the driver.

The guard used to be a check whose result was thrown away, so a cast that
had to be stopped went on. The reason has to be latched as well: a later
check must not quietly continue the fight after the character was found in
danger.
"""
import unittest

from client_action_guard import (ActionCancelled, ActionGuard, STOP_DEAD,
                                 STOP_IDENTITY, STOP_LOW_HEALTH)


def state(**overrides):
    result = dict(dead=False, health=52, max_health=52,
                  target_exists=True, target_guid='0xABC')
    result.update(overrides)
    return result


class ActionGuardTests(unittest.TestCase):
    def test_a_healthy_character_may_act(self):
        guard = ActionGuard()
        self.assertIsNone(guard.check_state(state(), 0.7, '0xABC'))
        self.assertFalse(guard.cancelled)

    def test_a_low_health_stops_the_action(self):
        guard = ActionGuard()
        reason = guard.check_state(state(health=30), 0.7, '0xABC')
        self.assertEqual(reason, STOP_LOW_HEALTH)
        self.assertTrue(guard.cancelled)

    def test_a_dead_character_stops_the_action_before_the_health(self):
        guard = ActionGuard()
        reason = guard.check_state(state(dead=True, health=0), 0.7, '0xABC')
        self.assertEqual(reason, STOP_DEAD)

    def test_another_creature_stops_the_action(self):
        guard = ActionGuard()
        reason = guard.check_state(state(target_guid='0xOTHER'), 0.7, '0xABC')
        self.assertEqual(reason, STOP_IDENTITY)

    def test_a_target_that_is_gone_is_not_a_change_of_identity(self):
        guard = ActionGuard()
        self.assertIsNone(guard.check_state(state(target_exists=False),
                                            0.7, '0xABC'))

    def test_the_first_reason_is_the_one_that_is_kept(self):
        guard = ActionGuard()
        guard.cancel(STOP_LOW_HEALTH)
        guard.cancel(STOP_DEAD)
        self.assertEqual(guard.reason, STOP_LOW_HEALTH)

    def test_a_latched_reason_survives_a_healthy_reading(self):
        guard = ActionGuard()
        guard.cancel(STOP_DEAD)
        self.assertEqual(guard.check_state(state(), 0.7, '0xABC'), STOP_DEAD)

    def test_the_guard_can_be_cleared_by_the_run(self):
        guard = ActionGuard()
        guard.cancel(STOP_DEAD)
        guard.clear()
        self.assertFalse(guard.cancelled)
        self.assertIsNone(guard.check_state(state(), 0.7, '0xABC'))

    def test_the_exception_carries_the_reason(self):
        error = ActionCancelled(STOP_LOW_HEALTH)
        self.assertEqual(error.reason, STOP_LOW_HEALTH)


if __name__ == '__main__':
    unittest.main()
