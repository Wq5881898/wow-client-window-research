"""Try to select a hostile and report what the client does.

The chat input of the client may still be open, and a command that goes
into a text field does not reach the client. The screen is captured after
every step so the state can be read.
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
from client_chat_guard import ensure_chat_closed

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'


def shot(name):
    path = OUT / ('target-diag-' + name + '.png')
    grab_desktop().save(path)
    return path


def read_state():
    try:
        return decode(assert_real_frame(grab_desktop()))
    except Exception as exc:
        return {'error': repr(exc)}


def send(hwnd, text, settle=2.0):
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.6)
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.04)
    time.sleep(0.2)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(settle)


def main():
    hwnd = d.game_window()
    d.ensure_foreground(hwnd)
    print('before', read_state())
    print('closed chat:', ensure_chat_closed(hwnd, read_state))
    print('after esc', read_state())
    shot('01-before')
    send(hwnd, '/target Diseased Young Wolf')
    print('after target', read_state())
    shot('02-target')
    send(hwnd, '/target nearest')
    print('after nearest', read_state())
    shot('03-nearest')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
