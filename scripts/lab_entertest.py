"""Session-2: test Enter variants for WoW chat input."""
import ctypes
import ctypes.wintypes as wt
import sys
import time
from pathlib import Path

import win32con
import win32gui

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import lab_driver5 as d5

u = ctypes.windll.user32


def vk_enter():
    d5.press(win32con.VK_RETURN)


def char_enter():
    i = d5.INPUT()
    i.type = 1
    i.union.ki = d5.KEYBDINPUT(0x1C, 0x00, 0, 0, None)  # sc1C make
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))
    i.union.ki.dwFlags = win32con.KEYEVENTF_KEYUP
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))


def char_enter_ext():
    # WM_CHAR equivalent: KEYEVENTF_UNICODE with \r
    i = d5.INPUT()
    i.type = 1
    i.union.ki = d5.KEYBDINPUT(0, 0x0D, win32con.KEYEVENTF_UNICODE, 0, None)
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))
    i.union.ki.dwFlags |= win32con.KEYEVENTF_KEYUP
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))


def main():
    hwnd = d5.find_game_window()
    if not hwnd:
        d5.log('no game window')
        return 1
    d5.ensure_foreground(hwnd)
    tests = [
        ('vkenter', vk_enter),
        ('sc1c', char_enter),
        ('unicode_d', char_enter_ext),
    ]
    for name, fn in tests:
        d5.press(0xBF)
        time.sleep(0.5)
        d5.clear_field()
        d5.type_text('test ' + name)
        time.sleep(0.6)
        fn()
        time.sleep(1.2)
        d5.screenshot('ent-%s.png' % name)
    return 0


if __name__ == '__main__':
    sys.exit(main())
