"""The walking primitives of the driver, with the way around obstacles.

The character walks into a rock and stays there. The walk then has to turn
away from the target and follow the obstacle, keeping the same side until
the character moves again, so that a wall is slid along instead of approached
from both sides.

Three rules keep the way out of an obstacle honest:

* a turn is not a collision. Only a step that was meant to move the
  character forward and did not move it counts as being blocked, otherwise
  the walk gives up while the character is only turning towards the target;
* the state of the obstacle has one owner. The number of the blocked steps
  and the side of the detour live in the primitive, so the walk and the
  primitive cannot count the same step twice;
* a walk that does not come closer ends with a reason. A walk that is
  blocked forever must not look like a walk that is on its way.
"""
import ctypes
import math
import time

import lab_driver5 as d
from client_obstacle import Obstacle
from client_danger_recovery import wrap

VK_FORWARD = 0x57
VK_BACKWARD = 0x53
VK_LEFT = 0x25
VK_RIGHT = 0x27

# The client turns with pi radians per second.
TURN_RATE = math.pi
# A movement of the character counts as real above this.
MOVED = 0.0006
# How often the character may be blocked on one side of an obstacle before
# the other side is tried.
STUCK_LIMIT = 6
# After this many steps without any movement the character walks backwards,
# which is the way out of a rock it stands in.
BACKWARD_AFTER = 4
# How many steps may pass without the character coming closer before the
# walk is given up.
NO_PROGRESS_LIMIT = 12


class FocusLost(RuntimeError):
    """The client window could not be brought to the front.

    The keyboard input of the system goes to the foreground window, so a
    key that is sent while the client is in the back reaches another
    program. The walk has to stop instead.
    """


class WalkResult:
    """The outcome of a walk towards a place.

    The result says whether the character arrived, how often it was
    blocked, how far it came and why the walk ended. A walk that did not
    arrive is not a failure of the walk itself: the report has to show that
    the character could not move.
    """

    def __init__(self, distance=None, arrived=False, blocked=0, steps=0,
                 traveled=0.0, reason=None):
        self.distance = distance
        self.arrived = arrived
        self.blocked = blocked
        self.steps = steps
        self.traveled = traveled
        self.reason = reason

    def __repr__(self):
        return ('WalkResult(distance=%s, arrived=%s, blocked=%s, steps=%s, '
                'reason=%s)' % (self.distance, self.arrived, self.blocked,
                                 self.steps, self.reason))


def hold(vk, seconds, hwnd=None):
    """Hold a key down for a while.

    The keyboard input of the system goes to the foreground window, so the
    client has to be in front before the key is pressed.
    """
    if hwnd is not None:
        try:
            d.ensure_foreground(hwnd)
        except Exception as exc:
            raise FocusLost('the client window could not take the focus: '
                            + repr(exc))
    key = d.INPUT()
    key.type = 1
    key.union.ki = d.KEYBDINPUT(vk, 0, 0, 0, None)
    if d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key)) != 1:
        raise RuntimeError('the key could not be sent')
    try:
        time.sleep(seconds)
    finally:
        key.union.ki.dwFlags = 2
        d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key))


def walk_heading(hwnd, reader, heading, seconds=60.0, stop=None, trace=None):
    """Walk in a fixed direction until the stop function says so.

    The heading of the client is kept, so the character walks straight even
    when the ground is not level. The function returns whether the stop was
    reached and the state of the last reading.
    """
    deadline = time.monotonic() + seconds
    state = reader()
    while time.monotonic() < deadline:
        state = reader()
        error = wrap(heading - state['facing'])
        if abs(error) > 0.10:
            hold(VK_LEFT if error > 0 else VK_RIGHT,
                 min(1.1, max(0.06, abs(error) / TURN_RATE)), hwnd)
            continue
        hold(VK_FORWARD, 1.2, hwnd)
        state = reader()
        if trace is not None:
            trace.append({'position': [state['pos_x'], state['pos_y']],
                          'facing': state['facing']})
        if stop is not None and stop(state):
            return True, state
    return False, state


def walk_to(hwnd, reader, target, tolerance=0.004, timeout=120.0, trace=None):
    """Walk towards a place.

    When the character does not move at all, it is standing in front of an
    obstacle. The walk then keeps a direction of the world and moves along
    the obstacle, and the aim at the target comes back as soon as the
    character moves again. An angle towards the target would make the
    character walk on a circle around it.

    The result says whether the character arrived and why the walk ended.
    """
    deadline = time.monotonic() + timeout
    distance = None
    obstacle = Obstacle(tries=STUCK_LIMIT)
    slide = None
    best = None
    steps = 0
    without_progress = 0
    reason = None
    while time.monotonic() < deadline:
        state = reader()
        distance = math.hypot(target[0] - state['pos_x'],
                              target[1] - state['pos_y'])
        if trace is not None:
            trace.append({'distance': distance,
                           'position': [state['pos_x'], state['pos_y']],
                           'facing': state['facing'],
                           'slide': slide})
        if distance <= tolerance:
            return WalkResult(distance=distance, arrived=True,
                              blocked=obstacle.blocked, steps=steps,
                              traveled=obstacle.traveled)
        if best is None or distance < best - 0.0005:
            best = distance
            without_progress = 0
        else:
            without_progress += 1
            if without_progress >= NO_PROGRESS_LIMIT:
                # The character does not come closer. The walk is given up
                # with a reason, so the report does not look like a walk
                # that is still on its way.
                return WalkResult(distance=distance, arrived=False,
                                  blocked=obstacle.blocked, steps=steps,
                                  traveled=obstacle.traveled,
                                  reason='no_progress')
        before = (state['pos_x'], state['pos_y'])
        if slide is not None:
            wanted = slide
        else:
            wanted = math.atan2(-(target[0] - state['pos_x']),
                                -(target[1] - state['pos_y']))
        error = wrap(wanted - state['facing'])
        turned = False
        try:
            if abs(error) > 0.10:
                seconds = min(1.1, max(0.06, abs(error) / TURN_RATE))
                hold(VK_LEFT if error > 0 else VK_RIGHT, seconds, hwnd)
                turned = True
            else:
                # The reading of the telemetry costs about as much time as
                # the walk, so a long way is covered with longer steps.
                hold(VK_FORWARD, min(2.0, max(0.5, distance * 6.0)), hwnd)
        except FocusLost as exc:
            return WalkResult(distance=distance, arrived=False,
                              blocked=obstacle.blocked, steps=steps,
                              traveled=obstacle.traveled, reason='no_focus')
        after = reader()
        steps += 1
        moved = math.hypot(after['pos_x'] - before[0],
                           after['pos_y'] - before[1])
        if turned:
            # A turn is not a collision. The character did not stand in
            # front of a rock, it only looked the other way.
            obstacle.turned()
            continue
        obstacle.note(moved)
        if moved < MOVED:
            # The character does not move towards the target, so it slides
            # along the obstacle.
            towards = math.atan2(-(target[0] - after['pos_x']),
                                 -(target[1] - after['pos_y']))
            slide = obstacle.slide_heading(towards)
            if obstacle.hits == BACKWARD_AFTER:
                # The character does not move at all. Walking backwards is
                # the way out of a rock the character stands in.
                hold(VK_BACKWARD, 1.0, hwnd)
        else:
            slide = None
    return WalkResult(distance=distance, arrived=False,
                      blocked=obstacle.blocked, steps=steps,
                      traveled=obstacle.traveled, reason=reason)
