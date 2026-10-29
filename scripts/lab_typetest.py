"""Test WM_KEYDOWN-typing vs WM_CHAR-typing after PostMessage-open."""
import sys
import time
from pathlib import Path

import win32con
import win32gui

sys.path.insert(0, r'C:\APP\opencode\project\WoW自动化预研\scripts')
import lab_driver5 as d

LOG = Path(r'C:\APP\opencode\project\WoW自动化预研\.cache\desktop-check\typetest3.log')

VKMAP = {}
for name, vk in [('W', 0x57), ('O', 0x4F), ('P', 0x50), ('R', 0x52), ('B', 0x42),
                 ('E', 0x45), ('S', 0x53), ('T', 0x54), ('A', 0x41), ('U', 0x55)]:
    VKMAP[name] = vk


def log(*a):
    line = ' '.join(str(x) for x in a)
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def type_vk(hwnd, text, delay=0.06):
    for c in text.upper():
        vk = VKMAP.get(c)
        if vk is None:
            continue
        d.post_key(hwnd, vk)
        time.sleep(delay)


def main():
    hwnd = d.find_game_window()
    log('--- typetest3 start hwnd', hwnd)
    if not hwnd:
        return 1
    # variant A: WM_KEYDOWN typing
    d.post_key(hwnd, 0x1B)
    time.sleep(0.5)
    d.post_key(hwnd, 0xBF, 0x0E)
    time.sleep(0.5)
    for _ in range(60):
        d.post_key(hwnd, 0x0E)
    time.sleep(0.3)
    type_vk(hwnd, 'wowprobe')
    time.sleep(0.4)
    d.screenshot('tt3-vk.png')
    log('variant vk done')
    # variant B: WM_CHAR typing
    d.post_key(hwnd, 0x1B)
    time.sleep(0.5)
    d.post_key(hwnd, 0xBF, 0x0E)
    time.sleep(0.5)
    for _ in range(60):
        d.post_key(hwnd, 0x0E)
    time.sleep(0.3)
    d.type_text3(hwnd, 'wowprobe')
    time.sleep(0.4)
    d.screenshot('tt3-char.png')
    log('variant char done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
