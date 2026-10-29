"""Session-2: target a nearby creature by GUID and snapshot."""
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
    i.union.ki = d5.KEYBDINPUT(0x0D, 0x1C, 0, 0, None)  # VK_RETURN + sc1C
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))
    i.union.ki.dwFlags = 0x0002  # KEYEVENTF_KEYUP
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))


def slash(cmd):
    d5.press(0xBF)
    time.sleep(0.5)
    d5.clear_field()
    d5.type_text(cmd)
    time.sleep(0.8)
    send_enter()
    time.sleep(1.5)


def main():
    guid = sys.argv[1] if len(sys.argv) > 1 else '0-4164-00000000-0000-0000-00000D0F'
    scene = sys.argv[2] if len(sys.argv) > 2 else 'target_selected'
    hwnd = d5.find_game_window()
    if not hwnd:
        d5.log('no game window')
        return 1
    d5.ensure_foreground(hwnd)
    d5.press(0xBF)
    time.sleep(0.5)
    d5.clear_field()
    d5.type_text('target ' + guid)
    d5.screenshot('wow-13-target-typed.png')
    time.sleep(0.5)
    d5.screenshot('wow-13-target-typed2.png')
    i = d5.INPUT()
    i.type = 1
    i.union.ki = d5.KEYBDINPUT(0x0D, 0x1C, 0, 0, None)  # VK_RETURN + sc1C
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))
    i.union.ki.dwFlags = 0x0002  # KEYEVENTF_KEYUP
    d5.SendInput(1, ctypes.byref(i), ctypes.sizeof(d5.INPUT))
    time.sleep(1.5)
    d5.screenshot('wow-13-target.png')
    slash('wp once ' + scene)
    time.sleep(1)
    d5.screenshot('wow-13-target-snapshot.png')
    return 0


if __name__ == '__main__':
    sys.exit(main())
