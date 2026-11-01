"""Bring the ghost back to life at the graveyard.

The client shows a "Resurrect now?" dialog once the ghost interacts with
the graveyard. The accept button sits in the middle of the screen, so the
routine clicks a few candidate spots and then the dialog button.
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
ACCEPT_BUTTON = (960, 252)
# Gravestones and the resurrection NPC, in screen pixels.
CANDIDATES = [
    (224, 224), (336, 304), (424, 360), (832, 360),
    (1440, 464), (1010, 800), (1750, 400),
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


def main():
    run = 'client_graveyard_' + str(time.time_ns())
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

        state = reader()
        result['start'] = {'health': state['health'], 'dead': state['dead']}
        evidence.capture('01-start', state)
        if not state['dead']:
            result['status'] = 'ALREADY_ALIVE'
            return 0

        for point in CANDIDATES:
            d.click_si(*point)
            time.sleep(0.8)
            # The dialog may appear right away; its accept button is fixed.
            d.click_si(*ACCEPT_BUTTON)
            time.sleep(1.2)
            try:
                state = reader()
            except ValueError:
                result['attempts'].append({'point': point, 'error': 'decode failed'})
                continue
            result['attempts'].append({'point': point, 'dead': state['dead'],
                                       'health': state['health']})
            if not state['dead']:
                result['status'] = 'RESURRECTED'
                evidence.capture('02-resurrected', state)
                break
        if result['status'] != 'RESURRECTED':
            raise ValueError('the graveyard did not release the ghost')
        result['final'] = state
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('graveyard run', path, result['status'])
    return 0 if result['status'] in ('RESURRECTED', 'ALREADY_ALIVE') else 1


if __name__ == '__main__':
    raise SystemExit(main())
