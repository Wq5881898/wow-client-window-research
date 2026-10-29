"""Session-2: click via SendInput absolute coords (normalized 0..65535)."""
import ctypes
import sys
import time
import win32con
import win32gui
import win32api
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import lab_driver5 as d5

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


def click_norm(x, y):
    vx = ctypes.windll.user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    vy = ctypes.windll.user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    vw = ctypes.windll.user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    vh = ctypes.windll.user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    nx = int((x - vx) * 65535 / max(vw - 1, 1))
    ny = int((y - vy) * 65535 / max(vh - 1, 1))
    i = d5.INPUT()
    i.type = 0
    i.union.mi = d5.MOUSEINPUT(nx, ny, 0,
                               win32con.MOUSEEVENTF_MOVE | win32con.MOUSEEVENTF_ABSOLUTE,
                               0, None)
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))
    time.sleep(0.2)
    d5.log('after norm move cursor', win32gui.GetCursorPos())
    i.union.mi = d5.MOUSEINPUT(nx, ny, 0,
                               win32con.MOUSEEVENTF_LEFTDOWN | win32con.MOUSEEVENTF_ABSOLUTE,
                               0, None)
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))
    time.sleep(0.05)
    i.union.mi = d5.MOUSEINPUT(nx, ny, 0,
                               win32con.MOUSEEVENTF_LEFTUP | win32con.MOUSEEVENTF_ABSOLUTE,
                               0, None)
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))
    d5.log('clicked norm', x, y)


def main():
    x = float(sys.argv[1])
    y = float(sys.argv[2])
    hwnd = d5.find_game_window()
    d5.ensure_foreground(hwnd)
    click_norm(x, y)
    time.sleep(1)
    d5.screenshot('wow-15-normclick.png')
    return 0


if __name__ == '__main__':
    sys.exit(main())
