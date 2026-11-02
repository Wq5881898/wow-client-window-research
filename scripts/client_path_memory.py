"""The path the character actually walked.

The client of 3.3.5a cannot report the position of the character in world
coordinates: ``GetUnitPosition`` does not exist there, so the navmesh of the
server is not reachable from this route. What the client can offer is the
path it really walked, and the server accepts every step of it. That path is
the feasible path of this route, and its length is the distance that can be
compared between two runs.

The points are the normalised map coordinates of the zone, the same values
the probe reports.
"""
import math


class PathMemory:
    """The waypoints of a walked path."""

    def __init__(self, min_step=0.002):
        self.min_step = min_step
        self.points = []

    def record(self, x, y):
        """Add a point when it is far enough from the last one."""
        if not self.points:
            self.points.append((float(x), float(y)))
            return True
        if math.dist(self.points[-1], (x, y)) >= self.min_step:
            self.points.append((float(x), float(y)))
            return True
        return False

    def length(self):
        """The length of the whole path."""
        return sum(math.dist(a, b)
                   for a, b in zip(self.points, self.points[1:]))

    def nearest_index(self, x, y):
        """The index of the recorded point closest to the given one."""
        if not self.points:
            return None
        return min(range(len(self.points)),
                   key=lambda i: math.dist(self.points[i], (x, y)))

    def route_back(self, x, y):
        """The waypoints from the point nearest to (x, y) back to the start.

        The start of the path is the place where the ghost appeared, which
        is the graveyard. Following the path backwards therefore leads from
        the corpse to the graveyard without cutting a corner.
        """
        if not self.points:
            return []
        index = self.nearest_index(x, y)
        return list(reversed(self.points[:index + 1]))

    def chunks(self, route, max_length=0.012):
        """Split a route into pieces that are not longer than max_length.

        The server answers every movement request on its own, so a long leg
        is split into shorter ones to keep the control over the walk.
        """
        if not route:
            return []
        pieces = []
        current = [route[0]]
        length = 0.0
        for point in route[1:]:
            length += math.dist(current[-1], point)
            current.append(point)
            if length >= max_length:
                pieces.append(current)
                current = [point]
                length = 0.0
        if len(current) > 1:
            pieces.append(current)
        return pieces
