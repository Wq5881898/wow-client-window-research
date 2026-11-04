"""Walk the character to a place in the zone.

The heading of the client and the map coordinates were measured, so the walk
is a closed loop: turn towards the place, walk a little, look where the
character is now and turn again.
"""
import ctypes
import math
import time

import lab_driver5 as d
from client_danger_recovery import bearing_to, wrap

VK_FORWARD = 0x57
VK_LEFT = 0x25
VK_RIGHT = 0x27
TURN_RATE = math.pi


def hold(vk, seconds, hwnd):
    """Hold a key down for a while with the client in the foreground."""
    d.ensure_foreground(hwnd)
    key = d.INPUT()
    key.type = 1
    key.union.ki = d.KEYBDINPUT(vk, 0, 0, 0, None)
    d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key))
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
    """Walk towards a place. Returns the distance that is left."""
    deadline = time.monotonic() + timeout
    distance = None
    while time.monotonic() < deadline:
        state = reader()
        distance = math.hypot(target[0] - state['pos_x'],
                              target[1] - state['pos_y'])
        if trace is not None:
            trace.append({'distance': distance,
                          'position': [state['pos_x'], state['pos_y']],
                          'facing': state['facing']})
        if distance <= tolerance:
            return distance
        error = wrap(bearing_to(state, target) - state['facing'])
        if abs(error) > 0.10:
            seconds = min(1.1, max(0.06, abs(error) / TURN_RATE))
            hold(VK_LEFT if error > 0 else VK_RIGHT, seconds, hwnd)
        else:
            # The reading of the telemetry costs about as much time as the
            # walk, so a long way is covered with longer steps.
            hold(VK_FORWARD, min(2.0, max(0.5, distance * 6.0)), hwnd)
    return distance
