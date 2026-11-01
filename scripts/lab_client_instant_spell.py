"""Test whether an instant spell can hold a target down.

A creature that leaves combat regenerates quickly, so a slow spell can never
finish it. An instant spell has no cast time, so the driver can keep the
pressure on. This measures the gap between two instant casts and the health
of the target over the sequence.
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
SPELL = 'Frostbolt'
WALK = 0x57
TURN = 0x25


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
        d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key))
        time.sleep(seconds)
    finally:
        key.union.ki.dwFlags = 2
        d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key))


def cast(hwnd):
    """Type a cast command without waiting for the client."""
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.15)
    for character in '/cast ' + SPELL:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.02)
    d.post_key(hwnd, win32con.VK_RETURN)


def main():
    run = 'client_instant_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', samples=[])
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        # Find a hostile that is worth testing against.
        state = None
        for _ in range(16):
            d.post_key(hwnd, win32con.VK_TAB)
            time.sleep(0.6)
            candidate = reader()
            if candidate['target_exists'] and candidate['target_attackable']:
                state = candidate
                break
            hold(WALK, 1.6)
            hold(TURN, 0.35)
        if state is None:
            raise ValueError('no hostile in view')
        result['target'] = {'guid': state['target_guid'],
                            'health': state['target_health'],
                            'range': state['spell_range']}
        evidence.capture('01-target', state)

        # One cast proves whether the spell exists at all.
        before = reader()
        cast(hwnd)
        time.sleep(1.5)
        after = reader()
        result['first_cast'] = {
            'cast_started_before': before['cast_started'],
            'cast_started_after': after['cast_started'],
            'cast_succeeded': after['cast_succeeded'],
            'cast_failed': after['cast_failed'],
            'error_reason': after['last_error_reason'],
        }
        result['spell_usable'] = (after['cast_started'] != before['cast_started'])
        if not result['spell_usable']:
            raise ValueError('the spell cannot be cast')
        evidence.capture('02-first-cast', after)

        # Now a burst: cast as fast as the client accepts it and watch the
        # health of the target.
        started = time.monotonic()
        while time.monotonic() - started < 14:
            cast(hwnd)
            time.sleep(0.25)
            state = reader()
            result['samples'].append({
                'elapsed': round(time.monotonic() - started, 2),
                'health': state['target_health'],
                'guid': state['target_guid'],
                'dead': state['target_dead'],
                'combat': state['combat'],
                'cast_succeeded': state['cast_succeeded'],
                'cast_failed': state['cast_failed'],
            })
            if state['target_dead'] or not state['target_exists']:
                break
        evidence.capture('03-burst', state)
        result['status'] = 'MEASURED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('04-end')
        path = evidence.write(result)
        d.log('instant spell run', path, result['status'])
    return 0 if result['status'] == 'MEASURED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
