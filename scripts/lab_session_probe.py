"""Check whether the interactive session can still produce live pixels."""
import time
import struct
import ctypes
import win32gui
from PIL import Image
import lab_driver5 as d

u = ctypes.windll.user32
g = ctypes.windll.gdi32


def grab(tag):
    w, h = u.GetSystemMetrics(0), u.GetSystemMetrics(1)
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
    img = Image.frombuffer('RGB', (w, h), buf.raw, 'raw', 'BGR', stride, 1)
    colors = img.getcolors(maxcolors=100000)
    d.log('session grab', tag, w, h, 'distinct', len(colors) if colors else 'many')
    return img


if __name__ == '__main__':
    hwnd = d.find_game_window()
    try:
        console = ctypes.windll.kernel32.WTSGetActiveConsoleSessionId()
    except Exception:
        console = 'unknown'
    d.log('probe hwnd', hwnd, 'console session', console)
    first = grab('t0')
    time.sleep(3)
    second = grab('t3')
    d.log('session frames differ', list(first.getdata()) != list(second.getdata()))
    first.save(d.OUT / 'session-grab-a.png')
    second.save(d.OUT / 'session-grab-b.png')
