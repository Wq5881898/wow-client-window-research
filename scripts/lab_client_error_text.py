"""Capture the client error text of a failed cast.

A failing cast makes the client print an error line on the screen. The
screenshot proves which text the probe has to map to a reason code.
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


def send(hwnd, text, settle=1.5):
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.4)
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.03)
    time.sleep(0.2)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(settle)


def main():
    run = 'client_error_text_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', attempts=[])
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        # Any cast at a target that is out of sight or out of range prints
        # the error line of the client.
        for attempt, command in enumerate(('/cast Fireball', '/cast Fireball')):
            before = reader()
            send(hwnd, command, settle=1.0)
            image = grab_desktop()
            image.crop((300, 60, 1600, 260)).save(
                '.cache/desktop-check/error-text-%d.png' % attempt)
            evidence.capture('error-%d' % attempt)
            after = reader()
            result['attempts'].append({
                'attempt': attempt,
                'ui_errors_before': before['ui_errors'],
                'ui_errors_after': after['ui_errors'],
                'cast_failed_before': before['cast_failed'],
                'cast_failed_after': after['cast_failed'],
                'last_error_reason': after['last_error_reason'],
                'last_reason': after['last_reason'],
                'target_exists': after['target_exists'],
                'target_health': after['target_health'],
            })
        result['status'] = 'CAPTURED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        path = evidence.write(result)
        d.log('error text run', path, result['status'])
    return 0 if result['status'] == 'CAPTURED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
