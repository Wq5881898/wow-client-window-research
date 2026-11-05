"""The direction of a mark on the minimap.

The minimap is centred on the character and has north at the top, so the
place of a mark on it gives the direction to that mark. The quest marker
of the valley is drawn in yellow, and it is the way back to the abbey.

The mark is found by its colour and its shape: the quest marker is a tall
narrow exclamation mark, while the dots of the people and the creatures are
small squares.

The functions work on a picture of the whole screen and on a picture of
the minimap alone; the centre of the map is given in the coordinates of the
picture that is looked at.
"""
import math

from PIL import Image

# The minimap of the fullscreen client (1920x1080).
MINIMAP = (1735, 20, 1910, 195)
# The middle of the minimap is the character.
CENTRE = (1822, 108)


def quest_marker(image, area=MINIMAP, centre=CENTRE):
    """The place of the quest marker on the minimap.

    None is returned when there is no marker in the picture.
    """
    region = image.convert('RGB').crop(area)
    pixels = region.load()
    found = []
    for y in range(0, region.size[1]):
        for x in range(0, region.size[0]):
            r, g, b = pixels[x, y]
            if r > 190 and g > 150 and b < 110 and r > b + 90:
                found.append((x + area[0], y + area[1]))
    groups = []
    for point in found:
        for group in groups:
            if any(abs(point[0] - other[0]) <= 4 and
                   abs(point[1] - other[1]) <= 4 for other in group):
                group.append(point)
                break
        else:
            groups.append([point])
    marks = []
    for group in groups:
        xs = [point[0] for point in group]
        ys = [point[1] for point in group]
        width = max(xs) - min(xs)
        height = max(ys) - min(ys)
        if len(group) < 6:
            continue
        if height >= 8 and width <= 8:
            # A tall narrow group is the exclamation mark of a quest.
            marks.append({'x': sum(xs) // len(xs), 'y': sum(ys) // len(ys),
                          'width': width, 'height': height,
                          'pixels': len(group)})
    if not marks:
        return None
    return max(marks, key=lambda mark: mark['height'])


def marker_in(image, centre=None):
    """The quest marker of a picture of the minimap alone.

    The picture of the minimap has its own size, so the centre of the map
    is taken from the picture itself.
    """
    region = image.convert('RGB')
    if centre is None:
        centre = (region.size[0] // 2, region.size[1] // 2)
    found = quest_marker(region, area=(0, 0, region.size[0], region.size[1]),
                         centre=centre)
    return found


def heading_to(mark, centre=CENTRE):
    """The heading of a mark on the minimap.

    The map has north at the top and the heading of the client grows
    counter clockwise from the north, so the heading is the angle of the
    mark counted from the top towards the right.
    """
    east = mark['x'] - centre[0]
    south = mark['y'] - centre[1]
    return math.atan2(east, -south)


def distance_to(mark, centre=CENTRE):
    """How far the mark is from the middle of the minimap."""
    return math.hypot(mark['x'] - centre[0], mark['y'] - centre[1])
