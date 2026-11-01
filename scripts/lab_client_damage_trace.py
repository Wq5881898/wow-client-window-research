"""Diagnose why the health of the bound target rose during the fight.

One cast is issued and the target is sampled densely afterwards. The guid,
the health, the death flag and the combat flag together show whether the
rise was a regeneration, a respawn or a different creature.
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
FIREBALL = 133


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


def send(hwnd, text, settle=0.4):
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.4)
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.05)
    time.sleep(0.2)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(settle)


def main():
    run = 'client_damage_trace_' + str(time.time_ns())
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

        # Select a hostile with the tab key.
        state = None
        for _ in range(6):
            d.post_key(hwnd, win32con.VK_TAB)
            time.sleep(0.6)
            candidate = reader()
            if candidate['target_exists'] and candidate['target_attackable']:
                state = candidate
                break
        if state is None:
            raise ValueError('no hostile in view')
        result['target'] = {'guid': state['target_guid'],
                            'health': state['target_health'],
                            'range': state['spell_range']}
        evidence.capture('01-target', state)

        send(hwnd, '/cast Fireball', settle=0.0)
        started = time.monotonic()
        while time.monotonic() - started < 12:
            state = reader()
            result['samples'].append({
                'elapsed': round(time.monotonic() - started, 2),
                'guid': state['target_guid'],
                'health': state['target_health'],
                'max_health': state['target_max_health'],
                'dead': state['target_dead'],
                'exists': state['target_exists'],
                'combat': state['combat'],
                'cast_succeeded': state['cast_succeeded'],
                'cast_failed': state['cast_failed'],
            })
            time.sleep(0.25)
        result['status'] = 'TRACED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('02-end')
        path = evidence.write(result)
        d.log('damage trace run', path, result['status'])
    return 0 if result['status'] == 'TRACED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
