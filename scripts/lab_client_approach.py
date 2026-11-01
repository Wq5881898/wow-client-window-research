"""Close the distance to the selected target.

Selecting a unit with the tab key turns the character towards it, so a
repeated tab and forward walk brings the character into spell range without
needing a facing readout.
"""
import json
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
VK_TURN_LEFT = 0x25


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
    run = 'client_approach_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', steps=[])
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        for step in range(16):
            d.post_key(hwnd, win32con.VK_TAB)
            time.sleep(0.5)
            state = reader()
            if not state['target_exists'] or not state['target_attackable']:
                result['steps'].append({'step': step, 'error': 'no target'})
                hold(VK_FORWARD, 1.5)
                continue
            # Walk a short leg and turn, so an obstacle does not trap the
            # character and the next tab selects another creature.
            hold(VK_FORWARD, 0.8)
            time.sleep(0.2)
            hold(VK_TURN_LEFT, 0.5)
            hold(VK_FORWARD, 0.6)
            time.sleep(0.3)
            after = reader()
            record = {'step': step, 'health': after['target_health'],
                      'range': after['spell_range'],
                      'distance': after.get('target_distance'),
                      'position': [after['pos_x'], after['pos_y']]}
            result['steps'].append(record)
            if after['spell_range'] == 1 and after['target_health'] > 1:
                evidence.capture('01-in-range', after)
                result['status'] = 'IN_RANGE'
                result['target'] = {'guid': after['target_guid'],
                                    'health': after['target_health']}
                break
        if result['status'] != 'IN_RANGE':
            raise ValueError('the target could not be reached')
        result['final'] = reader()
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('02-end')
        path = evidence.write(result)
        d.log('approach run', path, result['status'])
    return 0 if result['status'] == 'IN_RANGE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
