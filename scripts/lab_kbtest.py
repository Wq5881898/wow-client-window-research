"""Session-2 keyboard experiment: focus game, press keys, screenshot before/after."""
import sys
import time
from pathlib import Path

import win32api
import win32gui

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import lab_driver5 as d5


def main():
    hwnd = d5.find_game_window()
    if not hwnd:
        d5.log('no game window')
        return 1
    d5.ensure_foreground(hwnd)
    d5.screenshot('kb-00-before.png')
    # move cursor into viewport and click once (no drag)
    win32api.SetCursorPos((400, 300))
    time.sleep(0.3)
    d5.press(0xBF)  # slash opens chat
    time.sleep(0.3)
    d5.press(0x1B)  # escape closes chat
    time.sleep(0.3)
    for vk, name in [(0x52, 'R'), (0x45, 'E'), (0x51, 'Q'), (0x31, '1')]:
        d5.press(vk)
        time.sleep(0.6)
    time.sleep(1)
    d5.screenshot('kb-01-after.png')
    return 0


if __name__ == '__main__':
    sys.exit(main())
