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

ROOT = Path(__file__).resolve().parents[1]
LOGOUT = (955, 585)
ACCOUNT = 'GM01'
PASSWORD = '123321'
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


def inside_the_world(image, hwnd=None):
    """True when the client shows the game world.

    The player frame with the golden portrait border sits in the top left
    corner of the screen while the character is in the world. The character
    selection shows the logo of the game there instead, so the corner tells
    the two apart. The corner is looked for where the client draws it, so the
    size of the window does not matter.
    """
    box = (30, 30, 110, 110)
    if hwnd is not None:
        left, top = picture_to_screen(hwnd, box[0], box[1])
        right, bottom = picture_to_screen(hwnd, box[2], box[3])
        box = (left, top, right, bottom)
    region = image.crop(box).convert('RGB')
    colours = region.getcolors(maxcolors=100000)
    if not colours:
        return False
    golden = 0
    for count, (r, g, b) in colours:
        if r > 110 and g > 80 and b < 70 and r > b + 40:
            golden += count
    return golden > 300


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
        # login. The world map covers the screen and hides the telemetry, so
        # it is closed before the state of the client is looked at.
        close_world_map(hwnd, reader)
        # The three screens are told apart by the picture, not by the
        # telemetry: the probe panel stays alive at the character selection.
        if inside_the_world(grab_desktop(), hwnd):
            d.post_key(hwnd, win32con.VK_ESCAPE)
            time.sleep(1.5)
            logout = picture_to_screen(hwnd, *LOGOUT)
            d.u.SetCursorPos(*logout)
            time.sleep(0.8)
            d.click_si(*logout)
            time.sleep(12.0)
            evidence.capture('00-after-logout')

        # The logout lands on the login screen when the session was fresh.
        if not at_character_selection(grab_desktop()):
            login(hwnd)
            evidence.capture('01-after-login')

        d.click_si(*picture_to_screen(hwnd, *point))
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
        d.click_si(*enter)
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
    finally:
        evidence.capture('04-end')
        path = evidence.write(result)
        d.log('enter run', path, result['status'])
    return 0 if result['status'] == 'IN_WORLD' else 1


if __name__ == '__main__':
    raise SystemExit(main())
