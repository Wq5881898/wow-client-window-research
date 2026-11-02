"""Map the coordinates of the 1920x1080 picture of the client to the screen.

The scripts click on elements of the client with the coordinates of its
picture. When the window is not the full size of the desktop, the picture is
scaled and shifted, so a raw click lands beside the element it was meant for.

The mapping is measured and not assumed: the caller passes a point that was
found in a screenshot of the desktop and the script returns the point of the
same element in the picture of the client.
"""
import ctypes
import win32gui
from ctypes import wintypes

BASE_WIDTH = 1920
BASE_HEIGHT = 1080


def is_fullscreen(hwnd):
    """True when the client draws on the whole screen.

    In the fullscreen mode the client keeps a small window at the top left
    of the virtual desktop and draws on the screen itself, so the picture of
    the client and the screen have the same pixels.
    """
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return left < -10000 or top < -10000


def client_origin(hwnd):
    """The top left corner of the client area on the screen."""
    if is_fullscreen(hwnd):
        return 0, 0
    x, y = win32gui.ClientToScreen(hwnd, (0, 0))
    return x, y


def client_size(hwnd):
    if is_fullscreen(hwnd):
        return BASE_WIDTH, BASE_HEIGHT
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    return right - left, bottom - top


def picture_to_screen(hwnd, x, y):
    """The screen position of a point of the 1920x1080 picture."""
    origin_x, origin_y = client_origin(hwnd)
    width, height = client_size(hwnd)
    scale_x = width / float(BASE_WIDTH)
    scale_y = height / float(BASE_HEIGHT)
    return (int(round(origin_x + x * scale_x)),
            int(round(origin_y + y * scale_y)))


def screen_to_picture(hwnd, x, y):
    """The position in the picture of a point of the screen."""
    origin_x, origin_y = client_origin(hwnd)
    width, height = client_size(hwnd)
    scale_x = width / float(BASE_WIDTH)
    scale_y = height / float(BASE_HEIGHT)
    return ((x - origin_x) / scale_x, (y - origin_y) / scale_y)
