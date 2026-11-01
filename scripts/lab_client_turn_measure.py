"""Measure whether a turn key really rotates the character.

The client has no facing readout, so the turn is measured through the
displacement of a short forward walk: the vector before and after the turn
must differ.
"""
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

ROOT = Path(__file__).resolve().parents[1]
VK_FORWARD = 0x57
VK_LEFT = 0x25
VK_RIGHT = 0x27


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


def hold(vk, seconds):
    import ctypes
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


def main():
    run = 'client_turn_measure_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', legs=[])
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        def walk(label, seconds=1.0):
            before = reader()
            hold(VK_FORWARD, seconds)
            time.sleep(0.4)
            after = reader()
            dx = after['pos_x'] - before['pos_x']
            dy = after['pos_y'] - before['pos_y']
            leg = {'label': label, 'dx': dx, 'dy': dy,
                   'distance': math.hypot(dx, dy),
                   'angle': math.degrees(math.atan2(dy, dx))}
            result['legs'].append(leg)
            return leg

        first = walk('before-turn')
        evidence.capture('01-before')

        # Try the arrow keys with several durations.
        for seconds in (0.3, 0.8, 1.5):
            hold(VK_LEFT, seconds)
            time.sleep(0.3)
            leg = walk('after-left-%.1f' % seconds)
            result['legs'][-1]['turn_seconds'] = seconds
        evidence.capture('02-after-left')

        # Compare the heading of the first and the last walk.
        if len(result['legs']) >= 2:
            delta = abs(result['legs'][0]['angle'] - result['legs'][-1]['angle'])
            delta = min(delta, 360 - delta)
            result['heading_change_degrees'] = delta
            result['turn_worked'] = delta > 20

        if not result.get('turn_worked'):
            raise ValueError('the turn key did not change the heading')
        result['status'] = 'TURN_MEASURED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('turn measure run', path, result['status'])
    return 0 if result['status'] == 'TURN_MEASURED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
