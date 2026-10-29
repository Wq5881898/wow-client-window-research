"""Diagnostic v3: incremental logging to find the blocking call."""
import ctypes
import sys
import time
from pathlib import Path

import win32gui

sys.path.insert(0, r'C:\APP\opencode\project\WoW自动化预研\scripts')
import lab_driver5 as d

u = ctypes.windll.user32
LOG = Path(r'C:\APP\opencode\project\WoW自动化预研\.cache\desktop-check\diag.log')


def log(*a):
    line = ' '.join(str(x) for x in a)
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


class POINT(ctypes.Structure):
    _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]


u.WindowFromPoint.restype = ctypes.c_void_p
u.WindowFromPoint.argtypes = [POINT]


def main():
    log('--- diag3 start')
    hwnd = d.find_game_window()
    log('game hwnd', hwnd)
    if not hwnd:
        return 1
    log('step: GetForegroundWindow')
    fg = u.GetForegroundWindow()
    log('fg', fg)
    log('step: WindowFromPoint')
    cap = u.WindowFromPoint(POINT(960, 604))
    log('cap', cap)
    if fg:
        log('fg class', win32gui.GetClassName(fg), 'title', repr(win32gui.GetWindowText(fg)))
    if cap:
        log('cap class', win32gui.GetClassName(cap), 'title', repr(win32gui.GetWindowText(cap)))
    log('step: ensure_foreground')
    d.ensure_foreground(hwnd)
    log('after ensure_fg', u.GetForegroundWindow())
    log('step: click_raw 960,604')
    d.click_raw(960, 604)
    log('step: screenshot after click')
    time.sleep(2)
    d.screenshot('diag-after-click.png')
    log('step: wait 30')
    time.sleep(30)
    d.screenshot('diag-after-wait.png')
    log('done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
