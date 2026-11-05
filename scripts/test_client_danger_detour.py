"""A test for the detour of the recovery.

The ghost stood in front of its corpse and walked back and forth, because
the detour changed its side on every step. The test shows that the side is
kept while the character does not move, and that the other side is only
tried when the current one never came closer.
"""
import unittest

from client_danger_recovery import DangerRecovery, bearing_to, wrap


def state(pos_x=0.5, pos_y=0.5, facing=0.0, corpse_dy=0.02,
          corpse_exists=True):
    return dict(sequence=1, game_ms=100, health=1, max_health=52, power=0,
                 combat=False, dead=True, target_exists=False,
                 target_guid='0x0', target_dead=False, target_health=0,
                 target_attackable=False, spell_range=2, spell_learned=True,
                 casting=False, speed=0.0, pos_x=pos_x, pos_y=pos_y,
                 facing=facing, corpse_x=0.5, corpse_y=0.5 + corpse_dy,
                 corpse_exists=corpse_exists, events=[])


class DetourTests(unittest.TestCase):
    def test_the_detour_keeps_its_side_while_the_character_is_stuck(self):
        machine = DangerRecovery()
        # The ghost is in front of the corpse and does not move.
        machine.observe(state(), 0.0)
        sides = []
        for step in range(4):
            machine.observe(state(pos_x=0.5, pos_y=0.5), 1.0 * step)
            sides.append(machine.avoid_side)
        # The side only changes when the other one is tried.
        self.assertEqual(len(set(sides)), 1)

    def test_the_detour_is_given_up_when_the_character_moves(self):
        machine = DangerRecovery()
        machine.observe(state(), 0.0)
        # The character moves and comes closer.
        machine.observe(state(pos_x=0.5, pos_y=0.52), 1.0)
        self.assertEqual(machine.avoid, 0.0)
        self.assertEqual(machine.stuck, 0)

    def test_the_best_distance_is_kept(self):
        machine = DangerRecovery()
        machine.observe(state(corpse_dy=0.05), 0.0)
        self.assertIsNotNone(machine.best_distance)


if __name__ == '__main__':
    unittest.main()
