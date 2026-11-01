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


def close_world_map(hwnd, reader=None):
    """Close the world map of the client.

    The map covers the whole screen, so the telemetry of the probe cannot be
    read while it is open. A stray click on the map button opens it. The
    close button of the map window is clicked, because the key that toggles
    the map does not always reach the client.
    """
    ensure_focus(hwnd)
    for _ in range(3):
        if reader is None:
            break
        try:
            reader()
            return True
        except Exception:
            pass
        # The close button of the map window sits in the top right corner.
        d.click_si(1857, 45)
        time.sleep(0.9)
        d.post_key(hwnd, win32con.VK_ESCAPE)
        time.sleep(0.5)
    return reader is None


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
