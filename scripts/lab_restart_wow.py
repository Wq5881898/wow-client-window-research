"""Restart Wow.exe in current (interactive) session."""
import subprocess
import sys
import time
from pathlib import Path

import psutil
import win32con
import win32gui

GAME = Path(r'C:\Azerothcore\wowclient\WOW_3.3.5a')
ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / '.cache' / 'desktop-check' / 'restart.log'


def log(*a):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(' '.join(str(x) for x in a) + '\n')


def main():
    log('=== restart')
    for p in psutil.process_iter(['name', 'pid']):
        try:
            if p.info['name'].lower() == 'wow.exe':
                log('killing', p.info['pid'])
                p.terminate()
        except psutil.Error:
            pass
    deadline = time.time() + 15
    while time.time() < deadline:
        if not any(p.info['name'].lower() == 'wow.exe'
                   for p in psutil.process_iter(['name'])):
            break
        time.sleep(0.5)
    time.sleep(2)
    subprocess.Popen([str(GAME / 'Wow.exe')], cwd=str(GAME))
    log('launched, waiting 20s')
    time.sleep(20)
    found = []

    def cb(h, _):
        if win32gui.GetClassName(h) == 'GxWindowClassD3d':
            found.append(h)
        return True
    win32gui.EnumWindows(cb, None)
    log('game hwnd', found)
    if found:
        win32gui.ShowWindow(found[0], win32con.SW_RESTORE)
        time.sleep(0.5)
        win32gui.SetWindowPos(found[0], 0, 40, 30, 1200, 800,
                              win32con.SWP_NOZORDER)
    return 0


if __name__ == '__main__':
    sys.exit(main())
