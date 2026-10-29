"""Session-2: probe PostMessage Enter (WM_KEYDOWN/WM_CHAR) to game window."""
import ctypes
import sys
import time
from pathlib import Path

import win32con
import win32gui

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import lab_driver5 as d5


def lp(vk, sc, ext=0):
    return 1 | (sc << 16) | (ext << 24) | (0 << 29) | (0 << 30) | (1 << 31)


def post_key(hwnd, msg, vk, sc):
    win32gui.PostMessage(hwnd, msg, vk, lp(vk, sc))


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
    d5.screenshot('wow-16-typed.png')
    post_key(hwnd, win32con.WM_KEYDOWN, 0x0D, 0x1C)
    post_key(hwnd, win32con.WM_CHAR, 0x0D, 0x1C)
    post_key(hwnd, win32con.WM_KEYUP, 0x0D, 0x1C)
    d5.log('posted WM_KEYDOWN/CHAR/UP RETURN')
    time.sleep(1.5)
    d5.screenshot('wow-16-after.png')
    return 0


if __name__ == '__main__':
    sys.exit(main())
