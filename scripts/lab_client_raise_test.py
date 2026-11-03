"""Try to put the fullscreen client above the other windows.

The client of the fullscreen mode is not exclusive: every other window
covers it, so the picture of the screen is not the game and a click of the
driver would land in that other window. The client keeps a window that
covers the whole screen. This script raises that window, checks that the
client survives it, and then clicks on it to see whether the client gets
its focus back and expands again.
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import win32con
import win32gui
import win32process
from client_capture import grab_desktop
import lab_driver5 as d

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'
POINT = (960, 540)


def client_windows(hwnd):
    try:
        pid = win32process.GetWindowThreadProcessId(hwnd)[1]
    except Exception:
        return []
    found = []

    def cb(other, _):
        try:
            if win32process.GetWindowThreadProcessId(other)[1] != pid:
                return True
            found.append((other, win32gui.GetClassName(other)))
        except Exception:
            pass
        return True

    win32gui.EnumWindows(cb, None)
    return found


def main():
    hwnd = d.game_window()
    pid = win32process.GetWindowThreadProcessId(hwnd)[1]
    report = ['client window %s %s' % (hwnd, win32gui.GetWindowRect(hwnd))]
    proxy = 0
    for other, cls in client_windows(hwnd):
        try:
            rect = win32gui.GetWindowRect(other)
        except Exception:
            rect = None
        report.append('window %s %s' % (cls, rect))
        if cls == 'D3DProxyWindow':
            proxy = other
    if not proxy:
        report.append('no proxy window')
        (OUT / 'raise-report.txt').write_text('\n'.join(report), encoding='utf-8')
        return 1
    try:
        win32gui.SetWindowPos(proxy, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                               win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
                               | win32con.SWP_NOACTIVATE)
        report.append('raised the proxy')
    except Exception as exc:
        report.append('raising failed: %r' % (exc,))
    time.sleep(2.0)
    report.append('client window now %s' % (win32gui.GetWindowRect(hwnd),))
    under = win32gui.WindowFromPoint(POINT)
    try:
        under_pid = win32process.GetWindowThreadProcessId(under)[1]
    except Exception:
        under_pid = None
    report.append('at %s: %s %s (pid %s, client %s)' % (
        POINT, under, win32gui.GetClassName(under), under_pid, pid))
    if under_pid == pid:
        d.click_si(*POINT)
        time.sleep(2.5)
        report.append('after the click: %s' % (win32gui.GetWindowRect(hwnd),))
        grab_desktop().save(OUT / 'raise-01.png')
    else:
        report.append('not clicking, another window is on top')
    (OUT / 'raise-report.txt').write_text('\n'.join(report), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
