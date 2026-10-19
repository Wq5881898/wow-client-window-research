"""List WoW windows, close modal dialogs, and capture the active game window."""
import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path

import win32con
import win32gui
import win32process
from PIL import Image

u = ctypes.windll.user32
g = ctypes.windll.gdi32

def windows_for_pid(pid):
    found = []
    def cb(hwnd, _):
        _, actual = win32process.GetWindowThreadProcessId(hwnd)
        if actual == pid:
            found.append(hwnd)
        return True
    win32gui.EnumWindows(cb, None)
    return found

def children(hwnd):
    found = []
    def cb(child, _):
        text = win32gui.GetWindowText(child)
        if text:
            found.append((child, text))
        return True
    win32gui.EnumChildWindows(hwnd, cb, None)
    return found

def close_dialogs(pid):
    for hwnd in windows_for_pid(pid):
        for child, text in children(hwnd):
            class_name = win32gui.GetClassName(child)
            if class_name == 'Button' and text in ('确定', 'OK'):
                win32gui.PostMessage(child, win32con.BM_CLICK, 0, 0)
                print(f'closed dialog button: {child} {text}')

def capture(pid, path):
    hwnd = next((x for x in windows_for_pid(pid) if win32gui.GetWindowText(x) == 'World of Warcraft'), 0)
    if not hwnd:
        print('no WoW window')
        return 1
    rect = wintypes.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    if w < 32 or h < 32:
        print(f'window too small: {w}x{h}, hwnd={hwnd}, visible={win32gui.IsWindowVisible(hwnd)}')
        return 2
    dc = u.GetWindowDC(hwnd)
    memory = g.CreateCompatibleDC(dc)
    bitmap = g.CreateCompatibleBitmap(dc, w, h)
    g.SelectObject(memory, bitmap)
    ok = u.PrintWindow(hwnd, memory, 0)
    info = ctypes.create_string_buffer(40)
    import struct
    struct.pack_into('<i', info, 0, 40)
    struct.pack_into('<i', info, 4, w)
    struct.pack_into('<i', info, 8, -h)
    struct.pack_into('<h', info, 12, 1)
    struct.pack_into('<h', info, 14, 32)
    buffer = ctypes.create_string_buffer(w * h * 4)
    lines = g.GetDIBits(memory, bitmap, 0, h, buffer, info, 0)
    image = Image.frombuffer('RGBA', (w, h), buffer.raw, 'raw', 'BGRA', 0, 1).convert('RGB')
    image.save(path)
    print(f'captured hwnd={hwnd} ok={ok} lines={lines} extrema={image.convert("L").getextrema()} file={path}')
    return 0

if __name__ == '__main__':
    pid = int(sys.argv[1])
    path = Path(sys.argv[2])
    close_dialogs(pid)
    time.sleep(1)
    sys.exit(capture(pid, path))
