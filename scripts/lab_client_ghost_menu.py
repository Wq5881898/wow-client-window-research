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
    # The ghost stands in the lower middle of the screen.
    d.right_click(960, 700)
    time.sleep(1.0)
    image = grab_desktop()
    image.save('.cache/desktop-check/ghost-menu.png')
    print('saved')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
