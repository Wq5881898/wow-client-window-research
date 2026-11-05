"""Decisions of the danger zone recovery."""
import math
import unittest
from client_danger_recovery import (DangerRecovery, bearing_to, distance_to,
                                    wrap, CORPSE_RANGE)
from client_path_memory import PathMemory

PLAYER_X = 0.4933
PLAYER_Y = 0.4223
FAR = 0.02
NEAR = CORPSE_RANGE * 0.5


def state(corpse_dx=0.0, corpse_dy=FAR, **changes):
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
    def test_a_target_to_the_south_is_a_half_turn(self):
        self.assertAlmostEqual(bearing_to(state(), (PLAYER_X, PLAYER_Y + FAR)),
                               math.pi)

    def test_a_target_to_the_north_is_the_north(self):
        self.assertAlmostEqual(bearing_to(state(), (PLAYER_X, PLAYER_Y - FAR)),
                               0.0)

    def test_a_target_to_the_east_is_a_quarter_turn_to_the_right(self):
        self.assertAlmostEqual(bearing_to(state(), (PLAYER_X + FAR, PLAYER_Y)),
                               -math.pi / 2)

    def test_the_distance_is_measured(self):
        self.assertAlmostEqual(distance_to(state(), (PLAYER_X, PLAYER_Y + 0.003)),
                               0.003)

    def test_wrap_brings_an_angle_into_range(self):
        self.assertAlmostEqual(wrap(3 * math.pi), math.pi)
        self.assertAlmostEqual(wrap(-3 * math.pi), -math.pi)


class PathMemoryTest(unittest.TestCase):
    def test_a_point_is_kept_when_it_is_far_enough(self):
        memory = PathMemory(min_step=0.002)
        self.assertTrue(memory.record(0.0, 0.0))
        self.assertFalse(memory.record(0.001, 0.0))
        self.assertTrue(memory.record(0.005, 0.0))
        self.assertEqual(len(memory.points), 2)

    def test_the_length_of_the_path_is_measured(self):
        memory = PathMemory(min_step=0.001)
        memory.record(0.0, 0.0)
        memory.record(0.03, 0.04)
        self.assertAlmostEqual(memory.length(), 0.05)

    def test_a_point_of_another_map_area_is_dropped(self):
        # The coordinates of the areas are not comparable, so a point that
        # is far away from the last one does not belong to the path.
        memory = PathMemory(min_step=0.001)
        memory.record(0.0, 0.0)
        self.assertFalse(memory.record(0.9, 0.4))
        self.assertEqual(len(memory.points), 1)
        self.assertAlmostEqual(memory.length(), 0.0)
        self.assertTrue(memory.record(0.01, 0.0))
        self.assertAlmostEqual(memory.length(), 0.01)

    def test_the_route_back_leads_to_the_start(self):
        memory = PathMemory(min_step=0.001)
        memory.record(0.0, 0.0)
        memory.record(0.01, 0.0)
        memory.record(0.02, 0.0)
        route = memory.route_back(0.02, 0.0)
        self.assertEqual(route[0], (0.02, 0.0))
        self.assertEqual(route[-1], (0.0, 0.0))

    def test_a_long_route_is_split_into_chunks(self):
        memory = PathMemory(min_step=0.001)
        for index in range(11):
            memory.record(index * 0.01, 0.0)
        pieces = memory.chunks(memory.points, max_length=0.025)
        self.assertTrue(len(pieces) > 1)
        for piece in pieces:
            length = sum(math.dist(a, b) for a, b in zip(piece, piece[1:]))
            self.assertLessEqual(length, 0.035)


class GraveyardAnchorTests(unittest.TestCase):
    """The anchor of the graveyard is where the ghost appears.

    The counterexample of the review: the character dies at (0.6, 0.6) and
    the corpse is not released yet, so the position is the place of the
    death. The ghost appears at the graveyard, and only that spot is the
    anchor of the route back.
    """

    def test_the_anchor_is_not_the_place_of_the_death(self):
        machine = DangerRecovery()
        action = machine.observe(state(corpse_exists=False, pos_x=0.6,
                                       pos_y=0.6), 0.0)
        self.assertEqual(action['action'], 'RELEASE')
        self.assertIsNone(machine.graveyard)
        # The spirit was released and the ghost stands at the graveyard.
        machine.observe(state(corpse_exists=True, pos_x=0.49, pos_y=0.43), 1.0)
        self.assertEqual(machine.phase, 'GHOST')
        self.assertAlmostEqual(machine.graveyard[0], 0.49)
        self.assertAlmostEqual(machine.graveyard[1], 0.43)

    def test_the_body_on_the_ground_is_a_state_of_its_own(self):
        machine = DangerRecovery()
        machine.observe(state(corpse_exists=False), 0.0)
        self.assertEqual(machine.phase, 'RELEASING')
        # The release is repeated while the window is still up.
        action = machine.observe(state(corpse_exists=False), 1.0)
        self.assertEqual(action['action'], 'RELEASE')
        self.assertEqual(action['attempt'], 2)

    def test_the_end_of_the_task_is_kept_when_the_character_dies_again(self):
        # The end of the task is a property of the task and not of the
        # death: a second death has the same end as the first one, so the
        # two runs can be compared. The place where the second ghost
        # appeared is kept apart.
        machine = DangerRecovery()
        machine.observe(state(corpse_exists=False), 0.0)
        machine.observe(state(corpse_exists=True), 1.0)
        first = machine.graveyard
        machine.observe(state(dead=False, health=26), 2.0)
        # A second death somewhere else.
        machine.observe(state(corpse_exists=False, pos_x=0.7, pos_y=0.7), 3.0)
        self.assertEqual(machine.graveyard, first)
        machine.observe(state(corpse_exists=True, pos_x=0.5, pos_y=0.44), 4.0)
        self.assertEqual(machine.graveyard, first)
        self.assertEqual(len(machine.releases), 2)
        self.assertAlmostEqual(machine.releases[1]['position'][0], 0.5)
        self.assertFalse(machine.releases[1]['is_the_end'])


class DangerRecoveryTest(unittest.TestCase):
    def test_a_living_character_without_a_route_is_done(self):
        machine = DangerRecovery()
        action = machine.observe(state(dead=False, health=52), 0.0)
        self.assertEqual(action['action'], 'DONE')

    def test_a_missing_corpse_gives_up(self):
        machine = DangerRecovery()
        # The client only knows the spot of the corpse after the spirit was
        # released, so the first step is to release it.
        for _ in range(5):
            action = machine.observe(state(corpse_exists=False), 0.0)
        self.assertEqual(action['action'], 'GIVE_UP')
        self.assertEqual(action['reason'], 'no_corpse')

    def test_the_spirit_is_released_first(self):
        machine = DangerRecovery()
        action = machine.observe(state(corpse_exists=False), 0.0)
        self.assertEqual(action['action'], 'RELEASE')
        self.assertEqual(machine.phase, 'RELEASING')

    def test_a_far_corpse_in_front_makes_the_character_walk(self):
        machine = DangerRecovery()
        action = machine.observe(state(corpse_dy=-FAR, facing=0.0), 0.0)
        self.assertEqual(action['action'], 'WALK')

    def test_a_corpse_to_the_south_makes_the_character_turn_left(self):
        machine = DangerRecovery()
        action = machine.observe(state(corpse_dy=FAR, facing=0.0), 0.0)
        self.assertEqual(action['action'], 'TURN')
        self.assertEqual(action['direction'], 'left')

    def test_a_corpse_to_the_west_makes_the_character_turn_left(self):
        machine = DangerRecovery()
        action = machine.observe(state(corpse_dx=-FAR, corpse_dy=0.0,
                                       facing=0.0), 0.0)
        self.assertEqual(action['action'], 'TURN')
        self.assertEqual(action['direction'], 'left')

    def test_a_corpse_to_the_east_makes_the_character_turn_right(self):
        machine = DangerRecovery()
        action = machine.observe(state(corpse_dx=FAR, corpse_dy=0.0,
                                       facing=0.0), 0.0)
        self.assertEqual(action['action'], 'TURN')
        self.assertEqual(action['direction'], 'right')

    def test_a_corpse_in_reach_is_accepted(self):
        machine = DangerRecovery()
        action = machine.observe(state(corpse_dy=NEAR, facing=0.0), 0.0)
        self.assertEqual(action['action'], 'ACCEPT')
        self.assertEqual(action['point'], (960, 230))

    def test_the_walk_of_the_ghost_is_remembered(self):
        machine = DangerRecovery()
        machine.observe(state(corpse_dy=-FAR, facing=0.0), 0.0)
        machine.observe(state(corpse_dy=-FAR, facing=0.0, pos_y=PLAYER_Y - 0.01),
                        1.0)
        self.assertTrue(len(machine.memory.points) >= 2)

    def test_the_revived_character_follows_the_path_back(self):
        machine = DangerRecovery()
        # The ghost walks north towards the corpse.
        machine.observe(state(corpse_dy=-FAR, facing=0.0), 0.0)
        machine.observe(state(corpse_dy=-FAR, facing=0.0, pos_y=PLAYER_Y - 0.01),
                        1.0)
        machine.observe(state(corpse_dy=NEAR, facing=0.0, pos_y=PLAYER_Y - 0.02),
                        2.0)
        # The character is alive again and stands where it died.
        action = machine.observe(state(dead=False, health=26,
                                       pos_y=PLAYER_Y - 0.02), 3.0)
        self.assertEqual(machine.phase, 'ESCAPE')
        # The character has to turn around to walk back to the graveyard.
        self.assertEqual(action['action'], 'TURN')
        self.assertEqual(len(machine.route), 3)
        # The first waypoint of the way back is the place the ghost was
        # seen last, the last one is the graveyard.
        self.assertAlmostEqual(machine.route[-1][1], PLAYER_Y)

    def test_the_escape_ends_at_the_graveyard(self):
        machine = DangerRecovery()
        machine.observe(state(corpse_dy=-FAR, facing=0.0), 0.0)
        machine.observe(state(corpse_dy=NEAR, facing=0.0, pos_y=PLAYER_Y - 0.02),
                        1.0)
        machine.observe(state(dead=False, health=26, pos_y=PLAYER_Y - 0.02), 2.0)
        # The character is back at the place where it appeared as a ghost.
        action = machine.observe(state(dead=False, health=26), 3.0)
        self.assertEqual(action['action'], 'DONE')
        self.assertEqual(action['reason'], 'safe')
        self.assertEqual(machine.phase, 'SAFE')

    def test_the_run_reports_the_two_corpses(self):
        machine = DangerRecovery()
        machine.observe(state(corpse_dy=NEAR, facing=0.0), 0.0)
        self.assertEqual(len(machine.corpses), 1)
        self.assertEqual(machine.corpses[0]['corpse'],
                         [PLAYER_X, PLAYER_Y + NEAR])

    def test_a_second_death_starts_the_run_again(self):
        machine = DangerRecovery()
        machine.observe(state(corpse_dy=NEAR, facing=0.0), 0.0)
        machine.observe(state(dead=False, health=26), 1.0)
        # The character dies a second time somewhere else.
        machine.observe(state(corpse_dx=0.01, corpse_dy=NEAR, facing=0.0,
                               pos_x=PLAYER_X + 0.05), 2.0)
        self.assertEqual(machine.phase, 'GHOST')
        # The end of the task is the place of the first ghost.
        self.assertAlmostEqual(machine.graveyard[0], PLAYER_X)
        # The path of the first death is kept, so the two can be compared.
        self.assertEqual(len(machine.corpses), 1)
        self.assertEqual(len(machine.memory.points), 1)
        self.assertEqual(machine.deaths, 2)

    def test_a_corpse_is_counted_once_per_death(self):
        # The dialog of the resurrection may have to be clicked more than
        # once. Every click must not add another corpse.
        machine = DangerRecovery()
        machine.observe(state(corpse_dy=NEAR, facing=0.0), 0.0)
        machine.observe(state(corpse_dy=NEAR, facing=0.0), 1.0)
        machine.observe(state(corpse_dy=NEAR, facing=0.0), 2.0)
        self.assertEqual(len(machine.corpses), 1)
        self.assertEqual(machine.corpses[0]['death'], 1)

    def test_a_second_corpse_is_counted(self):
        machine = DangerRecovery()
        machine.observe(state(corpse_dy=NEAR, facing=0.0), 0.0)
        machine.observe(state(dead=False, health=26), 1.0)
        # The second death: the ghost appears on the new corpse.
        machine.observe(state(corpse_dx=0.01, corpse_dy=NEAR, facing=0.0,
                               pos_x=PLAYER_X + 0.01, pos_y=PLAYER_Y + NEAR),
                        2.0)
        machine.observe(state(corpse_dx=0.01, corpse_dy=NEAR, facing=0.0,
                               pos_x=PLAYER_X + 0.01, pos_y=PLAYER_Y + NEAR),
                        3.0)
        self.assertEqual(len(machine.corpses), 2)
        self.assertEqual(machine.corpses[1]['death'], 2)

    def test_the_run_gives_up_after_the_budget(self):
        machine = DangerRecovery(time_budget=10.0)
        machine.observe(state(corpse_dy=-FAR, facing=0.0), 0.0)
        action = machine.observe(state(corpse_dy=-FAR, facing=0.0), 20.0)
        self.assertEqual(action['action'], 'GIVE_UP')
        self.assertEqual(action['reason'], 'time_budget')


if __name__ == '__main__':
    unittest.main()
