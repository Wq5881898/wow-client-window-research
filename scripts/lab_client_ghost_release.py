"""Release the ghost through the client own resurrect entry point.

The ghost state does not accept chat commands at all, and the graveyard of
this test server offers no release point candle, so the character cannot be
brought back with plain input. The client exposes the resurrect request
through AcceptResurrect, which is invoked here from the driver side. The
read only probe is not modified.
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

SCRIPTS = [
    'if IsPlayerGhost() then AcceptResurrect() end',
    'if IsPlayerGhost() then Resurrect() end',
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


def send(hwnd, text, settle=2.0):
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.4)
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.03)
    time.sleep(0.2)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(settle)


def main():
    run = 'client_ghost_release_' + str(time.time_ns())
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

        for script in SCRIPTS:
            send(hwnd, '/run ' + script, settle=3.0)
            try:
                state = reader()
            except ValueError:
                result['attempts'].append({'script': script, 'error': 'decode failed'})
                continue
            result['attempts'].append({'script': script, 'health': state['health'],
                                       'dead': state['dead'], 'power': state['power']})
            if not state['dead']:
                result['status'] = 'RELEASED'
                evidence.capture('02-released', state)
                break
        if result['status'] != 'RELEASED':
            raise ValueError('the client did not release the ghost')
        result['final'] = state
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('ghost release run', path, result['status'])
    return 0 if result['status'] in ('RELEASED', 'ALREADY_ALIVE') else 1


if __name__ == '__main__':
    raise SystemExit(main())
