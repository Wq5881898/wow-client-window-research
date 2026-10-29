"""Bounded movement and read-only range snapshots in the interactive session."""
import ctypes
import sys
import time

import lab_driver5 as d


def command(hwnd, text):
    d.post_key(hwnd, 0x0D)
    time.sleep(0.8)
    d.type_text3(hwnd, text)
    time.sleep(0.5)
    d.screenshot('distance-command-typed.png')
    d.post_key(hwnd, 0x0D)
    time.sleep(1.5)
    d.log('distance command', text)


def hold(vk, seconds):
    if not 0 < seconds <= 4:
        raise ValueError('movement duration must be in (0, 4]')
    i = d.INPUT()
    i.type = 1
    i.union.ki = d.KEYBDINPUT(vk, 0, 0, 0, None)
    try:
        if d.SendInput(1, ctypes.byref(i), ctypes.sizeof(i)) != 1:
            raise RuntimeError('movement key down failed')
        time.sleep(seconds)
    finally:
        i.union.ki.dwFlags = 2
        if d.SendInput(1, ctypes.byref(i), ctypes.sizeof(i)) != 1:
            raise RuntimeError('movement key up failed')
    time.sleep(0.8)


def main():
    mode = sys.argv[1]
    scene = sys.argv[2]
    hwnd = d.find_game_window()
    if not hwnd:
        return 1
    d.ensure_foreground(hwnd)
    command(hwnd, '/run GameMenuFrame:Hide()')
    if mode == 'baseline':
        command(hwnd, '/targetexact Lothos Riftwaker')
    elif mode == 'recover':
        command(hwnd, '.go creature id 14387')
        time.sleep(3)
    elif mode in ('back', 'forward'):
        hold(0x53 if mode == 'back' else 0x57, float(sys.argv[3]))
    elif mode != 'shot':
        raise ValueError(mode)
    if mode != 'baseline':
        command(hwnd, '/targetexact Lothos Riftwaker')
    command(hwnd, '/wp once ' + scene)
    d.screenshot(scene + '.png')
    command(hwnd, '/reload')
    time.sleep(8)
    return 0


if __name__ == '__main__':
    sys.exit(main())
