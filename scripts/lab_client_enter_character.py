"""Bring a character into the world from any of the client screens.

The client can be at the login screen, at the character selection or inside
the world. The script brings it to the requested character and confirms the
live telemetry is running.
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

ROOT = Path(__file__).resolve().parents[1]
ENTER_WORLD = (957, 984)
LOGOUT = (955, 585)
ACCOUNT = 'GM01'
PASSWORD = '123321'
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


def send(hwnd, text, settle=0.6):
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.4)
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.04)
    time.sleep(0.2)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(settle)


def login(hwnd):
    """Fill the account form of the login screen."""
    d.click_ui(hwnd, 512, 417)
    time.sleep(0.4)
    d.clear_field()
    d.type_text(ACCOUNT)
    time.sleep(0.3)
    d.press(win32con.VK_TAB)
    time.sleep(0.3)
    d.clear_field()
    d.type_text(PASSWORD)
    time.sleep(0.4)
    d.press(win32con.VK_RETURN)
    time.sleep(10.0)


def at_character_selection(image):
    """The character selection shows a red Enter World button at the bottom.

    The login screen has no such button, so the two screens can be told
    apart without reading any text.
    """
    region = image.crop((880, 950, 1040, 1010)).convert('RGB')
    red = 0
    for r, g, b in region.getdata():
        if r > 120 and g < 60 and b < 60:
            red += 1
    return red > 400


def main():
    run = 'client_enter_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', steps=[])
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

        # The client may be inside the world, at the selection or at the
        # login. The telemetry tells the world and the selection apart.
        try:
            reader()
            in_world = True
        except ValueError:
            in_world = False
        if in_world:
            d.post_key(hwnd, win32con.VK_ESCAPE)
            time.sleep(1.5)
            d.u.SetCursorPos(*LOGOUT)
            time.sleep(0.8)
            d.click_si(*LOGOUT)
            time.sleep(12.0)
            evidence.capture('00-after-logout')

        # The logout lands on the login screen or on the character
        # selection, and neither of them shows the telemetry.
        try:
            reader()
        except ValueError:
            pass
        else:
            raise ValueError('the client is still inside the world')
        if not at_character_selection(grab_desktop()):
            login(hwnd)
            evidence.capture('01-after-login')

        d.click_si(*point)
        time.sleep(1.5)
        evidence.capture('02-picked')
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
        evidence.capture('03-in-world', state)
        if state['dead']:
            raise ValueError('the character entered the world as a ghost')
        result['status'] = 'IN_WORLD'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('04-end')
        path = evidence.write(result)
        d.log('enter run', path, result['status'])
    return 0 if result['status'] == 'IN_WORLD' else 1


if __name__ == '__main__':
    raise SystemExit(main())
