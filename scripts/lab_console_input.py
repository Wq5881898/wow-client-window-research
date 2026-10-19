"""Console automation for the 3.3.5a WoW client window (lab input).

Sends Win32 console input events to the Wow.exe console, as if typed and
Enter-pressed. Used to drive worldserver console commands for lab ops.
"""

from __future__ import annotations

import ctypes
import struct
import sys
import time
from ctypes import wintypes

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32

WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_RETURN = 0x0D
VK_BACK = 0x08


def find_console_window(pid: int) -> int:
    result = []
    proto = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        lpdw = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(lpdw))
        if lpdw.value == pid:
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if "console" in buf.value.lower():
                result.append(hwnd)
        return True

    user32.EnumWindows(proto(cb), 0)
    return result[0] if result else 0


def post_key(hwnd: int, vk: int) -> None:
    user32.PostMessageW(hwnd, WM_KEYDOWN, vk, 0)
    time.sleep(0.02)
    user32.PostMessageW(hwnd, WM_KEYUP, vk, 0)
    time.sleep(0.02)


def post_char(hwnd: int, ch: str) -> None:
    user32.PostMessageW(hwnd, 0x0102, ord(ch), 0)
    time.sleep(0.015)


def send_line(pid: int, text: str) -> int:
    hwnd = find_console_window(pid)
    if not hwnd:
        print(f"no console window for pid {pid}")
        return 1
    for ch in text:
        post_char(hwnd, ch)
    post_key(hwnd, VK_RETURN)
    print(f"sent to hwnd {hwnd}: {text}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: lab_console_input.py <pid> <line> [more lines...]")
        sys.exit(2)
    target = int(sys.argv[1])
    rc = 0
    for line in sys.argv[2:]:
        rc |= send_line(target, line)
        time.sleep(0.3)
    sys.exit(rc)
