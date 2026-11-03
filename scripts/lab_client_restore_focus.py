"""Try to give the client back its fullscreen window.

In the fullscreen mode the client shrinks its window when it loses the
focus, and a capture of the screen then shows the window of the user. The
client keeps a window that covers the whole screen; clicking that window
might give the client the focus back and make it expand again. The click is
only made when the point really belongs to the client.
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import win32gui
import win32process
from client_capture import grab_desktop
import lab_driver5 as d

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'
POINT = (960, 540)


def main():
    hwnd = d.game_window()
    pid = win32process.GetWindowThreadProcessId(hwnd)[1]
    report = []
    report.append('client window %s %s' % (hwnd, win32gui.GetWindowRect(hwnd)))
    under = win32gui.WindowFromPoint(POINT)
    try:
        under_pid = win32process.GetWindowThreadProcessId(under)[1]
    except Exception:
        under_pid = None
    report.append('at %s the window is %s %s %s (pid %s, client pid %s)' % (
        POINT, under, win32gui.GetClassName(under),
        win32gui.GetWindowText(under), under_pid, pid))
    if under_pid != pid:
        report.append('another window is on top, not clicking')
        (OUT / 'restore-report.txt').write_text('\n'.join(report), encoding='utf-8')
        return 1
    d.click_si(*POINT)
    time.sleep(2.0)
    report.append('after the click %s' % (win32gui.GetWindowRect(hwnd),))
    grab_desktop().save(OUT / 'restore-01.png')
    time.sleep(3.0)
    report.append('3s later %s' % (win32gui.GetWindowRect(hwnd),))
    grab_desktop().save(OUT / 'restore-02.png')
    (OUT / 'restore-report.txt').write_text('\n'.join(report), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
