import math
import unittest
from pathlib import Path

from PIL import Image

import client_minimap as mm

FIXTURE = Path(__file__).resolve().parent / 'fixtures' / 'minimap-northshire.png'
# The fixture is a crop of the screen that starts at x = 1660.
OFFSET = 1660


class MinimapTest(unittest.TestCase):
    def setUp(self):
        self.image = Image.open(FIXTURE)
        self.centre = (mm.CENTRE[0] - OFFSET, mm.CENTRE[1])

    def test_the_quest_marker_is_found(self):
        markers = mm.find_markers(self.image, centre=self.centre)
        self.assertTrue(markers)
        # The exclamation mark of the quest is the biggest group.
        self.assertGreaterEqual(markers[0]['pixels'], 15)
        self.assertEqual(markers[0]['x'], 138)
        self.assertEqual(markers[0]['y'], 124)

    def test_the_name_of_the_zone_is_not_a_marker(self):
        markers = mm.find_markers(self.image, centre=self.centre)
        for marker in markers:
            self.assertNotIn(marker['y'], range(0, 26))

    def test_the_direction_of_a_marker_is_read_from_the_map(self):
        markers = mm.find_markers(self.image, centre=self.centre)
        east, south = mm.direction(self.centre, markers[0])
        self.assertGreater(east, 0)
        self.assertGreater(south, 0)
        # The heading grows counter clockwise from the north, so a marker to
        # the south east has a heading between minus pi and zero.
        angle = mm.heading(self.centre, markers[0])
        self.assertLess(angle, 0)
        self.assertGreater(angle, -math.pi)

    def test_a_marker_to_the_north_has_a_heading_of_zero(self):
        marker = {'x': self.centre[0], 'y': self.centre[1] - 40}
        self.assertAlmostEqual(mm.heading(self.centre, marker), 0.0)

    def test_a_marker_to_the_east_has_a_heading_of_minus_a_quarter_turn(self):
        # Walking at the heading h moves the position by (-sin h, -cos h),
        # so east is the heading of minus a quarter turn.
        marker = {'x': self.centre[0] + 40, 'y': self.centre[1]}
        self.assertAlmostEqual(mm.heading(self.centre, marker), -math.pi / 2)

    def test_a_marker_to_the_south_has_a_heading_of_pi(self):
        marker = {'x': self.centre[0], 'y': self.centre[1] + 40}
        self.assertAlmostEqual(abs(mm.heading(self.centre, marker)), math.pi)

    def test_the_walk_of_a_heading_points_at_the_marker(self):
        # The heading has to move the character towards the marker.
        east, south = 20, 30
        angle = math.atan2(-east, -south)
        moved_east = -math.sin(angle) * 100
        moved_south = -math.cos(angle) * 100
        self.assertGreater(moved_east, 0)
        self.assertGreater(moved_south, 0)

    def test_the_markers_of_the_crossroads_are_found(self):
        image = Image.open(Path(__file__).resolve().parent / 'fixtures' /
                           'minimap-crossroads.png')
        markers = mm.find_markers(image, centre=self.centre)
        self.assertTrue(markers)
        kinds = set(marker['kind'] for marker in markers)
        self.assertIn('blue', kinds)

    def test_the_yellow_of_the_markers_is_recognised(self):
        self.assertTrue(mm.saturated_yellow((255, 223, 0)))
        self.assertFalse(mm.saturated_yellow((50, 57, 6)))
        self.assertFalse(mm.saturated_yellow((200, 200, 200)))

    def test_the_blue_of_the_markers_is_recognised(self):
        # The colour that was measured on the map of the crossroads.
        self.assertTrue(mm.saturated_blue((72, 81, 114)))
        self.assertFalse(mm.saturated_blue((50, 57, 6)))


if __name__ == '__main__':
    unittest.main()
