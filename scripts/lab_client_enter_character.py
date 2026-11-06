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
from client_parent_run import stamp
from client_chat_guard import close_world_map
from client_geometry import picture_to_screen
from client_read_fresh import (game_menu_open, find_logout_button, open_menu_logout,
                                release_spirit, wait_out_of_combat,
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
# The characters of the account in the order of the list on the screen.
# The rows are not written down: they are found in the picture, because the
# list moves when a character is added and a wrong row picks the wrong
# character. The fourth entry shows its name as a question mark.
CHARACTERS = ['Syra', 'Wao', 'Good', '?', 'Probehuman']

# The health of each character tells which one was actually entered, so a
# click that misses the entry cannot go unnoticed.
EXPECTED_HEALTH = {
    'Syra': (120, 160),
    'Wao': (3000, 4000),
    'Good': (3000, 4000),
    # The character gains levels in the experiments, so the health is only
    # a coarse proof of the identity.
    'Probehuman': (40, 200),
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


def golden_rows(image, x_from, x_to, y_from=100, y_to=560):
    """The rows that hold a golden band, as a list of (top, bottom).

    The names of the characters and the band behind the selected one are
    both golden. The band of the selection starts to the right of the
    names, so the two are looked for in different columns.
    """
    rows = []
    for y in range(y_from, y_to):
        count = 0
        for x in range(x_from, x_to, 4):
            r, g, b = image.getpixel((x, y))
            if r > 180 and g > 170 and b < 150:
                count += 1
        if count >= 20:
            rows.append(y)
    bands = []
    for y in rows:
        if bands and y - bands[-1][1] <= 2:
            bands[-1][1] = y
        else:
            bands.append([y, y])
    return [(top, bottom) for top, bottom in bands]


def name_rows(image):
    """The rows of the names of the characters of the list.

    The name of every character is written in golden letters in the column
    of the names. The rows are found in the picture, so the list may grow
    and shrink without the driver picking the wrong character.
    """
    bands = golden_rows(image, 1580, 1700)
    return [(top + bottom) // 2 for top, bottom in bands]


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

    The search stays above the action bar of the world: that bar has red
    icons of its own, and one of them was mistaken for the button, which
    made every picture of the world look like the selection screen.
    """
    pixels = image.convert('RGB').load()
    width, height = image.size
    best = None
    for y in range(int(height * 0.86), int(height * 0.96)):
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

    The panel of the probe is only on the screen in the world, so the
    reading of the panel decides. The Enter World button does not decide:
    the action bar of the world has red icons in the same part of the
    picture, and they were mistaken for the button.
    """
    try:
        reader()
    except Exception:
        return False
    return True


def run_recovery():
    """Run the recovery of a ghost, in its own process.

    The recovery drives the client, so it needs the client alone; the
    console of this process would cover the game.
    """
    import subprocess
    command = [sys.executable.replace('python.exe', 'pythonw.exe'), '-X',
               'utf8', str(Path(__file__).resolve().parent /
                           'lab_client_danger_recovery.py')]
    return subprocess.run(command, cwd=str(ROOT)).returncode


def main():
    run = 'client_enter_' + str(time.time_ns())
    result = stamp(dict(run=run, status='FAILED', steps=[]), sys.argv)
    wanted = 'Syra'
    if '--character' in sys.argv:
        wanted = sys.argv[sys.argv.index('--character') + 1]
    result['character'] = wanted
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        hide_consoles()

        def picture():
            # The desktop is shared with the user, so another window can be
            # in front. The picture of the screen is then not of the game,
            # and the red icon of the client in the task bar is mistaken for
            # the Enter World button. The client is brought to the front
            # before every picture.
            d.restore_foreground(hwnd)
            return grab_desktop()

        def raw_reader():
            return decode(assert_real_frame(picture()))

        def reader():
            # A window of the client that is modal freezes the panel of the
            # probe, so it is closed before the reading.
            return read_or_dismiss(raw_reader, d.game_window())

        if wanted not in CHARACTERS:
            raise ValueError('unknown character ' + wanted)
        index = CHARACTERS.index(wanted)

        # The client may be inside the world, at the selection or at the
        # login. The world map covers the screen and hides the telemetry, so
        # it is closed before the state of the client is looked at.
        close_world_map(hwnd, reader)
        # The three screens are told apart by the picture, not by the
        # telemetry: the probe panel stays alive at the character selection.
        in_world = inside_the_world(picture(), reader)
        result['inside_the_world'] = in_world
        if in_world:
            # The menu of the client has to be open before the logout can
            # The menu of the client does not open while the character is in
            # combat, so the fight has to be over first.
            wait_out_of_combat(reader, hwnd)
            # be clicked, so it is opened and checked.
            logout = open_menu_logout(hwnd)
            if logout is None:
                raise ValueError('the logout button of the client was not found')
            result['logout_button'] = logout
            d.u.SetCursorPos(*logout)
            time.sleep(0.8)
            d.click_client(hwnd, *logout)
            time.sleep(12.0)
            evidence.capture('00-after-logout')

        # The logout lands on the login screen when the session was fresh.
        at_selection = at_character_selection(picture())
        result['at_character_selection'] = at_selection
        if not at_selection:
            hwnd = d.game_window()
            login(hwnd)
            evidence.capture('01-after-login')
            # The login takes a while, and the list of the characters comes
            # after the realm. The list is waited for, or the names are
            # read from the picture of the login screen.
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                if at_character_selection(picture()):
                    at_selection = True
                    break
                time.sleep(2.0)
            result['at_character_selection'] = at_selection
            if not at_selection:
                raise ValueError('the list of the characters did not appear')

        hwnd = d.game_window()
        # The row of the name of the wanted character is found in the
        # picture, so a list that grew or shrank does not pick the wrong
        # character.
        rows = name_rows(picture())
        result['name_rows'] = rows
        if index >= len(rows):
            raise ValueError('the list shows %d characters, %s is the %d'
                             % (len(rows), wanted, index + 1))
        name_y = rows[index]
        result['expected_name_row'] = name_y
        # The click can miss the entry: only the name and the level line of
        # an entry answer to a click. A few points around the name are
        # tried until the band of the selection covers it. The first click
        # can also be swallowed by the window that has to take the focus.
        band = None
        for attempt in range(8):
            offset = (0, 8, -8)[attempt % 3]
            d.click_client(hwnd, *picture_to_screen(hwnd, 1620,
                                                    name_y + offset))
            time.sleep(1.0)
            bands = golden_rows(picture(), 1700, 1880)
            band = bands[0] if bands else None
            result['highlight_band'] = band
            if band and band[0] - 12 <= name_y <= band[1] + 12:
                break
        if not band or not (band[0] - 12 <= name_y <= band[1] + 12):
            raise ValueError('the character was not selected: the band is '
                             '%s, the name of %s is at %s'
                             % (band, wanted, name_y))
        evidence.capture('02-picked')
        enter = find_enter_world(picture())
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
            # The server kept the character as a ghost, because the client
            # was closed while it was dead. The window of the death is
            # closed, so the character comes back at the graveyard and the
            # run can go on.
            button = release_spirit(hwnd)
            result['release_button'] = button
            evidence.capture('03b-ghost-released')
            if button is None:
                # The spirit was released before, so there is no death
                # window left. The character is a ghost that has to walk to
                # its corpse and be revived there, which is the work of the
                # recovery.
                result['recovery'] = run_recovery()
                state = reader()
                result['after_recovery'] = {'health': state['health'],
                                            'dead': state['dead'],
                                            'position': [state['pos_x'],
                                                         state['pos_y']]}
                evidence.capture('03c-recovered', state)
                if state['dead']:
                    raise ValueError('the character stayed a ghost after the '
                                     'recovery')
            else:
                time.sleep(4.0)
                state = reader()
                result['after_release'] = {'health': state['health'],
                                           'dead': state['dead'],
                                           'position': [state['pos_x'],
                                                        state['pos_y']]}
                evidence.capture('03c-released', state)
                if state['dead']:
                    raise ValueError('the character stayed a ghost after the '
                                     'release of the spirit')
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
