"""List all windows (visible or not) belonging to a PID, with class names."""
import sys
import ctypes
from ctypes import wintypes
import win32gui, win32process

pid = int(sys.argv[1])
out = []
def cb(h, o):
    try:
        _, p = win32process.GetWindowThreadProcessId(h)
    except Exception:
        return True
    if p == pid:
        buf = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetClassNameW(h, buf, 256)
        o.append((h, win32gui.IsWindowVisible(h), repr(win32gui.GetWindowText(h)), buf.value))
    return True
win32gui.EnumWindows(cb, out)
win32gui.EnumDesktopWindows(0, cb, out)
seen = set()
for row in out:
    if row[0] not in seen:
        seen.add(row[0])
        print(row)
