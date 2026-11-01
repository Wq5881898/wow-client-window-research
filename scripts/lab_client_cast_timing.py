"""Measure how long a fireball cast takes to resolve.

The sweep reads the outcome after every attempt, so the wait has to be long
enough for the client to report the result of the spell.
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
TARGET = 'Chicken'


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


def send(hwnd, text, settle=0.2):
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.4)
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.03)
    time.sleep(0.2)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(settle)


def main():
    run = 'client_cast_timing_' + str(time.time_ns())
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

        send(hwnd, '/target ' + TARGET, settle=1.2)
        state = reader()
        if not state['target_exists']:
            raise ValueError('no target')
        result['target_health'] = state['target_health']

        before = reader()
        send(hwnd, '/cast Fireball', settle=0.0)
        samples = []
        started = time.monotonic()
        for _ in range(40):
            time.sleep(0.25)
            state = reader()
            samples.append({'elapsed': round(time.monotonic() - started, 2),
                            'cast_started': state['cast_started'],
                            'cast_succeeded': state['cast_succeeded'],
                            'cast_failed': state['cast_failed'],
                            'casting': state['casting']})
            if (state['cast_succeeded'] > before['cast_succeeded']
                    or state['cast_failed'] > before['cast_failed']):
                break
        result['samples'] = samples
        result['resolved_after_seconds'] = samples[-1]['elapsed'] if samples else None
        result['outcome'] = ('success'
                              if samples and samples[-1]['cast_succeeded'] > before['cast_succeeded']
                              else 'failure')
        result['status'] = 'MEASURED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('01-end')
        path = evidence.write(result)
        d.log('cast timing run', path, result['status'])
    return 0 if result['status'] == 'MEASURED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
