"""Log the character out and in again and check the state that remains.

A recovery is only accepted when the state survives a log out and a log
in: a picture of the moment of the revival says nothing about the state
that the character stays in. The script leaves the client at the character
selection, enters the character again and reports what the client shows.
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
from client_read_fresh import (read_or_dismiss, find_logout_button,
                                find_red_button)

ROOT = Path(__file__).resolve().parents[1]
CHARACTERS = {
    'Syra': (1600, 146),
    'Wao': (1600, 226),
    'Good': (1600, 304),
    'Probehuman': (1620, 465),
}
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


def raw_reader():
    return decode(assert_real_frame(grab_desktop()))


def at_character_selection(image):
    """The character selection shows a red Enter World button."""
    return find_red_button(image, top=0.85, bottom=0.99) is not None


def find_enter_world(image):
    """The Enter World button of the character selection."""
    return find_red_button(image, top=0.80, bottom=0.99)


def selected_row(image):
    """The vertical centre of the highlighted entry of the list."""
    best = None
    best_count = 0
    for y in range(120, 560):
        count = 0
        for x in range(1700, 1880, 4):
            r, g, b = image.convert('RGB').getpixel((x, y))
            if r > 180 and g > 170 and b < 150:
                count += 1
        if count > best_count:
            best_count = count
            best = y
    if best_count < 20:
        return None
    return best


def main():
    run = 'client_relogin_' + str(time.time_ns())
    result = dict(run=run, status='FAILED')
    evidence = Evidence(run)
    wanted = 'Probehuman'
    if '--character' in sys.argv[1:]:
        wanted = sys.argv[sys.argv.index('--character') + 1]
    result['character'] = wanted
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return read_or_dismiss(raw_reader, d.game_window())

        before = reader()
        result['before'] = {'health': before['health'], 'dead': before['dead'],
                            'combat': before['combat'],
                            'position': [before['pos_x'], before['pos_y']],
                            'corpse_exists': before.get('corpse_exists')}
        evidence.capture('01-before', before)

        # Open the menu of the client and leave the game with the logout.
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
        d.click_client(hwnd, *logout)
        time.sleep(12.0)
        evidence.capture('02-after-logout')

        # The client shows the character selection now.
        image = grab_desktop()
        if not at_character_selection(image):
            raise ValueError('the client did not reach the character selection')
        d.click_client(hwnd, *CHARACTERS[wanted])
        time.sleep(1.5)
        highlight = selected_row(grab_desktop())
        result['highlight_row'] = highlight
        evidence.capture('03-picked')
        if highlight is None or abs(highlight - CHARACTERS[wanted][1]) > 40:
            raise ValueError('the character was not selected: the highlight '
                             'is at %s' % highlight)
        enter = find_enter_world(grab_desktop())
        result['enter_world_button'] = enter
        if enter is None:
            raise ValueError('the Enter World button was not found')
        d.click_client(hwnd, *enter)
        time.sleep(18.0)
        hide_consoles()
        after = reader()
        result['after'] = {'health': after['health'], 'dead': after['dead'],
                           'combat': after['combat'],
                           'position': [after['pos_x'], after['pos_y']],
                           'corpse_exists': after.get('corpse_exists'),
                           'speed': after.get('speed')}
        evidence.capture('04-after-login', after)
        low, high = EXPECTED_HEALTH.get(wanted, (0, 100000))
        if after['dead']:
            raise ValueError('the character is dead after the log in')
        if not low <= after['health'] <= high:
            raise ValueError('the health after the log in is %d, expected %d-%d'
                             % (after['health'], low, high))
        result['status'] = 'VERIFIED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('09-end')
        path = evidence.write(result)
        d.log('relogin', str(path), result['status'])
    return 0 if result['status'] == 'VERIFIED' else 1


if __name__ == '__main__':
    import sys
    raise SystemExit(main())
