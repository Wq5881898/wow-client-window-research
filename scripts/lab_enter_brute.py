"""Session-2: brute-force Enter variants to execute a pending chat command."""
import ctypes
import sys
import time
from pathlib import Path

import win32con
import win32gui

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import lab_driver5 as d5


def lp(sc, ext=0, prev=0):
    return 1 | (sc << 16) | (ext << 24) | (prev << 30)


def variants(hwnd):
    # 1) SendInput VK_NUMPADENTER
    i = d5.INPUT()
    i.type = 1
    i.union.ki = d5.KEYBDINPUT(0x0D, 0x1C, 0, 0, None)
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))
    i.union.ki.dwFlags = win32con.KEYEVENTF_KEYUP
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))
    time.sleep(0.4)
    # 2) SendInput numpad enter with extended flag
    i.union.ki = d5.KEYBDINPUT(0x6D, 0x1C, win32con.KEYEVENTF_EXTENDEDKEY, 0, None)
    i.union.ki.dwFlags = win32con.KEYEVENTF_EXTENDEDKEY
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))
    i.union.ki.dwFlags = win32con.KEYEVENTF_EXTENDEDKEY | win32con.KEYEVENTF_KEYUP
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))
    time.sleep(0.4)
    # 3) PostMessage WM_KEYDOWN/WM_KEYUP with scan code, no WM_CHAR
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, 0x0D, lp(0x1C))
    time.sleep(0.05)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, 0x0D, lp(0x1C, prev=1))
    time.sleep(0.4)
    # 4) PostMessage WM_KEYDOWN with extended scancode (0xE01C)
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, 0x0D, lp(0x1C, ext=1))
    time.sleep(0.05)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, 0x0D, lp(0x1C, ext=1, prev=1))
    time.sleep(0.4)
    # 5) WM_CHAR 13 then 10
    win32gui.PostMessage(hwnd, win32con.WM_CHAR, 13, 0)
    time.sleep(0.05)
    win32gui.PostMessage(hwnd, win32con.WM_CHAR, 10, 0)
    time.sleep(0.4)
    # 6) VK_ACCEPT / WM_KEYDOWN 0x0F? skip; 7) SendInput VK_RETURN sc000 (no scancode)
    i.union.ki = d5.KEYBDINPUT(0x0D, 0, win32con.KEYEVENTF_SCANCODE, 0, None)
    i.union.ki.dwFlags = win32con.KEYEVENTF_SCANCODE
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))
    i.union.ki.dwFlags = win32con.KEYEVENTF_SCANCODE | win32con.KEYEVENTF_KEYUP
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))
    d5.log('sent 6 enter variants')


def main():
    lua = sys.argv[1] if len(sys.argv) > 1 else 'ReturnToGame()'
    hwnd = d5.find_game_window()
    if not hwnd:
        d5.log('no game window')
        return 1
    d5.ensure_foreground(hwnd)
    d5.press(0xBF)
    time.sleep(0.4)
    d5.press(0xBF)
    time.sleep(0.5)
    d5.clear_field()
    d5.type_text('run ' + lua)
    time.sleep(0.6)
    variants(hwnd)
    time.sleep(1.5)
    d5.screenshot('wow-17-after.png')
    return 0


if __name__ == '__main__':
    sys.exit(main())
