"""Measure how fast the panel of the probe is updated.

The client draws very slowly when another window is in front of it, and the
panel then shows an old picture. The rate of the sequence tells how fast
the client is drawing.
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame

ROOT = Path(__file__).resolve().parents[1]


def read():
    try:
        return decode(assert_real_frame(grab_desktop()))['sequence']
    except Exception as exc:
        return 'error: ' + repr(exc)[:40]


def main():
    hwnd = d.game_window()
    d.ensure_foreground(hwnd)
    foreground = win32gui.GetForegroundWindow()
    print('game window', hwnd, 'foreground', foreground,
          'title', win32gui.GetWindowText(foreground))
    first = read()
    started = time.monotonic()
    time.sleep(4.0)
    second = read()
    elapsed = time.monotonic() - started
    print('sequence', first, '->', second, 'in', round(elapsed, 2), 's')
    if isinstance(first, int) and isinstance(second, int):
        print('updates per second', round((second - first) / elapsed, 1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
