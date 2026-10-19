"""Clean login flow for WoW 3.3.5 via SendInput (run in interactive session).

Assumptions verified by user via VNC: PostMessage WM_CHAR reached the edit box
but both strings landed in the account field. This script: click account field,
select-all + delete, type user, Tab, select-all + delete, type password, Enter.
"""
import sys
import time
from pathlib import Path

import win32con
import win32gui

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'

u = __import__('ctypes').windll.user32
import ctypes
import ctypes.wintypes as wt


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [('dx', wt.LONG), ('dy', wt.LONG), ('mouseData', wt.DWORD),
                ('dwFlags', wt.DWORD), ('time', wt.DWORD),
                ('dwExtraInfo', ctypes.c_void_p)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [('wVk', wt.WORD), ('wScan', wt.WORD), ('dwFlags', wt.DWORD),
                ('time', wt.DWORD), ('dwExtraInfo', ctypes.c_void_p)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [('uMsg', wt.DWORD), ('wParamL', wt.WORD), ('wParamH', wt.WORD)]


class INPUTUNION(ctypes.Union):
    _fields_ = [('ki', KEYBDINPUT), ('mi', MOUSEINPUT), ('hi', HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [('type', wt.DWORD), ('union', INPUTUNION)]


SendInput = u.SendInput


def key(vk, up=False):
    i = INPUT()
    i.type = 1
    i.union.ki = KEYBDINPUT(vk, 0, 0, 0, None)
    SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
    if up:
        i.union.ki.dwFlags = win32con.KEYEVENTF_KEYUP
        SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))


def press(vk):
    key(vk, up=True)


def char(c):
    i = INPUT()
    i.type = 1
    i.union.ki = KEYBDINPUT(0, 0, win32con.KEYEVENTF_UNICODE, 0, None)
    i.union.ki.wScan = ord(c)
    SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
    i.union.ki.dwFlags |= win32con.KEYEVENTF_KEYUP
    SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))


def type_text(text, delay=0.07):
    for c in text:
        char(c)
        time.sleep(delay)


def enter():
    press(win32con.VK_RETURN)


def tab():
    press(win32con.VK_TAB)


def clear_field():
    # Ctrl+A then Delete
    key(win32con.VK_CONTROL)
    time.sleep(0.05)
    press(ord('A'))
    time.sleep(0.05)
    key(win32con.VK_CONTROL, up=True)
    time.sleep(0.05)
    press(win32con.VK_BACK)
    time.sleep(0.05)


def click(hwnd, x, y):
    # move cursor to screen coord then real click via SendInput
    r = win32gui.GetWindowRect(hwnd)
    sx, sy = r[0] + x, r[1] + y
    ctypes.windll.user32.SetCursorPos(sx, sy)
    time.sleep(0.15)
    i = INPUT()
    i.type = 0
    i.union.mi = MOUSEINPUT(0, 0, 0, win32con.MOUSEEVENTF_LEFTDOWN, 0, None)
    SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
    time.sleep(0.05)
    i.union.mi.dwFlags = win32con.MOUSEEVENTF_LEFTUP
    SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))


def find_game_window():
    found = []

    def cb(hwnd, _):
        if win32gui.GetClassName(hwnd) == 'GxWindowClassD3d':
            found.append(hwnd)
        return True
    win32gui.EnumWindows(cb, None)
    return found[0] if found else 0


def main():
    user = sys.argv[1] if len(sys.argv) > 1 else 'GM01'
    pwd = sys.argv[2] if len(sys.argv) > 2 else '123321'
    hwnd = find_game_window()
    log = {'hwnd': hwnd}
    if not hwnd:
        print('no game window')
        return 1
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(1.0)
    # account field center in 800x600 client area
    click(hwnd, 382, 352)
    time.sleep(0.3)
    clear_field()
    type_text(user)
    time.sleep(0.4)
    tab()
    time.sleep(0.3)
    clear_field()
    type_text(pwd)
    time.sleep(0.4)
    enter()
    print('login flow sent:', user, '->', hwnd)
    return 0


if __name__ == '__main__':
    sys.exit(main())
