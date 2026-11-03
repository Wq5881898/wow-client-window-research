"""Check whether the picture of the client can be read without the desktop.

In the fullscreen mode the client draws on the whole screen and every other
window covers it, so a capture of the desktop shows the other window. The
windows of the client itself may still hold the picture. This script saves
the desktop and the windows of the client so they can be compared.
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import win32gui
import win32process
from client_capture import grab_desktop, grab_window
import lab_client_restart

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
    lab_client_restart.main()
    time.sleep(30)
    import lab_driver5 as d
    hwnd = d.game_window()
    OUT.mkdir(parents=True, exist_ok=True)
    grab_desktop().save(OUT / 'cap-desktop.png')
    print('desktop saved', flush=True)
    for other, cls, title in client_windows(hwnd):
        print('window', other, cls, title, flush=True)
        try:
            image = grab_window(other)
            image.save(OUT / ('cap-%s-%d.png' % (cls, other)))
            print('   saved', image.size, flush=True)
        except Exception as exc:
            print('   failed:', repr(exc)[:120], flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
