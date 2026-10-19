"""Graceful exit Wow: foreground, /exit, wait, report."""
import subprocess
import sys
import time
from pathlib import Path

import psutil
import win32con
import win32gui

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import lab_driver5 as d5


def main():
    hwnd = d5.find_game_window()
    d5.log = lambda *a: None
    if not hwnd:
        print('no game window')
        return 1
    d5.ensure_foreground(hwnd)
    d5.click_ui(hwnd, 170, 742)
    time.sleep(0.4)
    press = d5.press
    press(0xBF)
    time.sleep(0.3)
    d5.type_text('exit')
    time.sleep(0.3)
    press(win32con.VK_RETURN)
    print('exit sent')
    deadline = time.time() + 30
    while time.time() < deadline:
        alive = [p for p in psutil.process_iter(['name'])
                 if p.info['name'].lower() == 'wow.exe']
        if not alive:
            print('wow exited cleanly')
            return 0
        time.sleep(1)
    print('wow still alive')
    return 1


if __name__ == '__main__':
    sys.exit(main())
