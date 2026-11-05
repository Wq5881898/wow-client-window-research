"""Kill detection and recovery semantics of the combat controller.

The rules that are checked here are the ones the knowledge base asks for:
a vanished target is only a kill when the death of the bound creature was
seen, the events of an earlier fight do not count as hits of this one, and
the number of hits is a number and not the serial of an event.
"""
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
    def test_a_vanishing_target_without_a_hit_is_a_loss(self):
        controller = CombatController('0xWOLF', 133)
        controller.bind_target(state())
        decision = controller.observe(state(target_exists=False), 0)
        self.assertEqual(decision['decision'], 'RECOVER')
        self.assertEqual(decision['reason'], 'target_lost')

    def test_a_success_without_a_drop_is_not_a_kill(self):
        # The first counterexample of the knowledge base: the target is
        # bound with 120 health, a success event arrives and the target
        # disappears without losing health. The client counts casts that did
        # not reach the creature as a success, so this is not a kill.
        controller = CombatController('0xWOLF', 133)
        controller.bind_target(state(target_health=120, event_serial=10))
        controller.observe(state(target_health=120, events=[success(11)]), 0)
        decision = controller.observe(state(sequence=2, game_ms=200,
                                           target_exists=False), 0.2)
        self.assertEqual(decision['decision'], 'VERIFY_SURVIVAL')
        self.assertEqual(decision['reason'], 'target_gone_unconfirmed')
        self.assertFalse(decision.get('kill_confirmed'))

    def test_a_vanishing_target_with_a_few_health_left_is_not_a_kill(self):
        # The second counterexample of the knowledge base: one to five
        # health left is a hint, not the proof that the creature died. It
        # may simply have walked out of sight.
        controller = CombatController('0xWOLF', 133)
        controller.bind_target(state(target_health=5, event_serial=10))
        controller.observe(state(target_health=5, events=[success(11)]), 0)
        decision = controller.observe(state(sequence=2, game_ms=200,
                                           target_exists=False), 0.2)
        self.assertEqual(decision['decision'], 'VERIFY_SURVIVAL')
        self.assertEqual(decision['reason'], 'target_gone_unconfirmed')
        self.assertFalse(decision.get('kill_confirmed'))
        # The low health is reported as a hint, not as the proof.
        self.assertTrue(decision.get('low_health_hint'))

    def test_a_vanishing_target_after_lethal_hit_is_not_a_kill(self):
        # One health left is still not a death that was seen.
        controller = CombatController('0xWOLF', 133)
        controller.bind_target(state())
        controller.observe(state(events=[success(1)]), 0)
        controller.observe(state(sequence=2, game_ms=200, target_health=1), 0.2)
        decision = controller.observe(state(sequence=3, game_ms=300,
                                           target_exists=False), 0.4)
        self.assertEqual(decision['decision'], 'VERIFY_SURVIVAL')
        self.assertEqual(decision['reason'], 'target_gone_unconfirmed')
        self.assertFalse(decision.get('kill_confirmed'))

    def test_a_seen_death_of_the_same_creature_is_a_kill(self):
        controller = CombatController('0xWOLF', 133)
        controller.bind_target(state(target_health=120, event_serial=10))
        controller.observe(state(target_health=120, events=[success(11)]), 0)
        # The creature is seen dead while it is still selected.
        decision = controller.observe(state(target_health=0, target_dead=True),
                                     0.2)
        self.assertEqual(decision['decision'], 'VERIFY_SURVIVAL')
        self.assertIn(decision['reason'], ('target_dead',
                                           'target_dead_out_of_combat'))
        # And it vanishes right afterwards: that is still a kill.
        decision = controller.observe(state(sequence=3, game_ms=300,
                                           target_exists=False), 0.4)
        self.assertEqual(decision['decision'], 'DONE')
        self.assertTrue(controller.last_target_dead)

    def test_the_events_of_an_earlier_fight_are_not_hits(self):
        # The event with the serial 5 is older than the line of the
        # binding, so it belongs to an earlier fight and does not count.
        controller = CombatController('0xWOLF', 133)
        controller.bind_target(state(target_health=120, event_serial=10))
        controller.observe(state(target_health=120, events=[success(5)]), 0)
        self.assertEqual(controller.successful_casts, 0)
        decision = controller.observe(state(sequence=2, game_ms=200,
                                           target_exists=False), 0.2)
        self.assertEqual(decision['decision'], 'RECOVER')
        self.assertEqual(decision['reason'], 'target_lost')

    def test_the_hits_are_counted_and_not_the_serial(self):
        controller = CombatController('0xWOLF', 133)
        controller.bind_target(state(event_serial=10))
        controller.observe(state(events=[success(11)]), 0)
        controller.observe(state(sequence=2, game_ms=200,
                                 events=[success(11), success(12)]), 0.2)
        self.assertEqual(controller.successful_casts, 2)

    def test_a_cast_that_is_reported_twice_counts_once(self):
        controller = CombatController('0xWOLF', 133)
        controller.bind_target(state(event_serial=10))
        controller.observe(state(events=[success(11)]), 0)
        controller.observe(state(sequence=2, game_ms=200,
                                 events=[success(11)]), 0.2)
        self.assertEqual(controller.successful_casts, 1)

    def test_the_threshold_is_the_documented_value(self):
        self.assertEqual(KILL_HEALTH_THRESHOLD, 5)


if __name__ == '__main__':
    unittest.main()
