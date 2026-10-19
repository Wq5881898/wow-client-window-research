"""Capture the WoW client window (or full screen) for lab observation."""
import sys
import time
import ctypes
from ctypes import wintypes
from PIL import ImageGrab

user32 = ctypes.windll.user32

def find_window(pid=None, title_sub=None):
    result = []
    EnumWindows = user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    GetWindowText = user32.GetWindowTextW
    GetWindowThreadProcessId = user32.GetWindowThreadProcessId
    IsWindowVisible = user32.IsWindowVisible
    def cb(hwnd, lparam):
        if not IsWindowVisible(hwnd):
            return True
        pid_out = wintypes.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid_out))
        buf = ctypes.create_unicode_buffer(256)
        GetWindowText(hwnd, buf, 256)
        if (pid is None or pid_out.value == pid) and (title_sub is None or title_sub.lower() in (buf.value or "").lower()):
            result.append((hwnd, pid_out.value, buf.value))
        return True
    EnumWindows(EnumWindowsProc(cb), 0)
    return result

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "shot.png"
    hwnds = find_window(title_sub="wow") or find_window(title_sub="world of warcraft") or find_window(title_sub="warcraft")
    if hwnds:
        hwnd, pid, title = hwnds[0]
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        img = ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom))
        print(f"window: hwnd={hwnd} pid={pid} title={title!r} rect=({rect.left},{rect.top},{rect.right},{rect.bottom})")
    else:
        img = ImageGrab.grab()
        print("window not found, full screen")
    img.save(out)
    print(f"saved: {out} size={img.size}")

if __name__ == "__main__":
    main()
