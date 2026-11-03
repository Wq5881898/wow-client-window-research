"""Watch the windows of the client while it starts.

The client can have more than one window of its class for a while and the
one that is on its way out has to be skipped. This script shows what the
windows look like over time, so the reason for "no game window" is visible.
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import win32gui
import lab_driver5 as d
import lab_client_restart


def windows():
    found = []

    def cb(hwnd, _):
        if win32gui.GetClassName(hwnd) == 'GxWindowClassD3d':
            alive = True
            try:
                win32gui.GetWindowRect(hwnd)
            except Exception:
                alive = False
            found.append((hwnd, alive, win32gui.GetWindowText(hwnd)))
        return True

    win32gui.EnumWindows(cb, None)
    return found


def main():
    lab_client_restart.main()
    for step in range(16):
        import subprocess
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Wow.exe',
                              '/FO', 'CSV', '/NH'], capture_output=True,
                             text=True, encoding='gbk', errors='replace')
        pids = [line.split(',')[1].strip('"') for line in out.stdout.splitlines()
                if line.startswith('"Wow.exe"')]
        print('%5.1fs pid=%s windows=%s' % (step * 5, pids, windows()),
              flush=True)
        time.sleep(5)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
