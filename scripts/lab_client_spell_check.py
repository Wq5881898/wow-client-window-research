"""Report which spells the character knows and the spell of a cast.

The probe recognises a fixed set of spells, so the driver needs to know
which of them the character actually has.
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
SPELLS = [
    (133, 'Fireball'),
    (168, 'Frost Armor'),
    (123, 'Frostbolt'),
    (123, 'Frost Bolt'),
    (116, 'Frost Nova'),
    (120, 'Frost Ward'),
    (122, 'Frost Shock'),
    (113, 'Frost Armor Rank 2'),
    (212, 'Fireball Rank 2'),
]


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


def send(hwnd, text, settle=0.6):
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.4)
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.04)
    time.sleep(0.2)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(settle)


def hold_key(vk, seconds):
    import ctypes
    key = d.INPUT()
    key.type = 1
    key.union.ki = d.KEYBDINPUT(vk, 0, 0, 0, None)
    try:
        d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key))
        time.sleep(seconds)
    finally:
        key.union.ki.dwFlags = 2
        d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key))


def main():
    run = 'client_spell_check_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', checks=[])
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        # A spell can only be tested with a target in view, so the character
        # walks around until a hostile shows up.
        state = None
        for _ in range(14):
            d.post_key(hwnd, win32con.VK_TAB)
            time.sleep(0.6)
            candidate = reader()
            if candidate['target_exists'] and candidate['target_attackable']:
                state = candidate
                break
            # Walk on and turn, so a new creature comes into view.
            hold_key(0x57, 1.6)
            hold_key(0x25, 0.35)
        if state is None:
            raise ValueError('no hostile in view')
        result['target'] = {'guid': state['target_guid'],
                            'health': state['target_health']}

        for spell_id, name in SPELLS:
            before = reader()
            send(hwnd, '/cast ' + name, settle=2.2)
            after = reader()
            check = {'spell': name, 'id': spell_id,
                     'cast_started_before': before['cast_started'],
                     'cast_started_after': after['cast_started'],
                     'cast_succeeded': after['cast_succeeded'],
                     'cast_failed': after['cast_failed'],
                     'error_reason': after['last_error_reason']}
            check['castable'] = (after['cast_started'] != before['cast_started'])
            result['checks'].append(check)
        result['status'] = 'CHECKED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('01-end')
        path = evidence.write(result)
        d.log('spell check run', path, result['status'])
    return 0 if result['status'] == 'CHECKED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
