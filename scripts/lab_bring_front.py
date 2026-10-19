"""Bring WoW game window to foreground in current session, then screenshot."""
import ctypes
import ctypes.wintypes as wt
import time
from pathlib import Path

import win32con
import win32gui

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'

u = ctypes.windll.user32
g = ctypes.windll.gdi32
import struct
from PIL import Image


def find_game():
    found = []
    import win32process

    def cb(h, _):
        _, p = win32process.GetWindowThreadProcessId(h)
        if p == 31568 or win32gui.GetClassName(h) == 'GxWindowClassD3d':
            found.append((h, win32gui.GetClassName(h), win32gui.GetWindowText(h)))
        return True
    win32gui.EnumWindows(cb, None)
    log('all matches: ' + str(found))
    for h, cls, t in found:
        if cls == 'GxWindowClassD3d':
            return h
    return 0


def log(msg):
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / 'front.log', 'a', encoding='utf-8') as f:
        f.write(str(msg) + '\n')


def main():
    log('=== run')
    h = find_game()
    if not h:
        log('no game window')
        return 1
    log('hwnd %s visible %s rect %s' % (h, win32gui.IsWindowVisible(h),
                                        win32gui.GetWindowRect(h)))
    win32gui.ShowWindow(h, win32con.SW_RESTORE)
    time.sleep(0.5)
    win32gui.SetWindowPos(h, 0, 50, 50, 800, 600,
                          win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW)
    time.sleep(0.5)
    try:
        win32gui.SetForegroundWindow(h)
    except Exception as e:
        log('SetForegroundWindow failed: %s' % e)
        # alt-key trick to unlock foreground
        import ctypes
        u.keybd_event(0x12, 0, 0, 0)
        u.keybd_event(0x12, 0, 2, 0)
        win32gui.SetForegroundWindow(h)
    time.sleep(1)
    log('foreground now: %s' % win32gui.GetForegroundWindow())
    # screenshot primary
    W, H = u.GetSystemMetrics(0), u.GetSystemMetrics(1)
    sdc = u.GetDC(0)
    mdc = g.CreateCompatibleDC(sdc)
    bmp = g.CreateCompatibleBitmap(sdc, W, H)
    g.SelectObject(mdc, bmp)
    g.BitBlt(mdc, 0, 0, W, H, sdc, 0, 0, 0x00CC0020)
    bmi = ctypes.create_string_buffer(40)
    struct.pack_into('<i', bmi, 0, 40)
    struct.pack_into('<i', bmi, 4, W)
    struct.pack_into('<i', bmi, 8, -H)
    struct.pack_into('<h', bmi, 12, 1)
    struct.pack_into('<h', bmi, 14, 24)
    stride = (W * 3 + 3) & ~3
    buf = ctypes.create_string_buffer(stride * H)
    g.GetDIBits(mdc, bmp, 0, H, buf, bmi, 0)
    Image.frombuffer('RGB', (W, H), buf.raw, 'raw', 'BGR', stride, 1).save(
        OUT / 'wow-front.png')
    u.ReleaseDC(0, sdc)
    g.DeleteDC(mdc)
    g.DeleteObject(bmp)
    log('saved wow-front.png')


if __name__ == '__main__':
    main()
