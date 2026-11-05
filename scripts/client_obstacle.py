"""Walk around obstacles.

The character walks into a rock or a wall and stays there: the position
does not change at all, no matter which way it faces. A walk that only aims
at the target then burns its whole budget without moving, and the task ends
without a verdict. This happened on the way back to the place of birth, where
the character was wedged in a corner of Elwynn Forest and every direction
gave a step of zero.

The way out is to slide along the obstacle. The character turns away from
the target by a fixed angle and walks; the angle keeps its sign while the
character is stuck, so the character follows the wall instead of
oscillating between two directions. As soon as the character moves again,
the aim goes back to the target.
"""
import math


class Obstacle:
    """The state of the way around an obstacle.

    The detour is kept in one direction until the character moved again, so
    that a wall is followed instead of being approached from both sides.
    """

    def __init__(self, threshold=0.0006, angle=math.pi / 2, tries=3):
        self.threshold = threshold
        self.angle = angle
        self.tries = tries
        self.side = 1
        self.hits = 0
        self.detour = 0.0

    def note(self, moved):
        """Report how far the character moved and return the detour to use.

        A detour of zero means that the character is on its way to the
        target.
        """
        if moved >= self.threshold:
            self.hits = 0
            self.detour = 0.0
            return 0.0
        self.hits += 1
        if self.hits > self.tries:
            # The other side of the obstacle may be the way out.
            self.side = -self.side
            self.hits = 0
        self.detour = self.side * self.angle
        return self.detour

    @property
    def stuck(self):
        """True while the character did not move."""
        return self.detour != 0.0


def wanted_heading(state, target, detour=0.0):
    """The heading of the target, turned away by the detour.

    The heading of the client grows counter clockwise from the north, so a
    positive detour turns the character to the left.
    """
    from client_danger_recovery import bearing_to
    return bearing_to(state, target) + detour


def detour_heading(state, target, detour):
    """The error of the heading to walk to.

    The error is the difference between the wanted heading and the heading of
    the character, brought into the range of minus pi to plus pi. A positive
    error means that the character has to turn to the left.
    """
    from client_danger_recovery import wrap
    return wrap(wanted_heading(state, target, detour) - state['facing'])


def detour_of(state, target, detour):
    """The heading error of a walk that is turned away from the target.

    The error of the plain heading tells which way the character has to
    turn to reach the target. The detour is added to the wanted heading, so
    the character walks along the obstacle instead of into it.
    """
    from client_danger_recovery import wrap
    plain = wrap(wanted_heading(state, target, 0.0) - state['facing'])
    return wrap(plain + detour)
