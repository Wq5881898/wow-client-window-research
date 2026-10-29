"""Session-2: execute a Lua snippet via /run with guaranteed Enter, then snapshot."""
import ctypes
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import lab_driver5 as d5


def send_enter():
    i = d5.INPUT()
    i.type = 1
    i.union.ki = d5.KEYBDINPUT(0x0D, 0x1C, 0, 0, None)
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))
    i.union.ki.dwFlags = 0x0002
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))


def slash(cmd, shots=False):
    d5.press(0xBF)  # / opens chat (or closes it if open)
    time.sleep(0.4)
    d5.press(0xBF)  # ensure a fresh / prompt
    time.sleep(0.5)
    d5.clear_field()
    d5.type_text(cmd)
    time.sleep(0.6)
    if shots:
        d5.screenshot('wow-14-typed.png')
    send_enter()
    time.sleep(1.2)


def main():
    lua = sys.argv[1] if len(sys.argv) > 1 else 'print("hello")'
    hwnd = d5.find_game_window()
    if not hwnd:
        d5.log('no game window')
        return 1
    d5.ensure_foreground(hwnd)
    slash('/run ' + lua, shots=True)
    time.sleep(0.5)
    d5.screenshot('wow-14-after.png')
    return 0


if __name__ == '__main__':
    sys.exit(main())
