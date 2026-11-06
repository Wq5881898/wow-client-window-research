"""Let the client walk by itself: a click on the ground is a move request.

The driver sends keys, and the client answers with the position. When the
character does not move at all, the request itself may be the problem: the
client is told where to go by the server, and the server knows a path.

This script clicks on several places of the picture and writes down how
the position changes after every click. A click that moves the character
proves that the way out is a walk and not a key.
"""
import ctypes
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
from client_evidence import Evidence
from client_parent_run import stamp

ROOT = Path(__file__).resolve().parents[1]

# The places of the picture that are clicked. The character stands in the
# middle of the picture, so a place below it is in front of the character
# and a place above it is behind.
PLACES = [('middle', 960, 540), ('below', 960, 760), ('above', 960, 320),
          ('left', 520, 540), ('right', 1400, 540),
          ('below left', 620, 760), ('below right', 1300, 760)]


def reader():
    return decode(assert_real_frame(grab_desktop()))


def right_click(x, y):
    """A right click with the mouse of the system."""
    d.u.SetCursorPos(int(x), int(y))
    time.sleep(0.2)
    d.u.mouse_event(0x0008, 0, 0, 0, 0)
    time.sleep(0.1)
    d.u.mouse_event(0x0010, 0, 0, 0, 0)


def main():
    run = 'client_click_walk_' + str(time.time_ns())
    result = stamp(dict(run=run, status='FAILED', clicks=[]), sys.argv)
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
        state = reader()
        corpse = (state.get('corpse_x'), state.get('corpse_y'))
        result['corpse'] = list(corpse)
        result['start'] = {'position': [state['pos_x'], state['pos_y']],
                           'facing': state['facing'],
                           'dead': state['dead']}
        evidence.capture('01-start', state)
        for name, x, y in PLACES:
            before = reader()
            right_click(x, y)
            time.sleep(2.5)
            after = reader()
            moved = math.hypot(after['pos_x'] - before['pos_x'],
                               after['pos_y'] - before['pos_y'])
            entry = {'place': name, 'at': [x, y],
                     'moved': round(moved, 5),
                     'position_before': [before['pos_x'], before['pos_y']],
                     'position_after': [after['pos_x'], after['pos_y']],
                     'facing_after': round(after['facing'], 3)}
            if corpse[0] and corpse[1]:
                entry['distance_to_corpse'] = round(math.hypot(
                    corpse[0] - after['pos_x'], corpse[1] - after['pos_y']), 5)
            result['clicks'].append(entry)
            evidence.capture('02-%s' % name.replace(' ', '-'))
        state = reader()
        result['end'] = {'position': [state['pos_x'], state['pos_y']],
                         'dead': state['dead']}
        best = max(result['clicks'], key=lambda item: item['moved'])
        result['best_click'] = best['place']
        result['best_moved'] = best['moved']
        result['status'] = 'MEASURED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('click walk', str(path), result['status'])
    return 0 if result['status'] == 'MEASURED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
