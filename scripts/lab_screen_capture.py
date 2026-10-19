"""Capture the full screen of the current session (works in interactive session)."""
import sys
from pathlib import Path

import win32api
import win32con
import win32gui
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'
OUT.mkdir(parents=True, exist_ok=True)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else str(OUT / 'screen.png')
    left, top = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN), \
        win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
    w = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
    h = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
    hdesk = None  # run inside interactive session, default desktop is fine
    img = Image.new('RGB', (w, h))
    import ctypes
    u = ctypes.windll.user32
    g = ctypes.windll.gdi32
    sdc = u.GetDC(0)
    mdc = g.CreateCompatibleDC(sdc)
    bmp = g.CreateCompatibleBitmap(sdc, w, h)
    g.SelectObject(mdc, bmp)
    ok = g.BitBlt(mdc, 0, 0, w, h, sdc, left, top,
                  win32con.SRCCOPY | getattr(win32con, 'CAPTUREBLT', 0x40000000))
    import struct
    bmi = ctypes.create_string_buffer(40)
    struct.pack_into('<i', bmi, 0, 40)
    struct.pack_into('<i', bmi, 4, w)
    struct.pack_into('<i', bmi, 8, -h)
    struct.pack_into('<h', bmi, 12, 1)
    struct.pack_into('<h', bmi, 14, 24)
    buf = ctypes.create_string_buffer(w * h * 4)
    lines = g.GetDIBits(mdc, bmp, 0, h, buf, bmi, 0)
    img = Image.frombuffer('RGB', (w, h), buf.raw, 'raw', 'BGRX', 0, 1)
    img.save(out)
    u.ReleaseDC(0, sdc)
    g.DeleteDC(mdc)
    g.DeleteObject(bmp)
    print('saved', out, 'size', (w, h), 'ok', ok, 'lines', lines)


if __name__ == '__main__':
    main()
