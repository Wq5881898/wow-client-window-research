"""Find the names of the people around the character.

The full screen grid of the earlier search took a minute per direction and
still missed the small models, because a name is only a few pixels wide. The
name of a person is drawn above the model in a colour of its own, so the
places where a name can be are found in the picture first, and only there
the cursor is put. That is the order the knowledge base asks for: the scan
stays on the candidate places of a name and checks the budget at every
step.
"""
import math

from PIL import Image

# The area of the picture that holds the world. The minimap in the corner
# and the panel of the probe at the bottom are left out.
WORLD = (0, 0, 1700, 940)

# The frame of the character in the top left corner holds the name of the
# character itself, and the area of the target holds the name of the target.
# Both are not the people around the character.
UNIT_FRAME = (0, 0, 300, 110)
TARGET_FRAME = (260, 20, 580, 90)

# The colours a name is drawn in. A friendly name is yellow, a hostile one
# is red, a neutral one is white.
NAME_COLOURS = (
    (220, 200, 60), (240, 220, 90), (250, 235, 140),
    (200, 60, 50), (230, 90, 70),
    (230, 230, 230), (245, 245, 245),
)


def is_name_pixel(colour):
    """True for a pixel that can belong to the text of a name."""
    r, g, b = colour
    for want in NAME_COLOURS:
        if (abs(r - want[0]) <= 40 and abs(g - want[1]) <= 40
                and abs(b - want[2]) <= 60):
            return True
    return False


def name_candidates(image, area=WORLD, cluster=14):
    """The places in the picture where a name can be.

    The pixels of a name are grouped, and the middle of a group is the place
    where the cursor finds the name.
    """
    region = image.convert('RGB').crop(area)
    pixels = region.load()
    found = []
    for y in range(0, region.size[1], 2):
        for x in range(0, region.size[0], 2):
            if is_name_pixel(pixels[x, y]):
                found.append((x + area[0], y + area[1]))
    groups = []
    for point in found:
        for group in groups:
            if any(abs(point[0] - other[0]) <= cluster
                   and abs(point[1] - other[1]) <= cluster for other in group):
                group.append(point)
                break
        else:
            groups.append([point])
    candidates = []
    for group in groups:
        if len(group) < 4:
            # A single bright pixel is a spark of light, not a name.
            continue
        xs = [point[0] for point in group]
        ys = [point[1] for point in group]
        candidates.append({'x': sum(xs) // len(xs), 'y': sum(ys) // len(ys),
                           'pixels': len(group),
                           'left': min(xs), 'right': max(xs),
                           'top': min(ys), 'bottom': max(ys)})
    return candidates


def model_point(candidate):
    """The point of the model below a name.

    The name is written above the model, so the cursor finds the creature a
    little below the text.
    """
    return (candidate['x'], min(940, candidate['bottom'] + 12))


def spread(candidates, limit=40):
    """The candidates, the widest ones first.

    A long text is a name and a short one is usually a number of the combat
    text, so the long groups are tried first.
    """
    ordered = sorted(candidates,
                     key=lambda item: -(item['right'] - item['left']))
    return ordered[:limit]
