"""Read the telemetry of the client and make sure it is not an old picture.

The client renders very slowly when another window is in front of it, and
the panel of the probe then shows a picture of a moment that is minutes old.
A reading that is not fresh is worse than no reading, because it looks
right. Every read therefore checks that the sequence of the panel moved on,
and the client is woken up with a small movement of the mouse when it did
not.

A window of the client that is modal ("You have died") freezes the panel
half way through a write, and then nothing can be decoded at all. Such a
window is closed before the reading: the button of the dialog is the only
red button in the upper half of the screen.
"""
import time

import lab_driver5 as d


def nudge(hwnd, click=False):
    """Wake the client up without changing anything in the game."""
    try:
        x, y = d.win32gui.GetCursorPos()
    except Exception:
        return
    d.u.SetCursorPos(x + 1, y)
    time.sleep(0.15)
    d.u.SetCursorPos(x, y)
    time.sleep(0.15)
    if click:
        # A click on the ground of the world only moves the mouse, it does
        # not select anything.
        d.click_si(x, y, hold=0.1)


def find_red_button(image, top=0.12, bottom=0.32):
    """The centre of the red button in the upper half of the screen."""
    width, height = image.size
    pixels = image.convert('RGB').load()
    rows = {}
    for y in range(int(height * top), int(height * bottom)):
        found = [x for x in range(int(width * 0.35), int(width * 0.65))
                 if pixels[x, y][0] > 90
                 and pixels[x, y][0] > pixels[x, y][1] * 2.2
                 and pixels[x, y][0] > pixels[x, y][2] * 2.2]
        if len(found) > 30:
            rows[y] = (min(found), max(found))
    if not rows:
        return None
    ys = sorted(rows)
    left = min(rows[y][0] for y in ys)
    right = max(rows[y][1] for y in ys)
    return ((left + right) // 2, (ys[0] + ys[-1]) // 2)


def menu_buttons(image):
    """The centres of the red buttons of the game menu, from top to bottom.

    The menu of the client shows a column of buttons in the middle of the
    screen. They are Video, Sound, Interface, Key Bindings, Macros, Logout,
    Exit Game and Return to Game.
    """
    width, height = image.size
    pixels = image.convert('RGB').load()
    rows = []
    for y in range(int(height * 0.30), int(height * 0.66)):
        found = [x for x in range(int(width * 0.42), int(width * 0.58))
                 if pixels[x, y][0] > 100
                 and pixels[x, y][1] < 70 and pixels[x, y][2] < 70]
        if len(found) > 60:
            rows.append((y, min(found), max(found)))
    buttons = []
    for y, left, right in rows:
        if buttons and y - buttons[-1][1] <= 2:
            buttons[-1] = (buttons[-1][0], y, buttons[-1][2], right)
            continue
        buttons.append((y, y, left, right))
    return [((left + right) // 2, (top + bottom) // 2)
            for top, bottom, left, right in buttons]


def find_logout_button(image):
    """The centre of the logout button of the game menu, or None.

    The buttons of the menu are Video, Sound, Interface, Key Bindings,
    Macros, Logout, Exit Game and Return to Game. The logout button is the
    one that sits a little below the middle of the screen; it is picked by
    its place and not by its number, because not every button is drawn in
    red.
    """
    buttons = menu_buttons(image)
    if not buttons:
        return None
    height = image.size[1]
    wanted = height * 0.531
    return min(buttons, key=lambda b: abs(b[1] - wanted))


def game_menu_open(image):
    """True when the game menu of the client is on the screen.

    The menu shows a column of red buttons in the middle of the screen.
    """
    return len(menu_buttons(image)) >= 6


def open_menu_logout(hwnd, tries=8):
    """Open the menu of the client and return the logout button.

    The escape key closes the menu again, so it is only sent while the menu
    is not on the screen. The client is put in front first: the key is sent
    as real input and goes to the window that has the focus.
    """
    from client_capture import grab_desktop
    for attempt in range(tries):
        d.ensure_foreground(hwnd)
        time.sleep(0.6)
        image = grab_desktop()
        if game_menu_open(image):
            logout = find_logout_button(image)
            if logout is not None:
                return logout
            # The menu is open but the button was not found. The picture
            # may be too old, so it is taken again.
            time.sleep(1.0)
            continue
        d.post_key(hwnd, 0x1B)
        time.sleep(1.5)
    return None


def release_spirit(hwnd, tries=6):
    """Close the window of the death, so the character becomes a ghost.

    The button of the window is the only red button in the upper half of
    the screen.
    """
    from client_capture import grab_desktop
    for attempt in range(tries):
        image = grab_desktop()
        button = find_red_button(image)
        if button is not None:
            d.click_client(hwnd, *button)
            time.sleep(2.0)
            return button
        d.ensure_foreground(hwnd)
        time.sleep(0.5)
    return None


def read_fresh(reader, hwnd, tries=4, wait=0.8):
    """Return a state whose sequence moved on since the reading before."""
    state = reader()
    for _ in range(tries):
        time.sleep(wait)
        following = reader()
        if following['sequence'] != state['sequence']:
            return following
        nudge(hwnd, click=(_ == tries - 1))
        state = following
    return state


def read_or_dismiss(reader, hwnd, image=None, tries=6):
    """Read the telemetry and close a window of the client that blocks it.

    The death window of the client and the game menu are modal. They freeze
    the panel of the probe in the middle of a write, so nothing can be
    decoded while they are on the screen. The button of the death window is
    clicked, because the character has to become a ghost anyway; the escape
    key closes the game menu.

    The escape key must **not** be sent when the client shows the login
    screen: there it closes the client, and the driver would kill the
    client every time it looks at the login screen.
    """
    from client_capture import grab_desktop
    last = None
    for attempt in range(tries):
        try:
            return reader()
        except Exception as exc:
            last = exc
        if image is None:
            image = grab_desktop()
        button = find_red_button(image)
        if button is not None:
            d.click_client(hwnd, *button)
            time.sleep(1.5)
            image = None
            continue
        if game_menu_open(image):
            d.post_key(hwnd, 0x1B)
            time.sleep(0.8)
            image = None
            continue
        # Neither a dialog nor the menu: the client shows the login screen
        # or the picture is simply too old. The mouse is moved to wake the
        # client up, and the escape key is left alone.
        nudge(hwnd)
        image = None
    raise ValueError('the telemetry of the client cannot be read: '
                     + repr(last))
