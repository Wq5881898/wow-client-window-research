"""Recover the character with the game master commands of the test server."""
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
    run = 'client_gm_recover_' + str(time.time_ns())
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
        result['start'] = {'health': state['health'], 'dead': state['dead'],
                           'combat': state['combat']}
        evidence.capture('01-start', state)

        for command in ('resurrect', 'gm on', 'revive', 'heal', 'unlearn all'):
            send(hwnd, '/' + command, settle=2.0)
            try:
                state = reader()
            except ValueError:
                result['attempts'].append({'command': command, 'error': 'decode failed'})
                continue
            result['attempts'].append({'command': command, 'health': state['health'],
                                       'dead': state['dead'], 'power': state['power']})
            if not state['dead'] and state['health'] > 0:
                result['status'] = 'RECOVERED'
                evidence.capture('02-recovered', state)
                break
        if result['status'] != 'RECOVERED':
            raise ValueError('the game master commands did not recover the character')
        result['final'] = state
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('gm recover run', path, result['status'])
    return 0 if result['status'] == 'RECOVERED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
