"""Decision checks for the combat-period control state machine."""
import unittest
from client_combat_controller import (
    CombatController, RETRYABLE_REASONS, REASON_MANA, REASON_COOLDOWN,
    REASON_FACING, REASON_INVALID_TARGET, REASON_LINE_OF_SIGHT, REASON_RANGE)


def state(**changes):
    result = dict(sequence=1, game_ms=100, health=52, max_health=52, power=165,
                  combat=False, dead=False, target_exists=True,
                  target_guid='0xF130000337000A31', target_dead=False,
                  target_health=30, target_attackable=True, casting=False,
                  spell_learned=True, spell_range=1, speed=0.0,
                  pos_x=0.5, pos_y=0.5, facing=0.0, events=[])
    result.update(changes)
    return result


def event(serial, kind, spell=133, reason=0):
    return dict(serial=serial, kind=kind, spell=spell, at=1000 + serial, reason=reason)


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


class CombatControllerTests(unittest.TestCase):
    def test_binding_requires_matching_target(self):
        controller = CombatController('0xF130000337000A31', 133)
        self.assertEqual(controller.bind_target(state())['decision'], 'BOUND')
        for changes, reason in [({'target_exists': False}, 'no_target'),
                                ({'target_guid': '0xOTHER'}, 'target_identity_mismatch'),
                                ({'target_attackable': False}, 'target_not_attackable'),
                                ({'target_dead': True}, 'target_already_dead')]:
            controller = CombatController('0xF130000337000A31', 133)
            self.assertEqual(controller.bind_target(state(**changes))['reason'], reason)

    def test_cast_allowed_only_when_ready(self):
        driver = Driver()
        driver.controller.bind_target(state())
        decision = driver.warm()
        self.assertEqual(decision['decision'], 'CAST_ALLOWED')
        self.assertEqual(decision['attempt'], 1)

    def test_out_of_range_closes_distance(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        self.assertEqual(driver.frame(spell_range=0)['decision'], 'CLOSE_DISTANCE')

    def test_unknown_range_recovers(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        decision = driver.frame(spell_range=2)
        self.assertEqual(decision['decision'], 'RECOVER')
        self.assertEqual(decision['reason'], 'spell_range_unknown')

    def test_low_health_and_death_recover(self):
        for changes, reason in [({'health': 36}, 'low_health'),
                                ({'dead': True}, 'player_dead')]:
            driver = Driver()
            driver.controller.bind_target(state())
            driver.warm()
            decision = driver.frame(**changes)
            self.assertEqual(decision['decision'], 'RECOVER')
            self.assertEqual(decision['reason'], reason)

    def test_target_change_recovers(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        decision = driver.frame(target_guid='0xOTHER')
        self.assertEqual(decision['decision'], 'RECOVER')
        self.assertEqual(decision['reason'], 'target_identity_changed')

    def test_target_dead_requires_survival_check(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        decision = driver.frame(target_dead=True)
        self.assertEqual(decision['decision'], 'VERIFY_SURVIVAL')
        self.assertTrue(driver.controller.finished)

    def test_three_health_target_is_still_castable(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        self.assertEqual(driver.frame(target_health=3)['decision'], 'CAST_ALLOWED')

    def test_mana_and_cooldown_failures_wait(self):
        for reason in (REASON_MANA, REASON_COOLDOWN):
            driver = Driver()
            driver.controller.bind_target(state())
            driver.warm()
            decision = driver.frame(events=[event(1, 3, reason=reason)])
            self.assertEqual(decision['decision'], 'WAIT')

    def test_range_and_facing_failures_close_distance(self):
        for reason in (REASON_RANGE, REASON_FACING, REASON_LINE_OF_SIGHT):
            driver = Driver()
            driver.controller.bind_target(state())
            driver.warm()
            decision = driver.frame(events=[event(1, 3, reason=reason)])
            self.assertEqual(decision['decision'], 'CLOSE_DISTANCE')
            self.assertIn(reason, RETRYABLE_REASONS)

    def test_invalid_target_failure_recovers(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        decision = driver.frame(events=[event(1, 3, reason=REASON_INVALID_TARGET)])
        self.assertEqual(decision['decision'], 'RECOVER')

    def test_failed_event_is_not_replayed(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        driver.frame(events=[event(1, 3, reason=REASON_RANGE)])
        # The same event must not trigger the branch a second time.
        decision = driver.frame(events=[event(1, 3, reason=REASON_RANGE)])
        self.assertEqual(decision['decision'], 'CAST_ALLOWED')

    def test_attempt_budget_exhausts(self):
        driver = Driver(CombatController('0xF130000337000A31', 133, max_attempts=2))
        driver.controller.bind_target(state())
        driver.warm()
        for _ in range(2):
            driver.controller.record_attempt()
        decision = driver.frame()
        self.assertEqual(decision['decision'], 'RECOVER')
        self.assertEqual(decision['reason'], 'attempt_budget_exhausted')

    def test_recovery_is_sticky(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        driver.frame(health=10)
        self.assertEqual(driver.frame()['decision'], 'RECOVER')

    def test_window_hidden_recovers(self):
        driver = Driver()
        driver.controller.bind_target(state())
        driver.warm()
        decision = driver.controller.observe(state(), driver.now, window_visible=False)
        self.assertEqual(decision['decision'], 'RECOVER')
        self.assertEqual(decision['reason'], 'window_not_visible')


if __name__ == '__main__':
    unittest.main()
