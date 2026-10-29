"""Session2: relogin GM01 after crash-to-login. Assumes client already at login screen."""
import sys
import time
from pathlib import Path

sys.path.insert(0, r'C:\APP\opencode\project\WoW自动化预研\scripts')
import lab_driver5 as d

LOG = Path(r'C:\APP\opencode\project\WoW自动化预研\.cache\desktop-check\relogin.log')


def log(*a):
    line = ' '.join(str(x) for x in a)
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def click_screen(hwnd, x, y):
    try:
        d.click_ui(hwnd, x, y)
    except Exception:
        import traceback
        log('click EXC', traceback.format_exc())


def main():
    hwnd = d.find_game_window()
    log('--- relogin start hwnd', hwnd)
    if not hwnd:
        return 1
    d.ensure_foreground(hwnd)
    d.screenshot('rl-0-before.png')
    for _ in range(3):
        d.post_key(hwnd, 0x0D)
        time.sleep(0.4)
    d.screenshot('rl-1-ok.png')
    time.sleep(1)
    d.click_screen(hwnd, 512, 177)
    time.sleep(1)
    d.click_screen(hwnd, 512, 280)
    time.sleep(12)
    d.screenshot('rl-2-charselect.png')
    time.sleep(3)
    d.click_screen(hwnd, 512, 656)
    time.sleep(20)
    d.screenshot('rl-3-entered.png')
    return 0


if __name__ == '__main__':
    sys.exit(main())
