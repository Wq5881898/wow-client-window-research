"""The controller must give up on a target that takes no damage."""
import unittest
from client_combat_controller import CombatController, MIN_TARGET_PROGRESS


def state(**changes):
    result = dict(sequence=1, game_ms=100, health=52, max_health=52, power=165,
                  combat=False, dead=False, target_exists=True,
                  target_guid='0xF130000337000A31', target_dead=False,
                  target_health=120, target_attackable=True, casting=False,
                  spell_learned=True, spell_range=1, speed=0.0,
                  pos_x=0.5, pos_y=0.5, facing=0.0, events=[],
                  last_error_reason=0)
    result.update(changes)
    return result


class Driver:
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


class InsufficientProgressTest(unittest.TestCase):
    def test_a_target_that_takes_no_damage_is_abandoned(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        # A cast is issued at a target with 120 health.
        driver.controller.record_attempt(120)
        # The health drops by one point only, which is below the progress
        # that a spell of this level can achieve.
        decision = driver.frame(target_health=120 - MIN_TARGET_PROGRESS + 1)
        self.assertEqual(decision['decision'], 'RECOVER')
        self.assertEqual(decision['reason'], 'target_resists')

    def test_a_normal_drop_keeps_the_fight_going(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        driver.controller.record_attempt(120)
        decision = driver.frame(target_health=120 - MIN_TARGET_PROGRESS)
        self.assertNotEqual(decision.get('reason'), 'target_resists')

    def test_a_quiet_frame_between_casts_is_not_a_recovery(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        driver.controller.record_attempt(120)
        # The cast has not resolved yet, so the health did not change.
        decision = driver.frame(target_health=120)
        self.assertNotEqual(decision.get('reason'), 'target_resists')

    def test_the_first_observation_is_not_a_recovery(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        decision = driver.frame(target_health=120)
        self.assertNotEqual(decision.get('reason'), 'target_resists')


if __name__ == '__main__':
    unittest.main()
