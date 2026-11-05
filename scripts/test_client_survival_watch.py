"""The quiet time of the character after a fight.

The observation used to be counted in total, so a fight that ended in the
last second of the thirty seconds still passed. The time has to be
continuous: a character that is in combat, that moves, that dies or that
is no longer observed breaks it.
"""
import unittest

from client_survival_watch import (SurvivalWatch, BROKEN_COMBAT,
                                    BROKEN_DEAD, BROKEN_IDENTITY,
                                    BROKEN_MOVING, BROKEN_STALE)


def state(**overrides):
    result = dict(sequence=1, game_ms=100, dead=False, combat=False,
                  speed=0.0, player_guid='0x0000000000000008')
    result.update(overrides)
    return result


class SurvivalWatchTests(unittest.TestCase):
    def test_a_quiet_character_passes_after_the_time(self):
        watch = SurvivalWatch(required=10.0)
        now = 0.0
        for _ in range(11):
            watch.observe(state(sequence=watch.samples + 1), now)
            now += 1.0
        self.assertTrue(watch.passed)
        self.assertEqual(watch.quiet, 10.0)

    def test_a_fight_that_ends_at_the_last_moment_does_not_pass(self):
        watch = SurvivalWatch(required=10.0)
        now = 0.0
        for _ in range(9):
            watch.observe(state(sequence=watch.samples + 1), now)
            now += 1.0
        # The fight is still going on, so the time starts again.
        watch.observe(state(sequence=watch.samples + 1, combat=True), now)
        now += 1.0
        watch.observe(state(sequence=watch.samples + 1), now)
        now += 1.0
        self.assertFalse(watch.passed)
        self.assertEqual(watch.quiet, 1.0)
        self.assertIn(BROKEN_COMBAT, watch.breaks)

    def test_moving_breaks_the_quiet_time(self):
        watch = SurvivalWatch(required=10.0)
        watch.observe(state(sequence=1), 0.0)
        reason = watch.observe(state(sequence=2, speed=3.0), 1.0)
        self.assertEqual(reason, BROKEN_MOVING)
        self.assertEqual(watch.quiet, 0.0)

    def test_a_dead_character_breaks_the_quiet_time(self):
        watch = SurvivalWatch(required=10.0)
        watch.observe(state(sequence=1), 0.0)
        reason = watch.observe(state(sequence=2, dead=True), 1.0)
        self.assertEqual(reason, BROKEN_DEAD)

    def test_another_character_breaks_the_quiet_time(self):
        watch = SurvivalWatch(required=10.0, player_guid='0x0000000000000008')
        watch.observe(state(sequence=1), 0.0)
        reason = watch.observe(state(sequence=2, player_guid='0x0000000000000009'),
                               1.0)
        self.assertEqual(reason, BROKEN_IDENTITY)

    def test_a_picture_that_repeats_itself_is_not_an_observation(self):
        watch = SurvivalWatch(required=10.0)
        watch.observe(state(sequence=7), 0.0)
        reason = watch.observe(state(sequence=7), 1.0)
        self.assertEqual(reason, BROKEN_STALE)
        self.assertEqual(watch.quiet, 0.0)

    def test_the_summary_names_the_breaks(self):
        watch = SurvivalWatch(required=30.0)
        watch.observe(state(sequence=1), 0.0)
        watch.observe(state(sequence=2, combat=True), 1.0)
        summary = watch.summary()
        self.assertEqual(summary['required'], 30.0)
        self.assertEqual(summary['resets'], 1)
        self.assertEqual(summary['breaks'], [BROKEN_COMBAT])

    def test_the_time_is_grown_by_the_gap_between_two_readings(self):
        watch = SurvivalWatch(required=2.0)
        watch.observe(state(sequence=1), 0.0)
        watch.observe(state(sequence=2), 2.5)
        self.assertEqual(watch.quiet, 2.5)


if __name__ == '__main__':
    unittest.main()
