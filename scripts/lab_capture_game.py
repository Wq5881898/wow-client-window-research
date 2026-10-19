"""Capture WoW game window from interactive session."""
import ctypes
import struct
import sys
import time
from ctypes import wintypes
from pathlib import Path

import win32gui
import win32process
from PIL import Image

u = ctypes.windll.user32
g = ctypes.windll.gdi32

def main():
    pid = int(sys.argv[1])
    out = Path(sys.argv[2])
    wins = []
    def cb(hwnd, _):
        _, p = win32process.GetWindowThreadProcessId(hwnd)
        if p == pid:
            wins.append(hwnd)
        return True
    win32gui.EnumWindows(cb, None)
    print(f'found windows: {[(h, win32gui.GetWindowText(h)) for h in wins]}')
    # find the GxWindowClassD3d or the visible one with title WoW
    target = 0
    for h in wins:
        cls = win32gui.GetClassName(h)
        title = win32gui.GetWindowText(h)
        if cls == 'GxWindowClassD3d' or (title == 'World of Warcraft' and win32gui.IsWindowVisible(h)):
            target = h
            break
    if not target:
        print('no game window found')
        return 1
    print(f'target hwnd={target} class={win32gui.GetClassName(target)} visible={win32gui.IsWindowVisible(target)}')
    rect = wintypes.RECT()
    u.GetWindowRect(target, ctypes.byref(rect))
    w, ht = rect.right - rect.left, rect.bottom - rect.top
    print(f'rect: {w}x{ht}')
    dc = u.GetWindowDC(target)
    mdc = g.CreateCompatibleDC(dc)
    bmp = g.CreateCompatibleBitmap(dc, w, ht)
    g.SelectObject(mdc, bmp)
    ok = u.PrintWindow(target, mdc, 0)
    bmi = ctypes.create_string_buffer(40)
    struct.pack_into('<i', bmi, 0, 40)
    struct.pack_into('<i', bmi, 4, w)
    struct.pack_into('<i', bmi, 8, -ht)
    struct.pack_into('<h', bmi, 12, 1)
    struct.pack_into('<h', bmi, 14, 32)
    buf = ctypes.create_string_buffer(w * ht * 4)
    lines = g.GetDIBits(mdc, bmp, 0, ht, buf, bmi, 0)
    img = Image.frombuffer('RGBA', (w, ht), buf.raw, 'raw', 'BGRA', 0, 1).convert('RGB')
    img.save(out)
    print(f'PrintWindow={ok} lines={lines} extrema={img.convert("L").getextrema()} saved={out}')
    u.ReleaseDC(target, dc)
    return 0

if __name__ == '__main__':
    sys.exit(main())
