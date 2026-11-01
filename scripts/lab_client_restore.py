"""Restore the client window inside the interactive session and log it in.

All window manipulation must run in the session that owns the game window.
"""
import json
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'
GAME = r'C:\Azerothcore\wowclient\WOW_3.3.5a\Wow.exe'


def evidence(name):
    d.screenshot(name + '.png')
    return str(OUT / (name + '.png'))


def work_area():
    left, top, right, bottom = win32gui.GetWindowRect(win32gui.GetDesktopWindow())
    return left, top, right, bottom


def main():
    result = dict(status='FAILED', evidence=[], notes=[])
    hwnd = d.find_game_window()
    if not hwnd:
        import subprocess
        subprocess.Popen([GAME], cwd=str(Path(GAME).parent))
        time.sleep(30)
        hwnd = d.find_game_window()
        if not hwnd:
            raise RuntimeError('client did not start')
    result['hwnd'] = hwnd
    result['work_area'] = work_area()
    result['evidence'].append(evidence('restore-01-window'))

    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    time.sleep(0.6)
    # Fit the window inside the work area so the whole client is visible.
    left, top, right, bottom = work_area()
    width, height = right - left, bottom - top
    win32gui.SetWindowPos(hwnd, 0, left, top, width, height, win32con.SWP_NOZORDER)
    time.sleep(1.5)
    result['rect'] = win32gui.GetWindowRect(hwnd)
    d.ensure_foreground(hwnd)
    time.sleep(1.2)
    result['evidence'].append(evidence('restore-02-fitted'))
    result['status'] = 'WINDOW_FITTED'
    path = ROOT / 'results' / ('client_restore_' + str(time.time_ns()) + '.json')
    with path.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
