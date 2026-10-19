"""Type login credentials into the WoW login window in the interactive session."""
import sys
import time
from pathlib import Path

import win32con
import win32gui

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'


def find_game_window():
    found = []

    def cb(hwnd, _):
        if win32gui.GetClassName(hwnd) == 'GxWindowClassD3d':
            found.append(hwnd)
        return True
    win32gui.EnumWindows(cb, None)
    return found[0] if found else 0


def send(hwnd, text):
    for ch in text:
        if ch == ' ':
            win32api_key = win32con.VK_SPACE
            win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(' '), 0)
        else:
            win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(ch), 0)
        time.sleep(0.06)
    time.sleep(0.3)
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
    time.sleep(0.05)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)
    time.sleep(0.5)


def main():
    user = sys.argv[1] if len(sys.argv) > 1 else 'GM01'
    pwd = sys.argv[2] if len(sys.argv) > 2 else '123321'
    hwnd = find_game_window()
    if not hwnd:
        print('no game window')
        return 1
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(1)
    # click account field (relative to 800x600 window: field center ~ (382,352))
    lx, ly = 382, 352
    lparam = (ly << 16) | (lx & 0xFFFF)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(0.05)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)
    time.sleep(0.4)
    send(hwnd, user)
    time.sleep(0.8)
    send(hwnd, pwd)
    print('typed', user, pwd, 'to hwnd', hwnd)
    return 0


if __name__ == '__main__':
    sys.exit(main())
