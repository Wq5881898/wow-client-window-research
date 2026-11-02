"""Walk the character to a place given in the coordinates of the zone.

The heading of the client and the map coordinates were measured, so the
walk is a closed loop: turn towards the place, walk a little, look where
the character is now and turn again.
"""
import argparse
import ctypes
import json
import math
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
from client_evidence import Evidence
from client_read_fresh import read_or_dismiss
from client_danger_recovery import bearing_to, wrap

ROOT = Path(__file__).resolve().parents[1]
VK_FORWARD = 0x57
VK_LEFT = 0x25
VK_RIGHT = 0x27
TURN_RATE = math.pi


def hide_consoles():
    def cb(hwnd, _):
        try:
            cls = win32gui.GetClassName(hwnd)
            title = win32gui.GetWindowText(hwnd)
        except Exception:
            return True
        if cls == 'ConsoleWindowClass' or 'python.exe' in title.lower():
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            except Exception:
                pass
        return True
    win32gui.EnumWindows(cb, None)


def hold(vk, seconds, hwnd):
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--x', type=float, required=True)
    parser.add_argument('--y', type=float, required=True)
    parser.add_argument('--tolerance', type=float, default=0.004)
    parser.add_argument('--timeout', type=float, default=120.0)
    args = parser.parse_args()
    run = 'client_walk_to_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', target=[args.x, args.y], steps=[])
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return read_or_dismiss(
                lambda: decode(assert_real_frame(grab_desktop())),
                d.game_window())

        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            hwnd = d.game_window()
            state = reader()
            distance = math.hypot(args.x - state['pos_x'], args.y - state['pos_y'])
            result['steps'].append({'distance': distance,
                                    'position': [state['pos_x'], state['pos_y']],
                                    'facing': state['facing']})
            if distance <= args.tolerance:
                result['status'] = 'ARRIVED'
                result['final_distance'] = distance
                evidence.capture('01-arrived', state)
                break
            error = wrap(bearing_to(state, (args.x, args.y)) - state['facing'])
            if abs(error) > 0.10:
                seconds = min(1.1, max(0.06, abs(error) / TURN_RATE))
                hold(VK_LEFT if error > 0 else VK_RIGHT, seconds, hwnd)
            else:
                hold(VK_FORWARD, 0.8, hwnd)
        else:
            result['status'] = 'TIMEOUT'
            result['final_distance'] = result['steps'][-1]['distance']
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('09-end')
        path = evidence.write(result)
        d.log('walk to', str(path), result['status'])
    return 0 if result['status'] == 'ARRIVED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
