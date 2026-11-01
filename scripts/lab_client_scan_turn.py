"""Find a hostile creature by turning around and trying the tab key.

The tab key only selects a creature that is in front of the character, and
the client has no facing readout, so the character is turned in steps until
something is selected.
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
from client_chat_guard import ensure_chat_closed, ensure_focus, close_world_map

ROOT = Path(__file__).resolve().parents[1]
TURN_LEFT = 0x25
TURN_RIGHT = 0x27


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


def hold(vk, seconds, hwnd=None):
    import ctypes
    if hwnd is not None:
        ensure_focus(hwnd)
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
    run = 'client_scan_turn_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', picks=[])
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        close_world_map(hwnd, reader)
        found = None
        for step in range(24):
            ensure_chat_closed(hwnd, reader)
            d.post_key(hwnd, win32con.VK_TAB)
            time.sleep(0.6)
            state = reader()
            pick = {'step': step, 'guid': state['target_guid'],
                    'health': state['target_health'],
                    'class_id': state.get('target_class'),
                    'class': state.get('target_class_name'),
                    'range': state['spell_range'],
                    'exists': state['target_exists']}
            result['picks'].append(pick)
            if state['target_exists'] and state['target_attackable']:
                found = pick
                evidence.capture('01-picked', state)
                break
            # Turn a quarter and look again.
            hold(TURN_LEFT, 0.35, hwnd)
        result['target'] = found
        result['status'] = 'SCANNED' if found else 'NOTHING_FOUND'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('02-end')
        path = evidence.write(result)
        d.log('scan turn run', path, result['status'])
    return 0 if result['status'] == 'SCANNED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
