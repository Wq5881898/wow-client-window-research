"""The walking primitives of the driver, with the way around obstacles.

The character walks into a rock and stays there. The walk then has to turn
away from the target and follow the obstacle, keeping the same side until the
character moves again, so that a wall is slid along instead of approached
from both sides.
"""
import ctypes
import math
import time

import lab_driver5 as d
from client_obstacle import Obstacle, wanted_heading
from client_danger_recovery import bearing_to, wrap

VK_FORWARD = 0x57
VK_BACKWARD = 0x53
VK_LEFT = 0x25
VK_RIGHT = 0x27

# The client turns with pi radians per second.
TURN_RATE = math.pi
# A movement of the character counts as real above this.
MOVED = 0.0006


def hold(vk, seconds, hwnd=None):
    """Hold a key down for a while.

    The keyboard input of the system goes to the foreground window, so the
    client has to be in front before the key is pressed.
    """
    if hwnd is not None:
        try:
            d.ensure_foreground(hwnd)
        except Exception:
            pass
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
    """Walk towards a place. Returns the distance that is left.

    When the character does not move at all, the walk turns away from the
    target and follows the obstacle. The detour keeps its side until the
    character moves again, so the character slides along a wall instead of
    oscillating between two directions.
    """
    deadline = time.monotonic() + timeout
    distance = None
    obstacle = Obstacle()
    while time.monotonic() < deadline:
        state = reader()
        distance = math.hypot(target[0] - state['pos_x'],
                              target[1] - state['pos_y'])
        if trace is not None:
            trace.append({'distance': distance,
                          'position': [state['pos_x'], state['pos_y']],
                          'facing': state['facing'],
                          'detour': obstacle.detour})
        if distance <= tolerance:
            return distance
        before = (state['pos_x'], state['pos_y'])
        error = wrap(wanted_heading(state, target, obstacle.detour)
                     - state['facing'])
        if abs(error) > 0.10:
            seconds = min(1.1, max(0.06, abs(error) / TURN_RATE))
            hold(VK_LEFT if error > 0 else VK_RIGHT, seconds, hwnd)
        else:
            # The reading of the telemetry costs about as much time as the
            # walk, so a long way is covered with longer steps.
            hold(VK_FORWARD, min(2.0, max(0.5, distance * 6.0)), hwnd)
        after = reader()
        moved = math.hypot(after['pos_x'] - before[0],
                            after['pos_y'] - before[1])
        obstacle.note(moved)
    return distance
