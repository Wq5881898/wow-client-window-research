"""Check that the client window can still be observed on the desktop."""
import win32gui


def window_observable(hwnd):
    """True when the client window is visible and not minimised.

    Focus is deliberately not part of this test: a scheduled task runs
    without owning the foreground window, yet the panel is still readable.
    Pixel decoding already proves that the panel is actually on screen.
    """
    if not hwnd or not win32gui.IsWindow(hwnd):
        return False
    if win32gui.IsIconic(hwnd):
        return False
    return bool(win32gui.IsWindowVisible(hwnd))
