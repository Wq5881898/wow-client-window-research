"""Try to keep the client above the other windows.

In the fullscreen mode the client draws on the whole screen but it is not
exclusive: another window can cover it and then a click of the driver would
land in that window. The client keeps a real window of the size of the
screen, so raising that window should keep the client on top. This script
raises it and checks that the client survives and that the desktop shows the
game afterwards.
"""
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import win32con
import win32gui
from client_capture import grab_desktop, grab_window
import lab_driver5 as d

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'


def wow_pids():
    out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Wow.exe', '/FO', 'CSV',
                          '/NH'], capture_output=True, text=True,
                         encoding='gbk', errors='replace')
    return [line.split(',')[1].strip('"') for line in out.stdout.splitlines()
            if line.startswith('"Wow.exe"')]


def main():
    hwnd = d.game_window()
    print('window rect', win32gui.GetWindowRect(hwnd), 'pid', wow_pids(),
          flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    grab_desktop().save(OUT / 'top-01-before.png')
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                           win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
                           | win32con.SWP_NOACTIVATE)
    time.sleep(2.0)
    print('after raise    ', win32gui.GetWindowRect(hwnd), 'pid', wow_pids(),
          flush=True)
    grab_desktop().save(OUT / 'top-02-after.png')
    image = grab_window(hwnd)
    image.save(OUT / 'top-03-window.png')
    print('window capture', image.size, 'pid', wow_pids(), flush=True)
    time.sleep(20)
    print('20s later      ', 'pid', wow_pids(), flush=True)
    grab_desktop().save(OUT / 'top-04-later.png')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
