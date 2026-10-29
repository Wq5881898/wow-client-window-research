"""Single clean attempt: open, clear, type 'wowprobe status', submit with SendInput Enter."""
import sys
import time
from pathlib import Path

sys.path.insert(0, r'C:\APP\opencode\project\WoW自动化预研\scripts')
import lab_driver5 as d

LOG = Path(r'C:\APP\opencode\project\WoW自动化预研\.cache\desktop-check\single.log')


def log(*a):
    line = ' '.join(str(x) for x in a)
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def main():
    hwnd = d.find_game_window()
    log('--- single start hwnd', hwnd)
    if not hwnd:
        return 1
    d.ensure_foreground(hwnd)
    d.post_key(hwnd, 0x1B)
    time.sleep(0.5)
    d.post_key(hwnd, 0xBF, 0x0E)
    time.sleep(0.5)
    for _ in range(60):
        d.post_key(hwnd, 0x0E)
    time.sleep(0.3)
    d.type_text3(hwnd, 'wowprobe once windowed_enter2')
    time.sleep(0.4)
    d.screenshot('single-typed.png')
    d.press(0x0D)
    log('enter sent')
    time.sleep(3)
    d.screenshot('single-after.png')
    return 0


if __name__ == '__main__':
    sys.exit(main())
