"""Keep the chat input out of the way of the movement keys.

While the chat input of the client is open, every key press goes into the
text field instead of reaching the character. That is why the driver has to
close the chat before it moves, and the probe reports whether the chat is
open in the chat_open field.

The focus matters as well. The scheduled tasks run a console window, and a
hidden console can still be the foreground window. The keyboard input of the
system then goes to the console instead of the client, so the client never
sees the key press. Every input therefore has to make sure that the client
window is the foreground one.
"""
import time
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_geometry import picture_to_screen


def client_has_focus(hwnd):
    """True when the client window is the foreground window."""
    return win32gui.GetForegroundWindow() == hwnd


def ensure_focus(hwnd):
    """Bring the client window to the front. Returns True on success."""
    if client_has_focus(hwnd):
        return True
    d.ensure_foreground(hwnd)
    time.sleep(0.3)
    return client_has_focus(hwnd)


def chat_open(reader):
    """True when the chat input of the client is open."""
    try:
        return bool(reader()['chat_open'])
    except Exception:
        return False


def close_chat(hwnd, reader, attempts=3):
    """Close the chat input if it is open. Returns True when it is closed."""
    for _ in range(attempts):
        if not chat_open(reader):
            return True
        ensure_focus(hwnd)
        d.post_key(hwnd, win32con.VK_ESCAPE)
        time.sleep(0.4)
    return not chat_open(reader)

def ensure_chat_closed(hwnd, reader):
    """Close the chat and report when that was not possible."""
    if close_chat(hwnd, reader):
        return True
    raise ValueError('the chat input of the client stays open')


# The button that closes the game menu of the client, in the coordinates of
# the picture of the client.
RETURN_TO_GAME = (959, 649)


def ensure_no_modal(hwnd, reader):
    """Close the menu of the client when it covers the screen.

    The game menu is modal: it covers a part of the telemetry strip of the
    probe, so nothing can be read while it is open. The escape key closes
    it, and the button is the second try for the case that the client did
    not take the key.
    """
    for _ in range(3):
        try:
            reader()
            return True
        except Exception:
            pass
        ensure_focus(hwnd)
        d.post_key(hwnd, win32con.VK_ESCAPE)
        time.sleep(0.6)
        try:
            reader()
            return True
        except Exception:
            pass
        try:
            d.click_si(*picture_to_screen(hwnd, *RETURN_TO_GAME))
        except Exception:
            pass
        time.sleep(0.9)
    return False


# The close button of the world map window, in the coordinates of the 1920
# wide picture of the client. It sits in the top right corner of the map
# window.
WORLD_MAP_CLOSE = (1719, 25)


def world_map_open(image):
    """True when the world map covers the screen.

    The map is a window of its own with a dark frame around the parchment.
    The game world never shows that frame, so a horizontal band of near
    black pixels below the top bar tells the two apart.
    """
    band = image.crop((1660, 20, 1800, 90)).convert('RGB')
    dark = 0
    for r, g, b in band.getdata():
        if r < 60 and g < 60 and b < 60:
            dark += 1
    return dark > 200


def close_world_map(hwnd, reader=None):
    """Close the world map of the client.

    The map covers the whole screen, so the telemetry of the probe cannot be
    read while it is open. A stray click on the map button opens it. The
    escape key closes the map without touching any coordinate, so it is used
    first and the button of the map window is only a second try. The click
    is only made when the map is really on the screen, because the button
    sits in a corner that the client window uses as well.
    """
    ensure_focus(hwnd)
    for _ in range(3):
        image = None
        try:
            image = grab_desktop()
        except Exception:
            pass
        if image is not None and not world_map_open(image):
            return True
        d.post_key(hwnd, win32con.VK_ESCAPE)
        time.sleep(0.6)
        try:
            image = grab_desktop()
        except Exception:
            image = None
        if image is not None and not world_map_open(image):
            return True
        d.click_si(*picture_to_screen(hwnd, *WORLD_MAP_CLOSE))
        time.sleep(0.9)
    return True


def send_command(hwnd, text, reader, settle=1.2):
    """Type a slash command into a fresh chat input and submit it.

    The chat is closed first, so a command never lands in a text field that
    still holds something else.
    """
    ensure_chat_closed(hwnd, reader)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.5)
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.04)
    time.sleep(0.2)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(settle)
    return reader()
