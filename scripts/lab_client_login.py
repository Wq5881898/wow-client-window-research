"""Log the character into the world and confirm the telemetry panel is up."""
import json
import sys
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode
from client_evidence import Evidence

ROOT = Path(__file__).resolve().parents[1]
LOGIN = (716, 495)
ENTER_WORLD = (958, 992)
ACCOUNT = (960, 556)


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


def focus(hwnd):
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 0, 0, 1920, 1080,
                          win32con.SWP_NOZORDER)
    time.sleep(0.4)
    d.ensure_foreground(hwnd)
    time.sleep(0.5)


def main():
    run = 'client_login_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', steps=[])
    character = None
    if '--character' in sys.argv:
        index = sys.argv.index('--character')
        character = sys.argv[index + 1]
        result['character'] = character
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    if not hwnd:
        raise RuntimeError('no game window')
    try:
        hide_consoles()
        focus(hwnd)
        evidence.capture('01-login-screen')

        # Fill the account form: the client shows it on a fresh start.
        d.click_ui(hwnd, 512, 417)
        time.sleep(0.4)
        d.clear_field()
        d.type_text('GM01')
        time.sleep(0.3)
        d.press(win32con.VK_TAB)
        time.sleep(0.3)
        d.clear_field()
        d.type_text('123321')
        time.sleep(0.4)
        evidence.capture('02-credentials-entered')

        d.press(win32con.VK_RETURN)
        time.sleep(8.0)
        evidence.capture('03-character-select')

        # A character may be requested by name: the probe character can be
        # stuck in the ghost state, and another character of the account
        # takes over the role of the test subject.
        wanted = result.get('character')
        if wanted:
            for character in wanted:
                win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
                time.sleep(0.05)
            time.sleep(1.5)
            evidence.capture('04-character-picked')

        # The Enter World button is at the bottom centre of the client window.
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        d.click_raw(int((left + right) / 2), int(bottom - 95))
        time.sleep(12.0)
        hide_consoles()
        focus(hwnd)
        time.sleep(2.0)
        state = decode(grab_desktop())
        result['protocol'] = state['protocol']
        result['health'] = state['health']
        result['position'] = [state['pos_x'], state['pos_y']]
        evidence.capture('05-in-world', state)
        if state['protocol'] not in (3, 4, 5):
            raise ValueError('telemetry panel missing, protocol ' + str(state['protocol']))
        if state['dead'] or state['combat']:
            raise ValueError('unexpected state on login')
        result['status'] = 'IN_WORLD'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('06-end')
        path = evidence.write(result)
        d.log('login run', path, result['status'])
    return 0 if result['status'] == 'IN_WORLD' else 1


if __name__ == '__main__':
    raise SystemExit(main())
