"""Measure the shortest gap between two casts.

The creature regenerates as soon as it leaves combat, so the driver has to
start the next cast before the target recovers. This measures how fast the
commands can follow each other.
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


def main():
    run = 'client_cast_gap_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', casts=[])
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
                            'health': state['target_health']}

        for index in range(4):
            before = reader()
            # The command is typed without waiting for the client.
            d.post_key(hwnd, win32con.VK_RETURN)
            time.sleep(0.15)
            for character in '/cast Fireball':
                win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
                time.sleep(0.02)
            d.post_key(hwnd, win32con.VK_RETURN)
            started = time.monotonic()
            # Wait for the cast to start, then note how long it took.
            deadline = started + 8
            while time.monotonic() < deadline:
                state = reader()
                if state['cast_started'] != before['cast_started']:
                    break
                time.sleep(0.05)
            result['casts'].append({
                'index': index,
                'command_to_start': round(time.monotonic() - started, 3),
                'cast_started': state['cast_started'],
                'cast_succeeded': state['cast_succeeded'],
                'target_health': state['target_health'],
            })
            # No pause: the next command follows immediately.
            time.sleep(0.2)
        result['status'] = 'MEASURED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('01-end')
        path = evidence.write(result)
        d.log('cast gap run', path, result['status'])
    return 0 if result['status'] == 'MEASURED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
