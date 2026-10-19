"""Session-2 lab driver v3: window mgmt + click + screenshot.

Modes:
  closehelp          -> close Connection Help dialog (click Okay / Esc)
  login <user> <pwd> -> click login edit, type, Tab, type, Enter
  shot [name]        -> foreground game window, screenshot
"""
import ctypes
import ctypes.wintypes as wt
import struct
import sys
import time
from pathlib import Path

import win32con
import win32gui
import win32process
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / 'driver3.log'

u = ctypes.windll.user32
g = ctypes.windll.gdi32


def log(*a):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(' '.join(str(x) for x in a) + '\n')


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [('wVk', wt.WORD), ('wScan', wt.WORD), ('dwFlags', wt.DWORD),
                ('time', wt.DWORD), ('dwExtraInfo', ctypes.c_void_p)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [('dx', wt.LONG), ('dy', wt.LONG), ('mouseData', wt.DWORD),
                ('dwFlags', wt.DWORD), ('time', wt.DWORD),
                ('dwExtraInfo', ctypes.c_void_p)]


class INPUTUNION(ctypes.Union):
    _fields_ = [('ki', KEYBDINPUT), ('mi', MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [('type', wt.DWORD), ('union', INPUTUNION)]


SendInput = u.SendInput


def press(vk):
    i = INPUT()
    i.type = 1
    i.union.ki = KEYBDINPUT(vk, 0, 0, 0, None)
    SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
    i.union.ki.dwFlags = win32con.KEYEVENTF_KEYUP
    SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))


def char(c):
    i = INPUT()
    i.type = 1
    i.union.ki = KEYBDINPUT(0, ord(c), win32con.KEYEVENTF_UNICODE, 0, None)
    SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
    i.union.ki.dwFlags |= win32con.KEYEVENTF_KEYUP
    SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))


def type_text(text, delay=0.07):
    for c in text:
        char(c)
        time.sleep(delay)


def click(x, y):
    u.SetCursorPos(int(x), int(y))
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


def ensure_foreground(hwnd, x=40, y=30, w=1200, h=800):
    if not win32gui.IsWindowVisible(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.5)
    r = win32gui.GetWindowRect(hwnd)
    if r[0] < -10000:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.5)
    win32gui.SetWindowPos(hwnd, 0, x, y, w, h, win32con.SWP_NOZORDER)
    time.sleep(0.5)
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception as e:
        log('SetForegroundWindow failed', e)
        u.keybd_event(0x12, 0, 0, 0)
        u.keybd_event(0x12, 0, 2, 0)
        win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.8)
    return win32gui.GetWindowRect(hwnd)


def screenshot(name):
    w = u.GetSystemMetrics(0)
    h = u.GetSystemMetrics(1)
    sdc = u.GetDC(0)
    mdc = g.CreateCompatibleDC(sdc)
    bmp = g.CreateCompatibleBitmap(sdc, w, h)
    g.SelectObject(mdc, bmp)
    g.BitBlt(mdc, 0, 0, w, h, sdc, 0, 0, 0x00CC0020)
    bmi = ctypes.create_string_buffer(40)
    struct.pack_into('<i', bmi, 0, 40)
    struct.pack_into('<i', bmi, 4, w)
    struct.pack_into('<i', bmi, 8, -h)
    struct.pack_into('<h', bmi, 12, 1)
    struct.pack_into('<h', bmi, 14, 24)
    stride = (w * 3 + 3) & ~3
    buf = ctypes.create_string_buffer(stride * h)
    lines = g.GetDIBits(mdc, bmp, 0, h, buf, bmi, 0)
    img = Image.frombuffer('RGB', (w, h), buf.raw, 'raw', 'BGR', stride, 1)
    path = OUT / name
    img.save(path)
    u.ReleaseDC(0, sdc)
    g.DeleteDC(mdc)
    g.DeleteObject(bmp)
    log('screenshot', path, 'lines', lines)
    return path


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'shot'
    hwnd = find_game_window()
    log('=== mode', mode, 'hwnd', hwnd)
    if not hwnd:
        log('no game window')
        return 1
    if mode == 'closehelp':
        r = ensure_foreground(hwnd)
        # Okay button approx client (890, 612) in 1024x768 UI
        pt = wt.POINT(890, 612)
        u.ClientToScreen(hwnd, ctypes.byref(pt))
        log('okay at', pt.x, pt.y, 'rect', r)
        click(pt.x, pt.y)
        time.sleep(1)
        screenshot('wow-03-helpclosed.png')
    elif mode == 'login':
        user = sys.argv[2] if len(sys.argv) > 2 else 'GM01'
        pwd = sys.argv[3] if len(sys.argv) > 3 else '123321'
        r = ensure_foreground(hwnd)
        # login edit approx client (382, 352) in 1024x768 UI
        pt = wt.POINT(382, 352)
        u.ClientToScreen(hwnd, ctypes.byref(pt))
        log('login edit at', pt.x, pt.y, 'rect', r)
        click(pt.x, pt.y)
        time.sleep(0.3)
        # select-all + delete
        i = INPUT()
        i.type = 1
        i.union.ki = KEYBDINPUT(win32con.VK_CONTROL, 0, 0, 0, None)
        SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
        time.sleep(0.04)
        press(ord('A'))
        i.union.ki.dwFlags = win32con.KEYEVENTF_KEYUP
        SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
        press(win32con.VK_BACK)
        time.sleep(0.2)
        type_text(user)
        time.sleep(0.4)
        press(win32con.VK_TAB)
        time.sleep(0.3)
        i.union.ki = KEYBDINPUT(win32con.VK_CONTROL, 0, 0, 0, None)
        SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
        time.sleep(0.04)
        press(ord('A'))
        i.union.ki.dwFlags = win32con.KEYEVENTF_KEYUP
        SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
        press(win32con.VK_BACK)
        time.sleep(0.2)
        type_text(pwd)
        time.sleep(0.4)
        screenshot('wow-04-before-enter.png')
        press(win32con.VK_RETURN)
        log('login submitted', user)
        time.sleep(3)
        screenshot('wow-05-after-enter.png')
    elif mode == 'shot':
        ensure_foreground(hwnd)
        screenshot(sys.argv[2] if len(sys.argv) > 2 else 'wow-shot3.png')
    return 0


if __name__ == '__main__':
    sys.exit(main())
