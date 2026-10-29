"""Session-2: log game window handle + rect each run."""
import sys
import win32gui
import win32process
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import lab_driver5 as d5

LOG = Path(r'C:\APP\opencode\project\WoW自动化预研\.cache\desktop-check\win.log')


def log(*a):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(' '.join(str(x) for x in a) + '\n')


def main():
    h = d5.find_game_window()
    log('hwnd', h)
    if h:
        log('title', repr(win32gui.GetWindowText(h)))
        log('rect', win32gui.GetWindowRect(h))
        log('client', win32gui.GetClientRect(h))
        log('pid', win32process.GetWindowThreadProcessId(h))
    return 0


if __name__ == '__main__':
    sys.exit(main())
