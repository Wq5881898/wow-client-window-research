"""Open the menu of the ghost itself, which carries the release option."""
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop


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


def main():
    hwnd = d.find_game_window()
    if not hwnd:
        print('no window')
        return 1
    d.ensure_foreground(hwnd)
    hide_consoles()
    d.post_key(hwnd, win32con.VK_ESCAPE)
    time.sleep(0.5)
    # The ghost stands in the lower middle of the screen. Several points are
    # tried because the ghost is small and its exact pixel position drifts.
    for point in ((960, 630), (960, 600), (960, 660), (900, 620), (1000, 640)):
        d.right_click(*point)
        time.sleep(0.8)
        image = grab_desktop()
        if image.crop((800, 500, 1200, 800)).getbbox() is not None:
            pass
        image.save('.cache/desktop-check/ghost-menu-%d.png' % point[1])
    print('saved')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
