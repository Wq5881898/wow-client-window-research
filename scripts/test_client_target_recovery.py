"""The controller must notice a target that recovered its health."""
import unittest
from client_combat_controller import CombatController


def state(**changes):
    result = dict(sequence=1, game_ms=100, health=52, max_health=52, power=165,
                  combat=False, dead=False, target_exists=True,
                  target_guid='0xF130000337000A31', target_dead=False,
                  target_health=30, target_attackable=True, casting=False,
                  spell_learned=True, spell_range=1, speed=0.0,
                  pos_x=0.5, pos_y=0.5, facing=0.0, events=[],
                  last_error_reason=0)
    result.update(changes)
    return result


class Driver:
    """Feeds the controller advancing frames so the heartbeat stays live."""

    def __init__(self, controller=None, target='0xF130000337000A31'):
        self.controller = controller or CombatController(target, 133)
        self.now = 0.0
        self.tick = 0

    def frame(self, **changes):
        self.tick += 1
        self.now += 0.2
        changes.setdefault('sequence', self.tick)
        changes.setdefault('game_ms', 100 * self.tick)
        return self.controller.observe(state(**changes), self.now)

    def warm(self):
        self.frame()
        return self.frame()


class TargetRecoveryTest(unittest.TestCase):
    def test_a_rising_health_is_noticed(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        driver.frame(target_health=30)
        driver.frame(target_health=45)
        self.assertEqual(driver.controller.recoveries, 1)

    def test_the_attempt_budget_restarts_after_a_recovery(self):
        controller = CombatController('0xF130000337000A31', 133, max_attempts=4)
        driver = Driver(controller)
        controller.bind_target(state())
        driver.warm()
        # Spend three of the four attempts.
        for _ in range(3):
            controller.record_attempt()
        # The target recovers its health, which gives the fight a new chance
        # instead of running out of attempts.
        driver.frame(target_health=30)
        decision = driver.frame(target_health=45)
        self.assertEqual(decision['decision'], 'CAST_ALLOWED')
        self.assertEqual(decision['reason'], 'target_recovered')
        self.assertEqual(controller.attempts, 0)

    def test_a_recovery_is_noticed_even_with_a_spent_budget(self):
        controller = CombatController('0xF130000337000A31', 133, max_attempts=4)
        driver = Driver(controller)
        controller.bind_target(state())
        driver.warm()
        for _ in range(3):
            controller.record_attempt()
        controller.record_attempt()
        # The rise is seen before the budget is checked, so the run continues.
        driver.frame(target_health=45)
        self.assertFalse(controller.finished)
        self.assertEqual(controller.recoveries, 1)

    def test_a_falling_health_is_not_a_recovery(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        # The baseline of the binding is the health of the default state, so
        # the first observation has to stay below it.
        driver.frame(target_health=25)
        driver.frame(target_health=25)
        self.assertEqual(driver.controller.recoveries, 0)

    def test_a_steady_health_is_not_a_recovery(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        # The health rises once against the baseline of the binding, then it
        # stays on that level, which is not a recovery any more.
        driver.frame(target_health=40)
        driver.frame(target_health=40)
        self.assertEqual(driver.controller.recoveries, 1)
        driver.frame(target_health=40)
        self.assertEqual(driver.controller.recoveries, 1)

if __name__ == '__main__':
    unittest.main()
