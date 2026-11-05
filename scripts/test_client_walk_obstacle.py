"""The walk has to tell a blocked step from a turn.

The walk counted a turn as a collision, so it gave up while the character
was only looking the other way. The state of the obstacle had two owners as
well, so the same step was counted twice and the way out of an obstacle was
tried too late. A walk that does not come closer has to end with a reason,
so it cannot look like a walk that is still on its way.
"""
import unittest

import client_walk as walk


class FakeReader:
    """A reader that hands out the states it was given."""

    def __init__(self, states):
        self.states = list(states)
        self.calls = 0

    def __call__(self):
        state = self.states[min(self.calls, len(self.states) - 1)]
        self.calls += 1
        return state


def state(x=0.5, y=0.43, facing=0.0):
    return {'pos_x': x, 'pos_y': y, 'facing': facing}


class WalkObstacleTests(unittest.TestCase):
    def setUp(self):
        self.pressed = []
        self.original = walk.hold
        walk.hold = self.fake_hold
        self.addCleanup(self.restore)

    def fake_hold(self, vk, seconds, hwnd=None):
        self.pressed.append(vk)

    def restore(self):
        walk.hold = self.original

    def test_a_walk_that_arrives_says_so(self):
        reader = FakeReader([state(0.5, 0.43)])
        result = walk.walk_to(1, reader, (0.5, 0.4295), timeout=2.0)
        self.assertTrue(result.arrived)
        self.assertEqual(result.reason, None)

    def test_a_turn_is_not_a_collision(self):
        # The character looks away from the target, so every step is a turn
        # and the character never moves. A turn is not a collision.
        reader = FakeReader([state(0.5, 0.43, facing=3.14159)])
        result = walk.walk_to(1, reader, (0.5, 0.36), timeout=5.0)
        self.assertEqual(result.blocked, 0)
        self.assertTrue(self.pressed)
        self.assertNotIn(walk.VK_FORWARD, self.pressed)

    def test_a_blocked_step_is_counted_once(self):
        # The character walks into a rock: the position does not change.
        # Every step that was meant to move the character and did not move
        # it counts once, and only those steps count.
        reader = FakeReader([state(0.5, 0.43, facing=0.0)])
        result = walk.walk_to(1, reader, (0.5, 0.36), timeout=5.0)
        forward = self.pressed.count(walk.VK_FORWARD)
        self.assertGreater(forward, 0)
        self.assertEqual(result.blocked, forward)

    def test_a_walk_without_progress_ends_with_a_reason(self):
        reader = FakeReader([state(0.5, 0.43, facing=0.0)])
        result = walk.walk_to(1, reader, (0.5, 0.36), timeout=20.0)
        self.assertFalse(result.arrived)
        self.assertEqual(result.reason, 'no_progress')

    def test_a_walk_that_moves_on_ends_without_a_reason(self):
        # The character comes closer every step, so the walk does not end
        # with the reason of a walk that is stuck.
        positions = [(0.5, 0.40), (0.5, 0.39), (0.5, 0.38), (0.5, 0.37),
                     (0.5, 0.361)]
        reader = FakeReader([state(x, y, facing=0.0) for x, y in positions])
        result = walk.walk_to(1, reader, (0.5, 0.36), timeout=5.0)
        self.assertIsNone(result.reason)

    def test_a_lost_focus_ends_the_walk(self):
        def broken(vk, seconds, hwnd=None):
            raise walk.FocusLost('the window is in the back')
        walk.hold = broken
        reader = FakeReader([state(0.5, 0.43, facing=0.0)])
        result = walk.walk_to(1, reader, (0.5, 0.36), timeout=5.0)
        self.assertEqual(result.reason, 'no_focus')
        self.assertFalse(result.arrived)


if __name__ == '__main__':
    unittest.main()
