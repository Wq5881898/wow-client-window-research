"""Session-2: try Enter variants inside a long-text edit box."""
import ctypes
import sys
import time
from pathlib import Path

import win32con
import win32gui

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import lab_driver5 as d5

PREFIX = 'target 0-4164-00000000-0000-0000-00000EA4'


def variant_vk():
    d5.press(win32con.VK_RETURN)


def variant_sc1c():
    i = d5.INPUT()
    i.type = 1
    i.union.ki = d5.KEYBDINPUT(0, 0x1C, 0, 0, None)
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))
    i.union.ki.dwFlags = win32con.KEYEVENTF_KEYUP
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))


def variant_vk_sc():
    i = d5.INPUT()
    i.type = 1
    i.union.ki = d5.KEYBDINPUT(0x1C, 0x1C, 0, 0, None)
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))
    i.union.ki.dwFlags = win32con.KEYEVENTF_KEYUP
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))


def variant_unicode_d():
    i = d5.INPUT()
    i.type = 1
    i.union.ki = d5.KEYBDINPUT(0, 0x0D, win32con.KEYEVENTF_UNICODE, 0, None)
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))
    i.union.ki.dwFlags |= win32con.KEYEVENTF_KEYUP
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))


def variant_numpad():
    i = d5.INPUT()
    i.type = 1
    i.union.ki = d5.KEYBDINPUT(0x0D, 0x1C, 0, 0, None)  # VK_NUMLOCK/VK_RETURN + sc1C
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))
    i.union.ki.dwFlags = win32con.KEYEVENTF_KEYUP
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))


def variant_vk_ext():
    i = d5.INPUT()
    i.type = 1
    i.union.ki = d5.KEYBDINPUT(0x1C, 0x1C, 0x0100, 0, None)  # extended
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))
    i.union.ki.dwFlags = win32con.KEYEVENTF_KEYUP | 0x0100
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))


def variant_post():
    import win32api
    hwnd = d5.find_game_window()
    win32api.PostMessage(hwnd, 0x0100, win32con.VK_RETURN, 0x1C0001)
    time.sleep(0.05)
    win32api.PostMessage(hwnd, 0x0101, win32con.VK_RETURN, 0xC1C0001)


def variant_charmsg():
    import win32api
    hwnd = d5.find_game_window()
    win32api.PostMessage(hwnd, 0x0102, 0x0D, 0x1C0001)  # WM_CHAR \r


def main():
    hwnd = d5.find_game_window()
    if not hwnd:
        d5.log('no game window')
        return 1
    d5.ensure_foreground(hwnd)
    tests = [('char', variant_charmsg)]
    for name, fn in tests:
        d5.press(0xBF)
        time.sleep(0.5)
        d5.clear_field()
        d5.type_text(PREFIX)
        time.sleep(0.6)
        fn()
        time.sleep(1.5)
        d5.screenshot('ent2-%s.png' % name)
    return 0


if __name__ == '__main__':
    sys.exit(main())
