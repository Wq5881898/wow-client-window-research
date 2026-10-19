"""Capture primary monitor as 4 tiles to diagnose stride corruption."""
import ctypes
import ctypes.wintypes as wt
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'

u = ctypes.windll.user32
g = ctypes.windll.gdi32


def grab(x, y, w, h):
    sdc = u.GetDC(0)
    mdc = g.CreateCompatibleDC(sdc)
    bmp = g.CreateCompatibleBitmap(sdc, w, h)
    g.SelectObject(mdc, bmp)
    g.BitBlt(mdc, 0, 0, w, h, sdc, x, y, 0x00CC0020)
    bmi = ctypes.create_string_buffer(40)
    struct.pack_into('<i', bmi, 0, 40)
    struct.pack_into('<i', bmi, 4, w)
    struct.pack_into('<i', bmi, 8, -h)
    struct.pack_into('<h', bmi, 12, 1)
    struct.pack_into('<h', bmi, 14, 24)
    stride = (w * 3 + 3) & ~3
    buf = ctypes.create_string_buffer(stride * h)
    g.GetDIBits(mdc, bmp, 0, h, buf, bmi, 0)
    from PIL import Image
    img = Image.frombuffer('RGB', (w, h), buf.raw, 'raw', 'BGR', stride, 1)
    u.ReleaseDC(0, sdc)
    g.DeleteDC(mdc)
    g.DeleteObject(bmp)
    return img


def main():
    W = u.GetSystemMetrics(0)
    H = u.GetSystemMetrics(1)
    print('primary', W, H)
    tw, th = W // 2, H // 2
    tiles = {'tl': (0, 0), 'tr': (tw, 0), 'bl': (0, th), 'br': (tw, th)}
    for name, (x, y) in tiles.items():
        img = grab(x, y, tw, th)
        p = OUT / f'tile-{name}.png'
        img.save(p)
        print('saved', p)


if __name__ == '__main__':
    main()
