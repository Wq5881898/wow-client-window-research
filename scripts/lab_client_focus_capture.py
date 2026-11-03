"""Check that the client gives the picture of the screen once it has the focus.

In the fullscreen mode the client shrinks its window to a small one when it
loses the focus, and the picture is then only on the screen. Bringing the
client to the front should give the window its size back, and a capture of
the window should show the game.
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import win32gui
from client_capture import grab_desktop, grab_window
import lab_driver5 as d

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'


def report(hwnd, label):
    try:
        rect = win32gui.GetWindowRect(hwnd)
    except Exception as exc:
        print(label, 'no window:', repr(exc)[:80], flush=True)
        return
    try:
        image = grab_window(hwnd)
        colours = image.convert('RGB').getcolors(maxcolors=100000)
        print('%-22s rect=%s capture=%s colours=%s' % (
            label, rect, image.size, len(colours) if colours else 'many'),
            flush=True)
    except Exception as exc:
        print('%-22s rect=%s capture failed %s' % (label, rect,
              repr(exc)[:70]), flush=True)


def main():
    hwnd = d.game_window()
    report(hwnd, 'before foreground')
    grab_desktop().save(OUT / 'focus-01-before.png')
    d.ensure_foreground(hwnd)
    time.sleep(2.0)
    report(hwnd, 'after foreground')
    grab_desktop().save(OUT / 'focus-02-after.png')
    image = grab_window(hwnd)
    image.save(OUT / 'focus-03-window.png')
    print('window picture saved', image.size, flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
