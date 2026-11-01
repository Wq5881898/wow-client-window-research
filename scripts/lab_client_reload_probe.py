"""Reload the client UI so the installed probe copy takes effect."""
import sys
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d

SOURCE = Path(r'C:\Azerothcore\wowclient\WOW_3.3.5a\Interface\AddOns\WowProbeWotLK\WowProbeLive.lua')
REPO = Path(__file__).resolve().parents[1] / 'probes' / 'WowProbeWotLK' / 'WowProbeLive.lua'


def command(hwnd, text):
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.4)
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.03)
    time.sleep(0.2)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.6)


def main():
    hwnd = d.find_game_window()
    if not hwnd:
        print('no game window')
        return 1
    if SOURCE.exists() and REPO.exists():
        if SOURCE.read_bytes() != REPO.read_bytes():
            SOURCE.write_bytes(REPO.read_bytes())
            print('probe copy refreshed')
        else:
            print('probe copy already current')
    d.ensure_foreground(hwnd)
    # Lua errors pop up a blocking dialog, so they are turned off first.
    command(hwnd, '/console scriptErrors 0')
    command(hwnd, '/run if not UnitAffectingCombat("player") then ReloadUI() end')
    time.sleep(10)
    print('reload issued')
    return 0


if __name__ == '__main__':
    sys.exit(main())
