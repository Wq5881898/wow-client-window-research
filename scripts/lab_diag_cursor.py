"""Session-2 diagnostics: cursor movement + mss screenshot + click test."""
import ctypes
import struct
import sys
import time
from pathlib import Path

import win32con
import win32gui
import win32api
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / 'diag_cursor.log'

u = ctypes.windll.user32
g = ctypes.windll.gdi32


def log(*a):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(' '.join(str(x) for x in a) + '\n')


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [('wVk', ctypes.c_ushort), ('wScan', ctypes.c_ushort),
                ('dwFlags', ctypes.c_uint32), ('time', ctypes.c_uint32),
                ('dwExtraInfo', ctypes.c_void_p)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [('dx', ctypes.c_long), ('dy', ctypes.c_long),
                ('mouseData', ctypes.c_uint32), ('dwFlags', ctypes.c_uint32),
                ('time', ctypes.c_uint32), ('dwExtraInfo', ctypes.c_void_p)]


class INPUTUNION(ctypes.Union):
    _fields_ = [('ki', KEYBDINPUT), ('mi', MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [('type', ctypes.c_uint32), ('union', INPUTUNION)]


SendInput = u.SendInput


def find_game_window():
    found = []

    def cb(hwnd, _):
        if win32gui.GetClassName(hwnd) == 'GxWindowClassD3d':
            found.append(hwnd)
        return True
    win32gui.EnumWindows(cb, None)
    return found[0] if found else 0


def screenshot_mss(name):
    import mss
    with mss.mss() as sct:
        mon = sct.monitors[1]  # primary
        img = sct.grab(mon)
        Image.frombytes('RGB', img.size, img.rgb, 'raw', 'BGR',
                        img.width * 4, 0).save(OUT / name)
    log('mss screenshot', name, img.size)


def screenshot_gdi(name):
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
    g.GetDIBits(mdc, bmp, 0, h, buf, bmi, 0)
    Image.frombuffer('RGB', (w, h), buf.raw, 'raw', 'BGR', stride, 1).save(
        OUT / name)
    u.ReleaseDC(0, sdc)
    g.DeleteDC(mdc)
    g.DeleteObject(bmp)
    log('gdi screenshot', name, (w, h))


def main():
    log('=== diag session', ctypes.windll.kernel32.WTSGetActiveConsoleSessionId())
    hwnd = find_game_window()
    log('hwnd', hwnd)
    if not hwnd:
        return 1
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    p = win32api.GetCursorPos()
    log('cursor before', p)
    # ensure window is on screen (it may be minimized to -32000)
    if win32gui.GetWindowRect(hwnd)[0] < -10000:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.8)
    win32gui.SetWindowPos(hwnd, 0, 40, 30, 1200, 800, win32con.SWP_NOZORDER)
    time.sleep(0.5)
    log('rect after restore', win32gui.GetWindowRect(hwnd))
    u.SetCursorPos(1100, 500)
    time.sleep(0.5)
    log('cursor after SetCursorPos', win32api.GetCursorPos())
    i = INPUT()
    i.type = 0
    i.union.mi = MOUSEINPUT(50, 0, 0, win32con.MOUSEEVENTF_MOVE, 0, None)
    SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
    time.sleep(0.5)
    log('cursor after SendInput relative', win32api.GetCursorPos())
    import traceback
    try:
        screenshot_mss('diag-mss.png')
    except Exception:
        log('mss failed:', traceback.format_exc())
    screenshot_gdi('diag-gdi.png')
    # click game window center: SetCursorPos + SendInput button events
    l, t, r, b = win32gui.GetWindowRect(hwnd)
    cx, cy = (l + r) // 2, (t + b) // 2
    log('click center', cx, cy)
    u.SetCursorPos(cx, cy)
    time.sleep(0.3)
    log('cursor now', win32api.GetCursorPos())
    i.union.mi = MOUSEINPUT(0, 0, 0, win32con.MOUSEEVENTF_LEFTDOWN, 0, None)
    SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
    i.union.mi.dwFlags = win32con.MOUSEEVENTF_LEFTUP
    SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
    time.sleep(1)
    try:
        screenshot_mss('diag-after-click.png')
    except Exception:
        log('mss failed (after click):', traceback.format_exc())
    screenshot_gdi('diag-gdi2.png')
    return 0


if __name__ == '__main__':
    sys.exit(main())
