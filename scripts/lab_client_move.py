"""Bounded movement primitive: one short hold, then confirm the stop.

Sampling continues while the key is held, so the heartbeat never sees a gap.
Requires protocol 3 telemetry so position and facing confirm the result.
Rejects any run that starts in combat, dead, or with a live target.
"""
import ctypes
import json
import threading
import traceback
import time
from pathlib import Path
from PIL import ImageGrab
import lab_driver5 as d
from client_live_state import decode, assert_real_frame
from client_control_guard import ControlGuard
from client_window_state import window_observable

ROOT = Path(__file__).resolve().parents[1]
VK = {'forward': 0x57, 'back': 0x53, 'left': 0x41, 'right': 0x44}


def hold(vk, seconds):
    """Press and release a key; duration must stay inside the safe bound."""
    if not 0 < seconds <= 2:
        raise ValueError('hold duration must be in (0, 2]')
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


def displacement(before, after):
    dx = after['pos_x'] - before['pos_x']
    dy = after['pos_y'] - before['pos_y']
    return (dx * dx + dy * dy) ** 0.5


def facing_delta(before, after):
    diff = abs(after['facing'] - before['facing']) % (2 * 3.141592653589793)
    return min(diff, 2 * 3.141592653589793 - diff)


def main():
    run = 'client_move_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', samples=[])
    hwnd = d.find_game_window()
    holder = None
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        if d.u.GetForegroundWindow() != hwnd:
            raise ValueError('client window could not take focus for key input')
        guard = ControlGuard()
        frames = []

        def sample():
            image = assert_real_frame(ImageGrab.grab())
            state = decode(image)
            decision = guard.observe(state, time.monotonic(),
                                     window_observable(hwnd))
            frames.append(dict(host_monotonic=time.monotonic(),
                               control=decision, **state))
            return state, decision

        before, decision = sample()
        if decision['decision'] == 'RECOVERY_REQUIRED':
            raise ValueError(decision['reason'])
        if before['protocol'] != 3:
            raise ValueError('protocol 3 telemetry required')
        if before['combat'] or before['dead'] or before['target_exists']:
            raise ValueError('combat, dead or targeted baseline rejected')
        if before['speed'] != 0:
            raise ValueError('baseline not stationary')

        failure = []

        def run_hold():
            try:
                hold(VK['back'], 1.0)
            except Exception as exc:
                failure.append(repr(exc))

        holder = threading.Thread(target=run_hold)
        holder.start()
        moving = []
        while holder.is_alive():
            state, decision = sample()
            moving.append(state)
            time.sleep(.05)
        holder.join()
        if failure:
            raise ValueError(failure[0])
        # Keep sampling until the character is confirmed stopped; a fixed sleep
        # would outrun the heartbeat timeout and look like a lost session.
        deadline = time.monotonic() + 4
        stopped = 0
        after = None
        while time.monotonic() < deadline:
            state, decision = sample()
            if decision['decision'] == 'RECOVERY_REQUIRED':
                raise ValueError(decision['reason'])
            after = state
            if state['speed'] == 0:
                stopped += 1
                if stopped >= 3:
                    break
            else:
                stopped = 0
            time.sleep(.05)
        if not moving:
            raise ValueError('no samples captured during the hold')
        if not any(state['speed'] > 0 for state in moving):
            raise ValueError('movement never observed in telemetry')
        moved = displacement(before, after)
        if moved <= 1e-6:
            raise ValueError('no displacement after bounded hold')
        if after['speed'] != 0:
            raise ValueError('character still moving after release')

        result['before'] = before
        result['after'] = after
        result['displacement'] = moved
        result['facing_delta'] = facing_delta(before, after)
        result['moving_samples'] = len(moving)
        result['status'] = 'BOUNDED_MOVE_VERIFIED'
    except Exception as exc:
        result['error'] = repr(exc)
        result['traceback'] = traceback.format_exc()
    finally:
        result['samples'] = frames
        rows = frames
        result['max_capture_gap_seconds'] = max(
            (b['host_monotonic'] - a['host_monotonic'] for a, b in zip(rows, rows[1:])),
            default=0)
        path = ROOT / 'results' / (run + '.json')
        with path.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)
    return 0 if result['status'] == 'BOUNDED_MOVE_VERIFIED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
