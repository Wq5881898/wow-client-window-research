"""Look at the pixels of the minimap of a picture.

The minimap is the round window at the top right of the screen. It shows the
zone with north at the top, the arrow of the character in the middle and a
dot for every creature and person around. Reading it gives the driver a way
to find a place it does not know yet.

This script only prints what is in the picture, so the detection can be built
on real pixels instead of on guesses.
"""
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = sys.argv[1]
    image = Image.open(path).convert('RGB')
    width, height = image.size
    print('picture', image.size)
    # The minimap sits in the corner; find the round black frame.
    region = image.crop((width - 260, 0, width, 260))
    colours = Counter(region.getdata())
    print('most common colours in the corner:')
    for colour, count in colours.most_common(12):
        print('  ', colour, count)
    # The bright yellow of the quest marker.
    yellow = []
    for y in range(0, 260, 2):
        for x in range(0, 260, 2):
            r, g, b = region.getpixel((x, y))
            if r > 200 and g > 200 and b < 90:
                yellow.append((x + width - 260, y))
    print('bright yellow pixels:', len(yellow))
    if yellow:
        xs = [point[0] for point in yellow]
        ys = [point[1] for point in yellow]
        print('  x range', min(xs), max(xs), '| y range', min(ys), max(ys))
        # Group the yellow pixels into blobs: the quest marker and the dots
        # of the creatures are separate blobs.
        blobs = []
        for point in yellow:
            for blob in blobs:
                if any(abs(point[0] - other[0]) <= 3 and
                       abs(point[1] - other[1]) <= 3 for other in blob):
                    blob.append(point)
                    break
            else:
                blobs.append([point])
        print('  blobs:')
        for blob in blobs:
            bx = [point[0] for point in blob]
            by = [point[1] for point in blob]
            print('    x %d-%d y %d-%d pixels %d centre (%d, %d)'
                  % (min(bx), max(bx), min(by), max(by), len(blob),
                     sum(bx) // len(bx), sum(by) // len(by)))
    # The arrow of the character is a light triangle near the middle.
    light = []
    for y in range(60, 200, 1):
        for x in range(width - 220, width - 40, 1):
            r, g, b = image.getpixel((x, y))
            if r > 200 and g > 200 and b > 200:
                light.append((x, y))
    print('near white pixels in the map area:', len(light))
    if light:
        xs = [point[0] for point in light]
        ys = [point[1] for point in light]
        print('  x range', min(xs), max(xs), '| y range', min(ys), max(ys))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
