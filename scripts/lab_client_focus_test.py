"""Check whether the client survives a call that brings it to the front.

The client of the fullscreen mode keeps a small window at the top left of
the virtual desktop. The code that brings the client to the front must not
touch that window, or the client leaves.
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_driver5 as d


def main():
    hwnd = d.game_window()
    left, top, right, bottom = d.win32gui.GetWindowRect(hwnd)
    print('window rect', (left, top, right, bottom))
    if '--restore' in sys.argv:
        d.win32gui.ShowWindow(hwnd, d.win32con.SW_RESTORE)
        time.sleep(1.0)
        print('SW_RESTORE done')
    if '--foreground' in sys.argv:
        d.ensure_foreground(hwnd)
        print('ensure_foreground done')
    time.sleep(3.0)
    import win32gui
    try:
        print('rect after', win32gui.GetWindowRect(hwnd))
    except Exception as exc:
        print('rect after failed:', exc)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
