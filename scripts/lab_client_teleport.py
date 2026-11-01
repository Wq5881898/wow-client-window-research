"""Move the character with a game master command of the test server.

The account has game master rights, so the character can be placed where
the test needs it. This only moves the character, it does not change any
state of the world.
"""
import json
import sys
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
from client_evidence import Evidence
from client_chat_guard import ensure_chat_closed, close_world_map

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = 'GM01'


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


def send(hwnd, text, reader, settle=1.5):
    ensure_chat_closed(hwnd, reader)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.4)
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.04)
    time.sleep(0.2)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(settle)
    return reader()


def main():
    run = 'client_teleport_' + str(time.time_ns())
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

        close_world_map(hwnd, reader)
        before = reader()
        result['start'] = {'position': [before['pos_x'], before['pos_y']],
                            'health': before['health']}
        evidence.capture('01-start', before)

        # The game master commands need the game master mode to be on.
        send(hwnd, '.gm on', reader, settle=2.0)
        result['gm_on'] = True

        # The game master command that places the character at a spot of the
        # zone. Several forms are tried because the client and the server
        # accept different ones.
        commands = [
            '.tele ' + ACCOUNT + ' 42 62',
            '.tele Northshire Valley 42 62',
            '.tele ' + ACCOUNT + ' 42.5 62.5',
        ]
        for command in commands:
            send(hwnd, command, reader, settle=3.0)
            state = reader()
            moved = (abs(state['pos_x'] - before['pos_x']) >= 0.001
                     or abs(state['pos_y'] - before['pos_y']) >= 0.001)
            result['steps'].append({'command': command, 'moved': moved,
                                     'position': [state['pos_x'], state['pos_y']]})
            if moved:
                break
        state = reader()
        result['after_teleport'] = {'position': [state['pos_x'], state['pos_y']],
                                    'health': state['health']}
        evidence.capture('02-after-teleport', state)
        if abs(state['pos_x'] - before['pos_x']) < 0.001 \
                and abs(state['pos_y'] - before['pos_y']) < 0.001:
            raise ValueError('the character did not move')
        result['status'] = 'TELEPORTED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('teleport run', path, result['status'])
    return 0 if result['status'] == 'TELEPORTED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
