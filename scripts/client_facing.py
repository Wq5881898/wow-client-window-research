"""Turn the character toward the current target without a facing readout.

3.3.5a has no ``GetUnitFacing``, so the driver cannot ask where the
character is looking. The client does answer the question indirectly: a
spell on a target that is not in front fails and prints an error. The
client reports that failure as the range reason, because its range check
includes the cone in front of the character, so the driver watches the
failure itself rather than one specific reason code.

The loop is therefore: cast, and while the cast keeps failing, turn a small
step and cast again. The first successful cast proves the target came into
view.
"""
import ctypes
import time
import win32con
import win32gui
import lab_driver5 as d

VK_LEFT = 0x25
VK_RIGHT = 0x27
# The turn rate was measured at roughly 170 degrees per second, so a step of
# about ten degrees keeps the search from stepping over the target.
TURN_STEP_SECONDS = 0.06

# Failure reasons that a turn cannot fix.
NON_TURNABLE_REASONS = (2, 3)   # mana and cooldown


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


def cast_outcome(state, before):
    """Classify one cast attempt against the counters read before it.

    The probe reports cumulative counters, so the delta decides whether the
    attempt itself succeeded. Returns 'success', 'failure' or 'unknown'.
    """
    failed = state.get('cast_failed', 0) - before.get('cast_failed', 0)
    succeeded = state.get('cast_succeeded', 0) - before.get('cast_succeeded', 0)
    if succeeded > 0:
        return 'success'
    if failed > 0:
        return 'failure'
    return 'unknown'


class CastProbe:
    """Casts a spell and reports whether the attempt succeeded."""

    def __init__(self, cast, reader, spell_id=133, settle=0.8):
        self.cast = cast
        self.reader = reader
        self.spell_id = spell_id
        self.settle = settle

    def counters(self):
        state = self.reader()
        return {'cast_failed': state.get('cast_failed', 0),
                'cast_succeeded': state.get('cast_succeeded', 0),
                'last_error_reason': state.get('last_error_reason', 0),
                'event_serial': state.get('event_serial', 0),
                'events': state.get('events') or []}

    def attempt(self):
        state = self.cast()
        # The cast is asynchronous, so the outcome of the attempt may only
        # be visible a moment later.
        time.sleep(self.settle)
        return self.reader()


def sweep_toward(cast, max_steps=40, direction='left'):
    """Turn in small steps until a cast succeeds.

    `cast` is a CastProbe. The loop stops at the first attempt that produced
    a successful cast event for the bound spell. Returns the number of steps
    used and the last observed state.
    """
    before = cast.counters()
    state = cast.attempt()
    steps = 0
    while steps < max_steps:
        if cast_outcome(state, before) == 'success':
            break
        if state.get('last_error_reason') in NON_TURNABLE_REASONS:
            break
        turn_step(direction)
        steps += 1
        before = cast.counters()
        state = cast.attempt()
    return steps, state
