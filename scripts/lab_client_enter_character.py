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
from client_chat_guard import close_world_map
from client_geometry import picture_to_screen
from client_read_fresh import (game_menu_open, find_logout_button,
                             read_or_dismiss)

ROOT = Path(__file__).resolve().parents[1]
LOGOUT = (959, 574)
ACCOUNT = 'GM01'
PASSWORD = '123321'
# The account field of the login screen, in the coordinates of the picture
# of the client. It was measured on the login screen of 1920x1080.
ACCOUNT_FIELD = (960, 565)
# The names of the characters on the selection screen, in the coordinates of
# the 1920 wide picture of the client. The list sits on the right edge of the
# window and every entry shows its name on the first of three lines.
CHARACTERS = {
    'Syra': (1600, 146),
    'Wao': (1600, 226),
    'Good': (1600, 304),
    'Probehuman': (1620, 465),
}

# The health of each character tells which one was actually entered, so a
# click that misses the entry cannot go unnoticed.
EXPECTED_HEALTH = {
    'Syra': (120, 160),
    'Wao': (3000, 4000),
    'Good': (3000, 4000),
    'Probehuman': (40, 60),
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
    # The account field of the login screen, in the coordinates of the
    # picture of the client.
    d.click_client(hwnd, *picture_to_screen(hwnd, *ACCOUNT_FIELD))
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


def selected_row(image):
    """Return the vertical centre of the highlighted entry of the list.

    The selected character is shown with a bright golden band behind its
    three lines. The band starts to the right of the name, so a column
    further right catches it in every case.
    """
    best = None
    best_count = 0
    for y in range(120, 520):
        count = 0
        for x in range(1700, 1880, 4):
            r, g, b = image.getpixel((x, y))
            if r > 180 and g > 170 and b < 150:
                count += 1
        if count > best_count:
            best_count = count
            best = y
    if best_count < 20:
        return None
    return best


def find_enter_world(image):
    """The centre of the red Enter World button, or None.

    The button sits at the bottom of the screen in the middle. Its position
    moves with the size of the client window, so it is found in the picture
    instead of being guessed.
    """
    pixels = image.convert('RGB').load()
    width, height = image.size
    best = None
    for y in range(int(height * 0.75), height - 10):
        left = right = None
        for x in range(int(width * 0.35), int(width * 0.65)):
            r, g, b = pixels[x, y]
            if r > 70 and r > g * 2 and r > b * 2:
                if left is None:
                    left = x
                right = x
        if left is not None and right - left > 100:
            best = ((left + right) // 2, y)
    return best


def at_character_selection(image):
    """The character selection shows a red Enter World button at the bottom.

    The login screen has no such button, so the two screens can be told
    apart without reading any text.
    """
    return find_enter_world(image) is not None


def inside_the_world(image, reader):
    """True when the client shows the game world.

    The three screens are told apart by what is on the screen. The
    character selection shows a red Enter World button and the login screen
    shows the logo of the game. Only in the world the probe panel of the
    telemetry is on the screen, because the add-on is loaded when the
    character enters the world.
    """
    if find_enter_world(image) is not None:
        return False
    try:
        reader()
    except Exception:
        return False
    return True


def main():
    run = 'client_enter_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', steps=[])
    wanted = 'Syra'
    if '--character' in sys.argv:
        wanted = sys.argv[sys.argv.index('--character') + 1]
    result['character'] = wanted
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        hide_consoles()

        def raw_reader():
            return decode(assert_real_frame(grab_desktop()))

        def reader():
            # A window of the client that is modal freezes the panel of the
            # probe, so it is closed before the reading.
            return read_or_dismiss(raw_reader, d.game_window())

        point = CHARACTERS.get(wanted)
        if point is None:
            raise ValueError('unknown character ' + wanted)

        # The client may be inside the world, at the selection or at the
        # login. The world map covers the screen and hides the telemetry, so
        # it is closed before the state of the client is looked at.
        close_world_map(hwnd, reader)
        # The three screens are told apart by the picture, not by the
        # telemetry: the probe panel stays alive at the character selection.
        if inside_the_world(grab_desktop(), reader):
            # The menu of the client has to be open before the logout can
            # be clicked, so it is opened and checked.
            logout = None
            for _ in range(4):
                image = grab_desktop()
                logout = find_logout_button(image)
                if logout is not None:
                    break
                d.post_key(hwnd, win32con.VK_ESCAPE)
                time.sleep(1.2)
            if logout is None:
                raise ValueError('the logout button of the client was not found')
            result['logout_button'] = logout
            d.u.SetCursorPos(*logout)
            time.sleep(0.8)
            d.click_client(hwnd, *logout)
            time.sleep(12.0)
            evidence.capture('00-after-logout')

        # The logout lands on the login screen when the session was fresh.
        if not at_character_selection(grab_desktop()):
            hwnd = d.game_window()
            login(hwnd)
            evidence.capture('01-after-login')

        hwnd = d.game_window()
        d.click_client(hwnd, *picture_to_screen(hwnd, *point))
        time.sleep(1.5)
        evidence.capture('02-picked')
        # The click can miss the entry, so the highlight is checked before
        # the character is entered.
        highlight = selected_row(grab_desktop())
        result['highlight_row'] = highlight
        expected_y = picture_to_screen(hwnd, *point)[1]
        result['expected_highlight_row'] = expected_y
        if highlight is None or abs(highlight - expected_y) > 40:
            raise ValueError('the character was not selected: the highlight '
                             'is at %s, expected near %s' % (highlight, expected_y))
        enter = find_enter_world(grab_desktop())
        result['enter_world_button'] = enter
        if enter is None:
            raise ValueError('the Enter World button was not found')
        d.click_client(hwnd, *enter)
        time.sleep(15.0)
        hide_consoles()
        hwnd = d.game_window()
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
        # The health proves which character was entered.
        low, high = EXPECTED_HEALTH.get(wanted, (0, 100000))
        result['health_expected'] = [low, high]
        if not low <= state['health'] <= high:
            raise ValueError('the character that was entered is not the '
                             'requested one: health %d, expected %d-%d'
                             % (state['health'], low, high))
        result['status'] = 'IN_WORLD'
    except Exception as exc:
        result['error'] = repr(exc)
        # What the client looked like when it failed.
        try:
            import subprocess
            out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Wow.exe',
                                   '/FO', 'CSV', '/NH'], capture_output=True,
                                  text=True, encoding='gbk', errors='replace')
            result['wow_processes'] = [line.split(',')[1].strip('"')
                                       for line in out.stdout.splitlines()
                                       if line.startswith('"Wow.exe"')]
            windows = []

            def cb(hwnd, _):
                windows.append((hwnd, win32gui.GetClassName(hwnd),
                                win32gui.GetWindowText(hwnd)))
                return True

            win32gui.EnumWindows(cb, None)
            result['client_windows'] = [w for w in windows
                                        if 'Wow' in w[2] or 'D3D' in w[1]
                                        or 'Gx' in w[1]]
        except Exception:
            pass
    finally:
        evidence.capture('04-end')
        path = evidence.write(result)
        d.log('enter run', path, result['status'])
    return 0 if result['status'] == 'IN_WORLD' else 1


if __name__ == '__main__':
    raise SystemExit(main())
