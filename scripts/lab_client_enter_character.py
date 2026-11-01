"""Pick a character on the selection screen and enter the world."""
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

ROOT = Path(__file__).resolve().parents[1]
ENTER_WORLD = (957, 984)
LOGOUT = (955, 585)
# Character names on the selection screen, in screen pixels.
CHARACTERS = {
    'Syra': (1592, 152),
    'Wao': (1592, 245),
    'Good': (1592, 337),
    'Probehuman': (1592, 490),
}


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
    run = 'client_enter_' + str(time.time_ns())
    result = dict(run=run, status='FAILED')
    wanted = 'Syra'
    if '--character' in sys.argv:
        wanted = sys.argv[sys.argv.index('--character') + 1]
    result['character'] = wanted
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        point = CHARACTERS.get(wanted)
        if point is None:
            raise ValueError('unknown character ' + wanted)

        # The client may still be inside the world, so the game menu is used
        # to reach the character selection screen first.
        d.post_key(hwnd, win32con.VK_ESCAPE)
        time.sleep(1.5)
        evidence.capture('00-menu')
        d.u.SetCursorPos(*LOGOUT)
        time.sleep(0.8)
        d.click_si(*LOGOUT)
        time.sleep(12.0)
        evidence.capture('00-character-select')

        d.click_si(*point)
        time.sleep(1.5)
        evidence.capture('01-picked')
        d.click_si(*ENTER_WORLD)
        time.sleep(15.0)
        hide_consoles()
        d.ensure_foreground(hwnd)
        time.sleep(2.0)
        state = reader()
        result['protocol'] = state['protocol']
        result['health'] = state['health']
        result['dead'] = state['dead']
        result['power'] = state['power']
        result['position'] = [state['pos_x'], state['pos_y']]
        evidence.capture('02-in-world', state)
        if state['dead']:
            raise ValueError('the character entered the world as a ghost')
        result['status'] = 'IN_WORLD'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('enter run', path, result['status'])
    return 0 if result['status'] == 'IN_WORLD' else 1


if __name__ == '__main__':
    raise SystemExit(main())
