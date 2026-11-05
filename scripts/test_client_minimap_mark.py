"""The quest marker of the minimap is found in a picture."""
import unittest
from pathlib import Path

from PIL import Image

import client_minimap_mark as mark

FIXTURES = Path(__file__).resolve().parent / 'fixtures'


class QuestMarkerTests(unittest.TestCase):
    def setUp(self):
        self.image = Image.open(FIXTURES / 'minimap-valley.png').convert('RGB')
        self.centre = (self.image.size[0] // 2, self.image.size[1] // 2)

    def test_the_marker_of_the_valley_is_found(self):
        found = mark.marker_in(self.image)
        self.assertIsNotNone(found)
        # The marker is a tall narrow group, the exclamation mark of a quest.
        self.assertGreaterEqual(found['height'], 8)
        self.assertLessEqual(found['width'], 8)

    def test_the_distance_grows_when_the_marker_leaves_the_middle(self):
        found = mark.marker_in(self.image)
        self.assertGreater(mark.distance_to(found, self.centre), 0)

    def test_the_marker_gives_a_heading(self):
        found = mark.marker_in(self.image)
        heading = mark.heading_to(found, self.centre)
        self.assertGreaterEqual(heading, -3.15)
        self.assertLessEqual(heading, 3.15)

    def test_the_marker_of_the_crossroads_points_somewhere_else(self):
        # The two pictures were taken in different places, so the marker of
        # the quest is not in the same direction in both.
        other = Image.open(FIXTURES / 'minimap-crossroads.png').convert('RGB')
        centre = (other.size[0] // 2, other.size[1] // 2)
        first = mark.heading_to(mark.marker_in(self.image), self.centre)
        second = mark.heading_to(mark.marker_in(other), centre)
        self.assertNotAlmostEqual(first, second, places=1)


if __name__ == '__main__':
    unittest.main()
