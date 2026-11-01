"""Turn the character toward the current target without a facing readout.

3.3.5a has no ``GetUnitFacing``, so the driver cannot ask where the
character is looking. The client does answer the question indirectly: a
spell on a target that is not in front fails with the UI error
"Target needs to be in front of you.", which the probe reports as reason
code 5. That error is the feedback signal for a turn-and-retry loop.
"""
import ctypes
import time
import win32con
import win32gui
import lab_driver5 as d

VK_LEFT = 0x25
VK_RIGHT = 0x27
TURN_STEP_SECONDS = 0.12


REASON_FACING = 5


def hold(vk, seconds):
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


def turn_step(direction='left', seconds=TURN_STEP_SECONDS):
    """Turn the character by one small step."""
    vk = VK_LEFT if direction == 'left' else VK_RIGHT
    hold(vk, seconds)


def facing_failed(state):
    """True when the newest UI error says the target was not in front.

    The probe keeps the reason of the newest UI error in a dedicated field,
    because the general last_reason is overwritten by every spell event.
    """
    return state.get('last_error_reason') == REASON_FACING


def sweep_toward(cast, max_steps=40, direction='left'):
    """Turn in small steps until the cast stops failing on facing.

    `cast` performs one cast attempt and returns the decoded state. The
    probe reports the reason of the newest UI error, so the sweep watches
    that field after every attempt. Returns the number of steps used and
    the last observed state.
    """
    state = cast()
    steps = 0
    while facing_failed(state) and steps < max_steps:
        turn_step(direction)
        steps += 1
        state = cast()
    return steps, state
