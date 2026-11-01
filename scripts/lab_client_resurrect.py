"""Release the character from the ghost state and wait for the respawn."""
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
RESURRECT = (960, 252)    # "Accept" button of the "Resurrect now?" dialog


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
    run = 'client_resurrect_' + str(time.time_ns())
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

        state = reader()
        evidence.capture('01-ghost', state)
        result['start'] = {'health': state['health'], 'dead': state['dead'],
                           'combat': state['combat']}
        if not state['dead']:
            result['status'] = 'ALREADY_ALIVE'
        else:
            # The ghost dialog offers a release button on the right edge.
            d.click_si(*RESURRECT)
            time.sleep(2.0)
            state = reader()
            evidence.capture('02-after-release', state)
            result['after_release'] = {'dead': state['dead'], 'health': state['health']}
            # Wait for the server to respawn the character.
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                time.sleep(2.0)
                state = reader()
                if not state['dead'] and state['health'] > 0:
                    break
            evidence.capture('03-respawned', state)
            if state['dead']:
                raise ValueError('still a ghost after release')
            result['status'] = 'RESURRECTED'
        result['final'] = state
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('04-end')
        path = evidence.write(result)
        d.log('resurrect run', path, result['status'])
    return 0 if result['status'] in ('RESURRECTED', 'ALREADY_ALIVE') else 1


if __name__ == '__main__':
    raise SystemExit(main())
