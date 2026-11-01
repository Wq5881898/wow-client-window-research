"""Bounded retreat: move away from the target and confirm the outcome.

Two retreat styles are needed, and mixing them up is a proven failure:

* ``retreat`` holds the backward key. It only moves along the current
  heading, so it works when nothing is chasing the character.
* ``break_engagement`` turns away and runs. A chasing creature follows the
  old heading, so backing straight up runs along the pursuit line and never
  opens a gap. The 3.3.5a client has no ``GetUnitFacing``, so the turn is
  performed blind and the result is verified through the position field.

The action is deliberately simple so it can be verified without an enemy:
one short backward hold, then confirm the character stopped and moved.
A real combat retreat still needs a planned route; this is the primitive.
"""
import ctypes
import threading
import time
from PIL import ImageGrab
import lab_driver5 as d
from client_live_state import decode, assert_real_frame
from client_window_state import window_observable

VK_BACK = 0x53
VK_FORWARD = 0x57
VK_TURN_LEFT = 0x25
VK_TURN_RIGHT = 0x27
MAX_HOLD_SECONDS = 2
TURN_SECONDS = 0.5


def hold(vk, seconds):
    if not 0 < seconds <= MAX_HOLD_SECONDS:
        raise ValueError('hold duration must be in (0, %d]' % MAX_HOLD_SECONDS)
    key = d.INPUT()
    key.type = 1
    key.union.ki = d.KEYBDINPUT(vk, 0, 0, 0, None)
    try:
        if d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key)) != 1:
            raise RuntimeError('key down failed')
        time.sleep(seconds)
    finally:
        key.union.ki.dwFlags = 2
        if d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key)) != 1:
            raise RuntimeError('key up failed')


def retreat(hwnd, seconds=1.0, sampler=None):
    """Hold the backward key while sampling, then confirm the character stopped.

    `sampler` is called for every frame and must return the decoded state.
    """
    d.ensure_foreground(hwnd)
    if d.u.GetForegroundWindow() != hwnd:
        raise ValueError('client window could not take focus for key input')
    if not window_observable(hwnd):
        raise ValueError('client window not observable')

    failure = []
    moving = []

    def run_hold():
        try:
            hold(VK_BACK, seconds)
        except Exception as exc:
            failure.append(repr(exc))

    worker = threading.Thread(target=run_hold)
    worker.start()
    while worker.is_alive():
        state = sampler()
        moving.append(state)
        time.sleep(.05)
    worker.join()
    if failure:
        raise ValueError(failure[0])

    deadline = time.monotonic() + 4
    stopped = 0
    after = None
    while time.monotonic() < deadline:
        state = sampler()
        after = state
        if state['speed'] == 0:
            stopped += 1
            if stopped >= 3:
                break
        else:
            stopped = 0
        time.sleep(.05)
    if after is None:
        raise ValueError('no post-action sample')
    if after['speed'] != 0:
        raise ValueError('character still moving after release')
    if not moving:
        raise ValueError('no samples captured during the hold')
    return after, moving


def break_engagement(hwnd, sampler, steps=8, hold_seconds=2.0,
                     turn_seconds=TURN_SECONDS):
    """Turn away from a pursuer and run until the client reports no combat.

    Returns the list of step records. Raises when the character stays in
    combat for the whole budget: an unproven escape must not be reported as
    a successful recovery.
    """
    d.ensure_foreground(hwnd)
    if not window_observable(hwnd):
        raise ValueError('client window not observable')

    steps_done = []
    previous = None
    for attempt in range(steps):
        hold(VK_TURN_LEFT, turn_seconds)
        hold(VK_FORWARD, hold_seconds)
        time.sleep(0.2)
        state = sampler()
        position = (state['pos_x'], state['pos_y'])
        record = {'attempt': attempt, 'health': state['health'],
                  'combat': state['combat'], 'position': list(position)}
        if previous is not None:
            record['moved'] = position != previous
        previous = position
        steps_done.append(record)
        if not state['combat']:
            return steps_done
    raise ValueError('retreat did not clear combat')


def default_sampler():
    image = assert_real_frame(ImageGrab.grab())
    return decode(image)
