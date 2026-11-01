"""Capture the client inside its own session, for evidence during recovery.

A scheduled task starts with a console window that would cover the client,
so every console is hidden right before the capture.
"""
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop

OUT = Path(__file__).resolve().parents[1] / '.cache' / 'desktop-check'


def hide_consoles():
    hidden = []

    def cb(hwnd, _):
        try:
            cls = win32gui.GetClassName(hwnd)
            title = win32gui.GetWindowText(hwnd)
        except Exception:
            return True
        if cls != 'ConsoleWindowClass' and 'python.exe' not in title.lower():
            return True
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            hidden.append((hwnd, cls, title))
        except Exception:
            pass
        return True
    win32gui.EnumWindows(cb, None)
    return hidden


def main():
    hwnd = d.find_game_window()
    hidden = hide_consoles()
    if hwnd:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 0, 0, 1920, 1080,
                              win32con.SWP_NOZORDER)
    time.sleep(1.2)
    hidden2 = hide_consoles()
    time.sleep(0.4)
    image = grab_desktop()
    image.save(OUT / 'live-view.png')
    image.crop((0, 0, 960, 540)).save(OUT / 'live-view-top-left.png')
    colors = image.getcolors(maxcolors=100000)
    d.log('live view distinct', len(colors) if colors else 'many',
          'hidden consoles', len(hidden) + len(hidden2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
