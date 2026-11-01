"""Capture the desktop from inside the session that owns it.

ImageGrab from another session returns a stale or blank surface, so the
capture must run where the game window lives and read the screen DC there.
"""
import ctypes
import ctypes.wintypes
import struct
import time
from PIL import Image

u = ctypes.windll.user32
g = ctypes.windll.gdi32


def grab_desktop():
    width, height = u.GetSystemMetrics(0), u.GetSystemMetrics(1)
    sdc = u.GetDC(0)
    try:
        mdc = g.CreateCompatibleDC(sdc)
        try:
            bmp = g.CreateCompatibleBitmap(sdc, width, height)
            try:
                g.SelectObject(mdc, bmp)
                if not g.BitBlt(mdc, 0, 0, width, height, sdc, 0, 0, 0x00CC0020):
                    raise RuntimeError('BitBlt failed')
                bmi = ctypes.create_string_buffer(40)
                struct.pack_into('<i', bmi, 0, 40)
                struct.pack_into('<i', bmi, 4, width)
                struct.pack_into('<i', bmi, 8, -height)
                struct.pack_into('<h', bmi, 12, 1)
                struct.pack_into('<h', bmi, 14, 24)
                stride = (width * 3 + 3) & ~3
                buffer = ctypes.create_string_buffer(stride * height)
                g.GetDIBits(mdc, bmp, 0, height, buffer, bmi, 0)
                return Image.frombuffer('RGB', (width, height), buffer.raw,
                                        'raw', 'BGR', stride, 1)
            finally:
                g.DeleteObject(bmp)
        finally:
            g.DeleteDC(mdc)
    finally:
        u.ReleaseDC(0, sdc)


def grab_window(hwnd):
    """Capture one window's own surface, independent of the desktop."""
    rect = ctypes.wintypes.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(rect))
    width, height = rect.right - rect.left, rect.bottom - rect.top
    if width <= 0 or height <= 0:
        raise RuntimeError('window has no size')
    window_dc = u.GetWindowDC(hwnd)
    try:
        mdc = g.CreateCompatibleDC(window_dc)
        try:
            bmp = g.CreateCompatibleBitmap(window_dc, width, height)
            try:
                g.SelectObject(mdc, bmp)
                g.BitBlt(mdc, 0, 0, width, height, window_dc, 0, 0, 0x00CC0020)
                bmi = ctypes.create_string_buffer(40)
                struct.pack_into('<i', bmi, 0, 40)
                struct.pack_into('<i', bmi, 4, width)
                struct.pack_into('<i', bmi, 8, -height)
                struct.pack_into('<h', bmi, 12, 1)
                struct.pack_into('<h', bmi, 14, 24)
                stride = (width * 3 + 3) & ~3
                buffer = ctypes.create_string_buffer(stride * height)
                g.GetDIBits(mdc, bmp, 0, height, buffer, bmi, 0)
                return Image.frombuffer('RGB', (width, height), buffer.raw,
                                        'raw', 'BGR', stride, 1)
            finally:
                g.DeleteObject(bmp)
        finally:
            g.DeleteDC(mdc)
    finally:
        u.ReleaseDC(hwnd, window_dc)


if __name__ == '__main__':
    import win32gui
    hwnd = win32gui.FindWindow('GxWindowClassD3d', None)
    image = grab_desktop()
    image.save('session-desktop.png')
    print('desktop', image.size)
