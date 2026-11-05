"""Read the minimap of the client.

The minimap is the round window at the top right of the screen. It is
centred on the character and north is at the top, so the position of a
marker on it gives the direction to that marker: the driver can walk to a
place it has never been to.

The markers are drawn in saturated yellow: the exclamation mark of a quest
and the dots of the creatures and the people around. The frame of the
minimap and the name of the zone are drawn in other colours and are left
alone.
"""
import math

# The centre of the minimap of the fullscreen client (1920x1080). It is the
# character itself, because the minimap follows the character.
CENTRE = (1786, 112)

# The radius of the round window. The name of the zone is drawn above the
# window and the zoom buttons beside it, so the search stays inside the
# round part.
RADIUS = 85


def saturated_yellow(colour):
    """True for the yellow of the markers."""
    r, g, b = colour
    return r > 235 and 180 < g < 245 and b < 45


def saturated_blue(colour):
    """True for the blue of the markers.

    The mark of a quest that can be taken is drawn in blue, the mark of a
    tracked quest in yellow.
    """
    r, g, b = colour
    return b > 110 and b > r + 30 and b > g + 15


def find_markers(image, centre=CENTRE, radius=RADIUS):
    """The markers of the minimap as (x, y) points.

    A marker is a small group of yellow pixels; the middle of the group is
    the position of the marker.
    """
    pixels = image.convert('RGB').load()
    width, height = image.size
    found = []
    for y in range(max(0, centre[1] - radius), min(height, centre[1] + radius)):
        for x in range(max(0, centre[0] - radius),
                       min(width, centre[0] + radius)):
            if saturated_yellow(pixels[x, y]):
                found.append((x, y, 'yellow'))
            elif saturated_blue(pixels[x, y]):
                found.append((x, y, 'blue'))
    blobs = []
    for point in found:
        for blob in blobs:
            if any(abs(point[0] - other[0]) <= 3 and
                   abs(point[1] - other[1]) <= 3 for other in blob):
                blob.append(point)
                break
        else:
            blobs.append([point])
    markers = []
    for blob in blobs:
        xs = [point[0] for point in blob]
        ys = [point[1] for point in blob]
        kinds = set(point[2] for point in blob)
        marker = {'x': sum(xs) // len(xs), 'y': sum(ys) // len(ys),
                  'pixels': len(blob),
                  'kind': 'yellow' if 'yellow' in kinds else 'blue',
                  'height': max(ys) - min(ys),
                  'width': max(xs) - min(xs)}
        # The mark of a quest is a tall thin exclamation mark, the dot of a
        # person a small square.
        marker['shape'] = 'mark' if marker['height'] >= 8 else 'dot'
        markers.append(marker)
    # The bigger groups are the exclamation mark, the smaller ones the dots.
    markers.sort(key=lambda marker: -marker['pixels'])
    return markers


def direction(centre, marker):
    """The direction from the centre to a marker, as (east, south) steps."""
    return marker['x'] - centre[0], marker['y'] - centre[1]


def heading(centre, marker):
    """The heading of a marker.

    Walking at the heading h moves the position by (-sin h, -cos h), and
    the map has east towards the right and south downwards. The heading
    that points at the marker therefore has sin h = -east and cos h = -south.
    """
    east, south = direction(centre, marker)
    return math.atan2(-east, -south)


def nearest(markers, centre=CENTRE, biggest=True):
    """The marker that the driver should walk to.

    The exclamation mark of a quest is the biggest group, and it is the
    thing the driver usually wants; the dots of the creatures are the
    fallback.
    """
    if not markers:
        return None
    if biggest:
        return markers[0]
    return min(markers,
               key=lambda marker: math.hypot(marker['x'] - centre[0],
                                             marker['y'] - centre[1]))


def person_markers(markers):
    """The dots of the people and the creatures around.

    They are drawn as small squares, the mark of a quest as a tall
    exclamation mark.
    """
    return [marker for marker in markers if marker['shape'] == 'dot']
