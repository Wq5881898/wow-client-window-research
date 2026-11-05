"""The names of the people around the character.

The candidates of a name are found in the picture, so the cursor only has to
be put on a few places instead of a grid over the whole screen.
"""
import unittest
from pathlib import Path

from PIL import Image

import client_names as names

FIXTURE = Path(__file__).resolve().parent / 'fixtures' / 'names-scene.png'


class NameCandidateTests(unittest.TestCase):
    def setUp(self):
        self.image = Image.open(FIXTURE)

    def test_the_name_of_a_creature_is_found(self):
        candidates = names.name_candidates(self.image)
        self.assertTrue(candidates)
        # The name of the wolf is on the left of the picture.
        left = [item for item in candidates if item['x'] < 700]
        self.assertTrue(left)

    def test_the_model_is_below_the_name(self):
        candidates = names.name_candidates(self.image)
        self.assertTrue(candidates)
        for candidate in candidates:
            point = names.model_point(candidate)
            self.assertGreaterEqual(point[1], candidate['bottom'])
            self.assertLessEqual(point[1], 940)

    def test_the_minimap_is_not_a_candidate(self):
        # The minimap sits in the corner and has yellow marks of its own.
        candidates = names.name_candidates(self.image)
        for candidate in candidates:
            self.assertLess(candidate['x'], 1700)
            self.assertLess(candidate['y'], 940)

    def test_the_colour_of_a_name_is_recognised(self):
        self.assertTrue(names.is_name_pixel((240, 220, 90)))
        self.assertFalse(names.is_name_pixel((60, 90, 40)))
        self.assertFalse(names.is_name_pixel((120, 110, 100)))

    def test_the_widest_candidates_come_first(self):
        candidates = [{'x': 0, 'y': 0, 'pixels': 4, 'left': 0, 'right': 10,
                       'top': 0, 'bottom': 4},
                      {'x': 0, 'y': 0, 'pixels': 4, 'left': 0, 'right': 40,
                       'top': 0, 'bottom': 4}]
        ordered = names.spread(candidates)
        self.assertEqual(ordered[0]['right'], 40)


if __name__ == '__main__':
    unittest.main()
