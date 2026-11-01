"""Watch the health of the target without doing anything.

A creature that leaves combat regenerates quickly in this client version, so
the health of an untouched target shows whether the observed rise was a
regeneration or a different creature.
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
    run = 'client_regen_' + str(time.time_ns())
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

        start = time.monotonic()
        while time.monotonic() - start < 12:
            state = reader()
            result['samples'].append({
                'elapsed': round(time.monotonic() - start, 2),
                'guid': state['target_guid'],
                'health': state['target_health'],
                'combat': state['combat'],
            })
            time.sleep(0.4)
        result['status'] = 'SAMPLED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('01-end')
        path = evidence.write(result)
        d.log('regen run', path, result['status'])
    return 0 if result['status'] == 'SAMPLED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
