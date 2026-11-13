"""The controller must give up on a target that takes no damage.

The small-drop heuristic was removed on 2026-11-10: a partial hit or a
projectile that is sampled in flight is progress, not evidence of resistance.
The fight stays bounded by the attempt budget instead, and these tests keep
that bound honest.
"""
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
    def test_a_target_that_takes_no_damage_is_abandoned_by_the_budget(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        decisions = []
        for _ in range(driver.controller.max_attempts):
            driver.controller.record_attempt(120)
            decisions.append(driver.frame(target_health=120))
        self.assertEqual(decisions[-1]['decision'], 'RECOVER')
        self.assertEqual(decisions[-1]['reason'], 'attempt_budget_exhausted')
        for decision in decisions[:-1]:
            self.assertEqual(decision['decision'], 'CAST_ALLOWED')

    def test_a_normal_drop_keeps_the_fight_going(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        driver.controller.record_attempt(120)
        decision = driver.frame(target_health=120 - MIN_TARGET_PROGRESS)
        self.assertEqual(decision['decision'], 'CAST_ALLOWED')

    def test_a_small_drop_is_not_read_as_resistance(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        driver.controller.record_attempt(120)
        decision = driver.frame(target_health=120 - MIN_TARGET_PROGRESS + 1)
        self.assertNotEqual(decision.get('reason'), 'target_resists')
        self.assertEqual(decision['decision'], 'CAST_ALLOWED')

    def test_a_quiet_frame_between_casts_is_not_a_recovery(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        driver.controller.record_attempt(120)
        decision = driver.frame(target_health=120)
        self.assertNotEqual(decision.get('reason'), 'target_resists')
        self.assertEqual(decision['decision'], 'CAST_ALLOWED')

    def test_the_first_observation_is_not_a_recovery(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        decision = driver.frame(target_health=120)
        self.assertNotEqual(decision.get('reason'), 'target_resists')
        self.assertEqual(decision['decision'], 'CAST_ALLOWED')


if __name__ == '__main__':
    unittest.main()
