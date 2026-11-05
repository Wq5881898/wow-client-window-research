"""Walk around obstacles instead of standing in front of them."""
import unittest

import client_obstacle as obstacle


class ObstacleTests(unittest.TestCase):
    def test_a_character_that_moves_is_aimed_at_the_target(self):
        wall = obstacle.Obstacle()
        self.assertEqual(wall.note(0.01), 0.0)
        self.assertFalse(wall.stuck)

    def test_a_character_that_does_not_move_gets_a_detour(self):
        wall = obstacle.Obstacle()
        detour = wall.note(0.0)
        self.assertNotEqual(detour, 0.0)
        self.assertTrue(wall.stuck)

    def test_the_detour_keeps_its_direction_while_the_character_is_stuck(self):
        wall = obstacle.Obstacle()
        first = wall.note(0.0)
        second = wall.note(0.0)
        third = wall.note(0.0)
        self.assertEqual(first, second)
        self.assertEqual(second, third)

    def test_the_other_side_is_tried_when_the_wall_holds(self):
        wall = obstacle.Obstacle(tries=2)
        first = wall.note(0.0)
        for _ in range(2):
            last = wall.note(0.0)
        self.assertNotEqual(first, last)

    def test_the_aim_goes_back_to_the_target_after_moving(self):
        wall = obstacle.Obstacle()
        wall.note(0.0)
        self.assertEqual(wall.note(0.01), 0.0)
        self.assertFalse(wall.stuck)

    def test_the_detour_turns_the_character_to_the_left(self):
        from client_danger_recovery import wrap
        state = {'pos_x': 0.0, 'pos_y': 0.0, 'facing': 0.0}
        target = (0.0, 0.1)
        # The target is to the south, so the heading that points at it is
        # half a turn. The heading of the client grows counter clockwise from
        # the north, so a positive detour turns the character to the left.
        plain = obstacle.wanted_heading(state, target, 0.0)
        left = obstacle.wanted_heading(state, target, 0.5)
        right = obstacle.wanted_heading(state, target, -0.5)
        self.assertAlmostEqual(abs(wrap(plain)), 3.14159, places=4)
        self.assertAlmostEqual(wrap(left - plain), 0.5, places=4)
        self.assertAlmostEqual(wrap(right - plain), -0.5, places=4)

    def test_the_error_of_the_heading_is_wrapped(self):
        state = {'pos_x': 0.0, 'pos_y': 0.0, 'facing': 0.0}
        target = (0.0, 0.1)
        error = obstacle.detour_heading(state, target, 0.0)
        # The target is behind the character, so the error is half a turn.
        self.assertAlmostEqual(error, 3.14159, places=4)
        # A heading that differs by more than half a turn is wrapped.
        state = {'pos_x': 0.0, 'pos_y': 0.0, 'facing': 3.0}
        error = obstacle.detour_heading(state, target, 0.0)
        self.assertLessEqual(abs(error), 3.14159)


if __name__ == '__main__':
    unittest.main()
