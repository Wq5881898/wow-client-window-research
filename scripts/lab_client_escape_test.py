"""Check whether the escape key kills the client on the login screen.

The client leaves shortly after it shows the login screen, and the driver
presses the escape key there while it tries to close a window that covers
the screen. This script presses the key on its own and watches the client.
"""
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import win32con
import lab_driver5 as d
import lab_client_restart


def wow_pids():
    out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Wow.exe', '/FO', 'CSV',
                          '/NH'], capture_output=True, text=True,
                         encoding='gbk', errors='replace')
    return [line.split(',')[1].strip('"') for line in out.stdout.splitlines()
            if line.startswith('"Wow.exe"')]


def main():
    lab_client_restart.main()
    time.sleep(45)
    print('after start        ', wow_pids(), flush=True)
    for step in range(10):
        hwnd = d.game_window()
        if not hwnd:
            print('%2d no window        %s' % (step, wow_pids()), flush=True)
            break
        d.post_key(hwnd, win32con.VK_ESCAPE)
        time.sleep(6)
        print('%2d after escape    %s' % (step, wow_pids()), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
