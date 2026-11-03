"""Show every window of the client with its size and what a capture of it
shows.

In the fullscreen mode the client has several windows and only one of them
holds the picture. The size of the capture tells which one it is.
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import win32gui
import win32process
from client_capture import grab_desktop, grab_window
import lab_driver5 as d

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'


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
            found.append((other, win32gui.GetClassName(other),
                          win32gui.GetWindowText(other)))
        except Exception:
            pass
        return True

    win32gui.EnumWindows(cb, None)
    return found


def main():
    hwnd = d.game_window()
    print('game window', hwnd, win32gui.GetWindowRect(hwnd), flush=True)
    for other, cls, title in client_windows(hwnd):
        try:
            rect = win32gui.GetWindowRect(other)
        except Exception:
            rect = None
        print('window %-22s %-20s %s' % (cls, title[:20], rect), flush=True)
        if rect and rect[2] - rect[0] > 400 and rect[3] - rect[1] > 300:
            try:
                image = grab_window(other)
                path = OUT / ('win-%s-%d.png' % (cls, other))
                image.save(path)
                # A picture of the game is not a single flat colour.
                colours = image.convert('RGB').getcolors(maxcolors=100000)
                print('   capture %s  colours=%s' % (image.size,
                      len(colours) if colours else 'many'), flush=True)
            except Exception as exc:
                print('   capture failed:', repr(exc)[:100], flush=True)
    grab_desktop().save(OUT / 'win-desktop.png')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
