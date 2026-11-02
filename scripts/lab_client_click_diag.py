"""Click on a creature in the world and see whether the probe sees it.

The target frame of the client shows a creature while the probe reports no
target. A mouse click on the creature sets the target for sure, so it tells
the two apart.
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
from client_chat_guard import ensure_no_modal

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'


def read_state():
    try:
        return decode(assert_real_frame(grab_desktop()))
    except Exception as exc:
        return {'error': repr(exc)}


def brief(state):
    keys = ('sequence', 'target_guid', 'target_exists', 'target_attackable',
            'target_health', 'target_class_name', 'chat_open')
    return {k: state.get(k) for k in keys}


def main():
    hwnd = d.game_window()
    d.ensure_foreground(hwnd)
    ensure_no_modal(hwnd, read_state)
    print('before', brief(read_state()))
    # The wolf stands at the left edge of the screen.
    for point in ((100, 420), (120, 430), (150, 400)):
        d.click_si(*point, hold=0.2)
        time.sleep(0.8)
        print('click', point, brief(read_state()))
    grab_desktop().save(OUT / 'click-diag.png')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
