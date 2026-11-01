"""Bounded retreat: move away from the target and confirm the outcome.

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
MAX_HOLD_SECONDS = 2


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


def default_sampler():
    image = assert_real_frame(ImageGrab.grab())
    return decode(image)
