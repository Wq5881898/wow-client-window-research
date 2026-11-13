"""The cast decision of the fight loop."""
import unittest

from client_cast_step import (FINE_TURN_SECONDS, QUARTER_TURNS,
                              QUARTER_TURN_SECONDS, REASON_FACING,
                              REASON_LINE_OF_SIGHT, REASON_MANA,
                              REASON_NO_TARGET, REASON_NOT_READY,
                              REASON_RANGE, decide)


def state(**changes):
    result = dict(last_error_reason=0, health=172, max_health=172, power=378,
                  target_health=120, spell_range=1, target_exists=True,
                  target_dead=False, dead=False)
    result.update(changes)
    return result


class CastStepTests(unittest.TestCase):
    def test_a_facing_error_is_answered_by_a_quarter_turn(self):
        action = decide(state(last_error_reason=REASON_FACING))
        self.assertEqual(action['action'], 'turn')
        self.assertEqual(action['seconds'], QUARTER_TURN_SECONDS)
        self.assertEqual(action['count'], 'quarter')

    def test_three_quarter_turns_are_allowed_before_the_fine_step(self):
        for used in range(QUARTER_TURNS):
            action = decide(state(last_error_reason=REASON_FACING),
                            quarter_turns=used)
            self.assertEqual(action['reason'], 'facing_quarter_turn')
        action = decide(state(last_error_reason=REASON_FACING),
                        quarter_turns=QUARTER_TURNS)
        self.assertEqual(action['reason'], 'facing_fine_turn')
        self.assertEqual(action['seconds'], FINE_TURN_SECONDS)

    def test_a_target_that_cannot_be_faced_ends_the_fight(self):
        action = decide(state(last_error_reason=REASON_FACING),
                        quarter_turns=QUARTER_TURNS, fine_turns=99)
        self.assertEqual(action['action'], 'retreat')
        self.assertEqual(action['reason'], 'facing_not_found')

    def test_an_out_of_range_target_is_approached_not_turned(self):
        action = decide(state(last_error_reason=REASON_RANGE))
        self.assertEqual(action['action'], 'approach')
        action = decide(state(spell_range=0))
        self.assertEqual(action['action'], 'approach')

    def test_low_health_leaves_the_fight_unless_the_target_is_almost_dead(self):
        action = decide(state(health=98, target_health=120))
        self.assertEqual(action['action'], 'retreat')
        self.assertEqual(action['reason'], 'health_recovery_threshold')
        action = decide(state(health=98, target_health=40))
        self.assertEqual(action['action'], 'cast')

    def test_the_other_reasons_have_their_own_answer(self):
        self.assertEqual(decide(state(last_error_reason=REASON_MANA))['action'],
                         'rest')
        self.assertEqual(decide(state(last_error_reason=REASON_NOT_READY))['action'],
                         'wait')
        self.assertEqual(decide(state(last_error_reason=REASON_NO_TARGET))['action'],
                         'verify')
        self.assertEqual(
            decide(state(last_error_reason=REASON_LINE_OF_SIGHT))['action'], 'turn')

    def test_a_frame_without_an_error_means_cast(self):
        self.assertEqual(decide(state())['action'], 'cast')

    def test_a_gone_target_is_verified_not_fought(self):
        self.assertEqual(decide(state(target_exists=False))['action'], 'verify')
        self.assertEqual(decide(state(target_dead=True))['action'], 'verify')
        self.assertEqual(decide(state(dead=True))['action'], 'retreat')


if __name__ == '__main__':
    unittest.main()
