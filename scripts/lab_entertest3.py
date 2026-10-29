"""Probe Enter-key variants for submitting a chat command in windowed mode."""
import ctypes
import sys
import time
from pathlib import Path

import win32con

sys.path.insert(0, r'C:\APP\opencode\project\WoW自动化预研\scripts')
import lab_driver5 as d

u = ctypes.windll.user32
LOG = Path(r'C:\APP\opencode\project\WoW自动化预研\.cache\desktop-check\entertest3.log')


def log(*a):
    line = ' '.join(str(x) for x in a)
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def si_vk(vk, sc=0, flags=0):
    i = d.INPUT()
    i.type = 1
    i.union.ki = d.KEYBDINPUT(vk, sc, flags, 0, None)
    d.SendInput(1, ctypes.byref(i), ctypes.sizeof(d.INPUT))
    time.sleep(0.05)
    i.union.ki.dwFlags = flags | win32con.KEYEVENTF_KEYUP
    d.SendInput(1, ctypes.byref(i), ctypes.sizeof(d.INPUT))


def keybd_ev(vk, sc=0, flags=0):
    u.keybd_event(vk, sc, flags, 0)
    time.sleep(0.05)
    u.keybd_event(vk, sc, flags | 2, 0)


def variant(hwnd, name, send_fn):
    d.post_key(hwnd, 0x1B)
    time.sleep(0.5)
    d.post_key(hwnd, 0xBF, 0x0E)
    time.sleep(0.5)
    for _ in range(60):
        d.post_key(hwnd, 0x0E)
    time.sleep(0.3)
    d.type_text('wowprobe status')
    time.sleep(0.4)
    d.screenshot('ent3-typed-%s.png' % name)
    send_fn()
    time.sleep(2.5)
    d.screenshot('ent3-%s.png' % name)
    log('variant', name, 'done')


def main():
    hwnd = d.find_game_window()
    log('--- ent3 start hwnd', hwnd)
    if not hwnd:
        return 1
    variant(hwnd, 'sc1c', lambda: si_vk(0x0D, 0x1C))
    variant(hwnd, 'num', lambda: si_vk(0x0D, 0x1C, win32con.KEYEVENTF_EXTENDEDKEY))
    variant(hwnd, 'kb', lambda: keybd_ev(0x0D, 0x1C))
    variant(hwnd, 'kb0', lambda: keybd_ev(0x0D, 0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
