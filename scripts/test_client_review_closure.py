"""Counterexamples for blocked-history loss and unsafe character entry."""
import unittest
from unittest.mock import patch
import math
from PIL import Image
import client_walk as walk
from client_obstacle import Obstacle
from lab_client_enter_character import login_form_visible, verify_player


class ClosureTests(unittest.TestCase):
    def test_real_walk_executor_reaches_backward_branch_after_turns(self):
        state = {'pos_x': .5, 'pos_y': .5, 'facing': 0.0}
        pressed = []
        def hold(key, seconds, hwnd=None):
            pressed.append(key)
            if key in (walk.VK_LEFT, walk.VK_RIGHT):
                sign = 1 if key == walk.VK_LEFT else -1
                state['facing'] = (state['facing'] + sign * seconds
                                   * walk.TURN_RATE) % (2 * math.pi)
        with patch.object(walk, 'hold', side_effect=hold):
            result = walk.walk_to(1, lambda: dict(state), (.5, .4), timeout=2)
        self.assertIn(walk.VK_BACKWARD, pressed)
        self.assertEqual(result.reason, 'no_progress')

    def test_turn_and_direction_change_preserve_backward_budget(self):
        obstacle = Obstacle(threshold=.0004)
        for _ in range(3):
            obstacle.note(0)
            obstacle.turned()
        self.assertTrue(obstacle.next_direction(3))
        obstacle.note(0)
        self.assertEqual(obstacle.consecutive_blocked, 4)
        self.assertEqual(obstacle.blocked, 4)

    def test_real_movement_resets_blocked_streak(self):
        obstacle = Obstacle(threshold=.0004)
        obstacle.note(0)
        obstacle.note(.0005)
        self.assertEqual(obstacle.consecutive_blocked, 0)

    def test_unconfirmed_character_is_rejected_even_with_plausible_health(self):
        with self.assertRaises(ValueError):
            verify_player({'health': 130, 'player_guid': 'other'}, 'expected')
        with self.assertRaises(ValueError):
            verify_player({'health': 130}, None)

    def test_known_player_is_verified_while_dead_without_recovery(self):
        self.assertTrue(verify_player({'dead': True, 'player_guid': 'expected'},
                                      'expected'))

    def test_unknown_screen_cannot_receive_credentials(self):
        self.assertFalse(login_form_visible(Image.new('RGB', (1920, 1080))))
        self.assertFalse(login_form_visible(Image.new('RGB', (1024, 768))))


if __name__ == '__main__':
    unittest.main()
