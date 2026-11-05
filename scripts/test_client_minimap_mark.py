"""The heading of a mark on the minimap points at the mark.

The movement at the heading h is (-sin h, -cos h) in the map coordinates,
where x grows to the east and y to the south. A mark to the south east of
the character therefore has a heading of minus a quarter turn, and the
first version of the conversion had the sign of the east wrong, so the
character walked away from the mark.
"""
import math
import unittest

import client_minimap_mark as mark


class HeadingTests(unittest.TestCase):
    def heading_of(self, east, south):
        return mark.heading_to({'x': 100 + east, 'y': 100 + south},
                               (100, 100))

    def movement_of(self, east, south):
        """The direction the character walks at the heading of the mark."""
        heading = self.heading_of(east, south)
        return (-math.sin(heading), -math.cos(heading))

    def test_a_mark_to_the_north_is_a_heading_of_zero(self):
        self.assertAlmostEqual(self.heading_of(0, -40), 0.0)

    def test_a_mark_to_the_south_is_a_half_turn(self):
        self.assertAlmostEqual(abs(self.heading_of(0, 40)), math.pi)

    def test_a_mark_to_the_east_is_a_quarter_turn_to_the_right(self):
        heading = self.heading_of(40, 0)
        self.assertAlmostEqual(heading, -math.pi / 2)

    def test_the_walk_goes_towards_the_mark(self):
        for east, south in ((40, 0), (-40, 0), (0, 40), (0, -40),
                            (30, 30), (-30, 30), (30, -30), (-30, -30)):
            moved_east, moved_south = self.movement_of(east, south)
            # The movement has to point into the same quarter as the mark.
            if east == 0:
                same = moved_south * south > 0
            elif south == 0:
                same = moved_east * east > 0
            else:
                same = moved_east * east > 0 and moved_south * south > 0
            self.assertTrue(same, (east, south, moved_east, moved_south))

    def test_the_distance_of_the_mark(self):
        self.assertAlmostEqual(
            mark.distance_to({'x': 130, 'y': 140}, (100, 100)), 50.0)


if __name__ == '__main__':
    unittest.main()
