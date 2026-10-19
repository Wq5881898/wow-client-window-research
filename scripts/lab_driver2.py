"""Session-2 lab driver v2: launch / status / capture / type.

Modes:
  launch [user pwd]   -> start Wow.exe (if not running), wait, screenshot
  status              -> list windows of Wow pid, screenshot
  shot                -> screenshot only
  type user pwd       -> SendInput login flow
All screenshots use BitBlt of the virtual screen (works inside interactive session).
"""
import ctypes
import ctypes.wintypes as wt
import struct
import subprocess
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
GAME = Path(r'C:\Azerothcore\wowclient\WOW_3.3.5a')
LOG = OUT / 'driver2.log'

u = ctypes.windll.user32
g = ctypes.windll.gdi32


def log(*a):
    line = ' '.join(str(x) for x in a)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


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


def clear_field():
    i = INPUT()
    i.type = 1
    i.union.ki = KEYBDINPUT(win32con.VK_CONTROL, 0, 0, 0, None)
    SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
    time.sleep(0.04)
    press(ord('A'))
    time.sleep(0.04)
    i.union.ki.dwFlags = win32con.KEYEVENTF_KEYUP
    SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
    time.sleep(0.04)
    press(win32con.VK_BACK)
    time.sleep(0.04)


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


def wow_pids():
    pids = []

    def cb(h, _):
        _, p = win32process.GetWindowThreadProcessId(h)
        t = win32gui.GetWindowText(h)
        if t == 'World of Warcraft' and p not in pids:
            pids.append(p)
        return True
    win32gui.EnumWindows(cb, None)
    return pids


def find_game_window():
    found = []

    def cb(hwnd, _):
        if win32gui.GetClassName(hwnd) == 'GxWindowClassD3d':
            found.append(hwnd)
        return True
    win32gui.EnumWindows(cb, None)
    return found[0] if found else 0


def screenshot(name):
    # capture primary monitor only (multi-monitor virtual screen yields
    # tiled/garbage BitBlt when RDP/virtual displays are attached)
    w = u.GetSystemMetrics(0)   # SM_CXSCREEN
    h = u.GetSystemMetrics(1)   # SM_CYSCREEN
    left, top = 0, 0
    sdc = u.GetDC(0)
    mdc = g.CreateCompatibleDC(sdc)
    bmp = g.CreateCompatibleBitmap(sdc, w, h)
    g.SelectObject(mdc, bmp)
    g.BitBlt(mdc, 0, 0, w, h, sdc, left, top, 0x00CC0020)  # SRCCOPY|CAPTUREBLT
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
    log('screenshot', path, 'size', (w, h), 'lines', lines)
    return path


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'status'
    log('=== mode', mode, 'session', ctypes.windll.kernel32.WTSGetActiveConsoleSessionId())
    if mode == 'launch':
        if not wow_pids():
            subprocess.Popen([str(GAME / 'Wow.exe')], cwd=str(GAME))
            log('launched, waiting 25s')
            time.sleep(25)
        hwnd = find_game_window()
        log('after launch game hwnd', hwnd)
        screenshot('wow-01-launched.png')
    elif mode == 'shot':
        screenshot('wow-shot.png')
    elif mode == 'status':
        pids = wow_pids()
        hwnd = find_game_window()
        wins = []
        if pids:
            def cb(h, _):
                _, p = win32process.GetWindowThreadProcessId(h)
                if p in pids:
                    wins.append((h, win32gui.GetClassName(h), win32gui.GetWindowText(h)))
                return True
            win32gui.EnumWindows(cb, None)
        log('pids', pids, 'hwnd', hwnd, 'wins', wins)
        screenshot('wow-status.png')
    elif mode == 'type':
        user = sys.argv[2] if len(sys.argv) > 2 else 'GM01'
        pwd = sys.argv[3] if len(sys.argv) > 3 else '123321'
        hwnd = find_game_window()
        if not hwnd:
            log('no game window')
            return 1
        if not win32gui.IsWindowVisible(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.5)
        r = win32gui.GetWindowRect(hwnd)
        log('hwnd', hwnd, 'rect', r)
        if r[0] < -10000:  # minimized: restore and place onscreen
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.5)
            win32gui.SetWindowPos(hwnd, 0, 50, 50, 800, 600,
                                  win32con.SWP_NOZORDER)
            time.sleep(1)
            r = win32gui.GetWindowRect(hwnd)
            log('after restore rect', r)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(1.0)
        # client(382,352) -> screen: add border offset; use ClientToScreen
        pt = wt.POINT(382, 352)
        u.ClientToScreen(hwnd, ctypes.byref(pt))
        log('click at', pt.x, pt.y)
        click(pt.x, pt.y)
        time.sleep(0.3)
        clear_field()
        type_text(user)
        time.sleep(0.4)
        press(win32con.VK_TAB)
        time.sleep(0.3)
        clear_field()
        type_text(pwd)
        time.sleep(0.4)
        press(win32con.VK_RETURN)
        log('login flow sent', user)
        time.sleep(2)
        screenshot('wow-02-logged.png')
    return 0


if __name__ == '__main__':
    sys.exit(main())
