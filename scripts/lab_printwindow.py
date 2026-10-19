"""PrintWindow capture for a window owned by a given PID (lab observation)."""
import sys
import time
import ctypes
import struct
from ctypes import wintypes
from PIL import Image
import win32gui, win32process

u = ctypes.windll.user32
g = ctypes.windll.gdi32

def main():
    pid = int(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else "wow_pw.png"
    hwnds = []
    def cb(h, o):
        try:
            _, p = win32process.GetWindowThreadProcessId(h)
        except Exception:
            return True
        if p == pid:
            o.append(h)
        return True
    win32gui.EnumWindows(cb, hwnds)
    print("wow hwnds:", hwnds)
    if not hwnds:
        return 1
    h = hwnds[0]
    win32gui.ShowWindow(h, 9)  # SW_RESTORE
    time.sleep(1)
    r = wintypes.RECT()
    u.GetWindowRect(h, ctypes.byref(r))
    w, ht = r.right - r.left, r.bottom - r.top
    print("rect:", w, ht, "visible:", win32gui.IsWindowVisible(h))
    hdc = u.GetWindowDC(h)
    mdc = g.CreateCompatibleDC(hdc)
    bmp = g.CreateCompatibleBitmap(hdc, w, ht)
    g.SelectObject(mdc, bmp)
    ok = u.PrintWindow(h, mdc, 2)
    bmi = ctypes.create_string_buffer(40)
    struct.pack_into("<i", bmi, 0, 40)
    struct.pack_into("<i", bmi, 4, w)
    struct.pack_into("<i", bmi, 8, -ht)
    struct.pack_into("<h", bmi, 12, 1)
    struct.pack_into("<h", bmi, 14, 32)
    buf = ctypes.create_string_buffer(w * ht * 4)
    got = g.GetDIBits(mdc, bmp, 0, ht, buf, bmi, 0)
    img = Image.frombuffer("RGBA", (w, ht), buf.raw, "raw", "BGRA", 0, 1).convert("RGB")
    img.save(out)
    print(f"PrintWindow={ok} DIBitsLines={got} extrema={img.convert('L').getextrema()} saved={out}")
    u.ReleaseDC(h, hdc)
    return 0

if __name__ == "__main__":
    sys.exit(main())
