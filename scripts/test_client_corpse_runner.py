"""Decisions of the corpse running task."""
import math
import unittest
from client_corpse_runner import (CorpseRunner, bearing_to, corpse_distance,
                                  wrap, CORPSE_RANGE)

# The character stands in the graveyard of the valley.
PLAYER_X = 0.4933
PLAYER_Y = 0.4223
FAR = 0.02          # clearly out of reach
NEAR = CORPSE_RANGE * 0.5


def state(corpse_dx=0.0, corpse_dy=FAR, **changes):
    """The character in the world with a corpse at the given offset.

    The map x grows to the east and the map y to the south.
    """
    result = dict(sequence=1, game_ms=100, health=1, max_health=52, power=0,
                  combat=False, dead=True, target_exists=False,
                  target_guid='0x0', target_dead=False, target_health=0,
                  target_attackable=False, spell_range=2, spell_learned=True,
                  casting=False, speed=0.0, pos_x=PLAYER_X, pos_y=PLAYER_Y,
                  facing=0.0, corpse_x=PLAYER_X + corpse_dx,
                  corpse_y=PLAYER_Y + corpse_dy, corpse_exists=True, events=[])
    result.update(changes)
    return result


class BearingTest(unittest.TestCase):
    """The heading towards a target follows the measured conventions.

    The map x grows to the east and the map y to the south, the heading
    grows counter clockwise from the north and walking at the heading h
    moves the position by (-sin h, -cos h).
    """

    def test_a_corpse_to_the_south_is_a_half_turn(self):
        self.assertAlmostEqual(bearing_to(state(corpse_dy=FAR)), math.pi)

    def test_a_corpse_to_the_north_is_the_north(self):
        self.assertAlmostEqual(bearing_to(state(corpse_dy=-FAR)), 0.0)

    def test_a_corpse_to_the_east_is_a_quarter_turn_to_the_right(self):
        self.assertAlmostEqual(bearing_to(state(corpse_dx=FAR, corpse_dy=0)),
                               -math.pi / 2)

    def test_a_corpse_to_the_west_is_a_quarter_turn_to_the_left(self):
        self.assertAlmostEqual(bearing_to(state(corpse_dx=-FAR, corpse_dy=0)),
                               math.pi / 2)

    def test_the_distance_is_measured(self):
        self.assertAlmostEqual(corpse_distance(state(corpse_dy=0.0035)), 0.0035)

    def test_wrap_brings_an_angle_into_range(self):
        self.assertAlmostEqual(wrap(3 * math.pi), math.pi)
        self.assertAlmostEqual(wrap(-3 * math.pi), -math.pi)


class CorpseRunnerTest(unittest.TestCase):
    def test_a_living_character_ends_the_run(self):
        runner = CorpseRunner()
        action = runner.observe(state(dead=False, health=52), 0.0)
        self.assertEqual(action['action'], 'DONE')
        self.assertEqual(runner.phase, 'DONE')

    def test_a_missing_corpse_gives_up(self):
        runner = CorpseRunner()
        action = runner.observe(state(corpse_exists=False), 0.0)
        self.assertEqual(action['action'], 'GIVE_UP')
        self.assertEqual(action['reason'], 'no_corpse')

    def test_a_far_corpse_in_front_makes_the_character_walk(self):
        runner = CorpseRunner()
        action = runner.observe(state(corpse_dy=-FAR, facing=0.0), 0.0)
        self.assertEqual(action['action'], 'WALK')

    def test_a_corpse_to_the_south_makes_the_character_turn_left(self):
        runner = CorpseRunner()
        action = runner.observe(state(corpse_dy=FAR, facing=0.0), 0.0)
        self.assertEqual(action['action'], 'TURN')
        self.assertEqual(action['direction'], 'left')

    def test_a_corpse_to_the_east_makes_the_character_turn_right(self):
        runner = CorpseRunner()
        action = runner.observe(state(corpse_dx=FAR, corpse_dy=0, facing=0.0), 0.0)
        self.assertEqual(action['action'], 'TURN')
        self.assertEqual(action['direction'], 'right')

    def test_a_corpse_to_the_west_makes_the_character_turn_left(self):
        runner = CorpseRunner()
        action = runner.observe(state(corpse_dx=-FAR, corpse_dy=0, facing=0.0), 0.0)
        self.assertEqual(action['action'], 'TURN')
        self.assertEqual(action['direction'], 'left')

    def test_a_turned_character_walks_towards_the_corpse(self):
        runner = CorpseRunner()
        action = runner.observe(state(corpse_dx=FAR, corpse_dy=0,
                                      facing=-math.pi / 2), 0.0)
        self.assertEqual(action['action'], 'WALK')

    def test_a_corpse_in_reach_is_accepted(self):
        runner = CorpseRunner()
        action = runner.observe(state(corpse_dy=NEAR, facing=0.0), 0.0)
        self.assertEqual(action['action'], 'ACCEPT')
        self.assertEqual(action['point'], (960, 230))

    def test_the_accept_button_is_tried_a_few_times(self):
        runner = CorpseRunner()
        for _ in range(6):
            action = runner.observe(state(corpse_dy=NEAR, facing=0.0), 0.0)
        self.assertEqual(action['action'], 'ACCEPT')
        action = runner.observe(state(corpse_dy=NEAR, facing=0.0), 0.0)
        self.assertEqual(action['action'], 'GIVE_UP')
        self.assertEqual(action['reason'], 'dialog_not_accepted')

    def test_the_run_gives_up_after_the_budget(self):
        runner = CorpseRunner(time_budget=10.0)
        action = runner.observe(state(corpse_dy=-FAR, facing=0.0), 0.0)
        self.assertEqual(action['action'], 'WALK')
        action = runner.observe(state(corpse_dy=-FAR, facing=0.0), 20.0)
        self.assertEqual(action['action'], 'GIVE_UP')
        self.assertEqual(action['reason'], 'time_budget')

    def test_the_distance_gate_uses_the_map_range(self):
        runner = CorpseRunner()
        close = state(corpse_dy=CORPSE_RANGE * 0.5)
        far = state(corpse_dy=CORPSE_RANGE * 4, facing=math.pi)
        self.assertEqual(runner.observe(close, 0.0)['action'], 'ACCEPT')
        self.assertEqual(runner.observe(far, 0.1)['action'], 'WALK')

    def test_a_walk_that_does_not_help_leaves_the_direct_line(self):
        runner = CorpseRunner()
        # The character walks but the corpse does not get closer.
        runner.observe(state(corpse_dy=-FAR, facing=0.0), 0.0)
        action = runner.observe(state(corpse_dy=-FAR, facing=0.0), 1.0)
        self.assertEqual(action['action'], 'TURN')
        self.assertNotEqual(runner.avoid, 0.0)
        self.assertEqual(runner.stuck, 1)

    def test_a_walk_that_helps_keeps_the_direct_line(self):
        runner = CorpseRunner()
        runner.observe(state(corpse_dy=-FAR, facing=0.0), 0.0)
        closer = state(corpse_dy=-FAR + 0.005, facing=0.0)
        runner.observe(closer, 1.0)
        self.assertEqual(runner.avoid, 0.0)
        self.assertEqual(runner.stuck, 0)

    def test_the_run_records_what_it_did(self):
        runner = CorpseRunner()
        runner.observe(state(corpse_dy=-FAR, facing=0.0), 0.0)
        runner.observe(state(corpse_dy=-FAR, facing=1.0), 0.5)
        self.assertEqual(len(runner.history), 2)
        self.assertIn('distance', runner.history[0])
        self.assertIn('bearing_error', runner.history[1])


if __name__ == '__main__':
    unittest.main()
