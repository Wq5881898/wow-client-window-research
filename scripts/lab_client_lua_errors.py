"""Turn on the display of Lua errors and capture what the client says.

The panel of the probe stops being updated now and then. The error of the
add-on is only visible when the client is told to show it, so the console
is asked for it and the chat frame is captured afterwards.
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'


def send(hwnd, text, settle=1.5):
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.6)
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.03)
    time.sleep(0.2)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(settle)


def main():
    hwnd = d.game_window()
    d.ensure_foreground(hwnd)
    send(hwnd, '/console scriptErrors 1')
    time.sleep(6.0)
    image = grab_desktop()
    image.save(OUT / 'lua-errors.png')
    image.crop((0, 700, 960, 1040)).resize((1440, 510)).save(
        OUT / 'lua-errors-chat.png')
    print('saved', OUT / 'lua-errors-chat.png')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
