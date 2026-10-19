"""Interactive lab driver: launch WoW and capture its game window."""
import ctypes
import json
import struct
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

import win32api
import win32gui
import win32process
from PIL import Image

u = ctypes.windll.user32
g = ctypes.windll.gdi32
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'
OUT.mkdir(parents=True, exist_ok=True)
GAME = Path(r'C:\Azerothcore\wowclient\WOW_3.3.5a')


def game_windows(pid):
    """Return list of (hwnd, class, title, visible) for the given pid."""
    found = []

    def cb(hwnd, _):
        _, p = win32process.GetWindowThreadProcessId(hwnd)
        if p == pid:
            found.append((hwnd, win32gui.GetClassName(hwnd),
                          win32gui.GetWindowText(hwnd), bool(win32gui.IsWindowVisible(hwnd))))
        return True
    win32gui.EnumWindows(cb, None)
    return found


def pick_game_window(pid):
    wins = game_windows(pid)
    for h, cls, title, vis in wins:
        if cls == 'GxWindowClassD3d':
            return h, wins
    for h, cls, title, vis in wins:
        if title == 'World of Warcraft' and vis:
            return h, wins
    return 0, wins


def capture_window(hwnd, path):
    rect = wintypes.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(rect))
    w, ht = rect.right - rect.left, rect.bottom - rect.top
    dc = u.GetWindowDC(hwnd)
    mdc = g.CreateCompatibleDC(dc)
    bmp = g.CreateCompatibleBitmap(dc, w, ht)
    g.SelectObject(mdc, bmp)
    ok = u.PrintWindow(hwnd, mdc, 0)
    bmi = ctypes.create_string_buffer(40)
    struct.pack_into('<i', bmi, 0, 40)
    struct.pack_into('<i', bmi, 4, w)
    struct.pack_into('<i', bmi, 8, -ht)
    struct.pack_into('<h', bmi, 12, 1)
    struct.pack_into('<h', bmi, 14, 32)
    buf = ctypes.create_string_buffer(w * ht * 4)
    lines = g.GetDIBits(mdc, bmp, 0, ht, buf, bmi, 0)
    img = Image.frombuffer('RGBA', (w, ht), buf.raw, 'raw', 'BGRA', 0, 1).convert('RGB')
    img.save(path)
    u.ReleaseDC(hwnd, dc)
    return ok, lines, img.convert('L').getextrema(), (w, ht)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'status'
    result = {'mode': mode, 'pid': None}

    if mode == 'launch':
        args = sys.argv[2:]
        proc = subprocess.Popen([str(GAME / 'Wow.exe')] + args, cwd=str(GAME))
        result['pid'] = proc.pid
        time.sleep(25)

    # find WoW process
    pid = result['pid']
    if pid is None:
        # find running WoW in this session
        import win32process
        target = []

        def cb(h, _):
            _, p = win32process.GetWindowThreadProcessId(h)
            t = win32gui.GetWindowText(h)
            if t == 'World of Warcraft':
                target.append(p)
            return True
        win32gui.EnumWindows(cb, None)
        if not target:
            result['error'] = 'no WoW running'
            (OUT / 'driver-result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            return 1
        pid = target[0]
        result['pid'] = pid

    hwnd, wins = pick_game_window(pid)
    result['windows'] = wins
    result['game_hwnd'] = hwnd
    if hwnd:
        # restore and move to visible area (window may be off-screen after session switch)
        import win32con
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(1)
        win32gui.SetWindowPos(hwnd, 0, 50, 50, 800, 600,
                              win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW)
        time.sleep(2)
        shot = OUT / 'wow-game.png'
        ok, lines, extrema, size = capture_window(hwnd, shot)
        result['capture'] = {'ok': ok, 'lines': lines, 'extrema': extrema, 'size': size, 'file': str(shot)}

    (OUT / 'driver-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
