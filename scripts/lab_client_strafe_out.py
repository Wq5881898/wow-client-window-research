"""Try to leave the place by strafing.

The key of the forward movement does not move the character at all, but the
keys of the strafe do. The corpse lies in the south, and the strafe to the
left moves the character to the south. This script holds the strafe keys
one after the other and writes down how the distance to the corpse changes.

The result tells whether the ghost can leave the pocket by strafing, or
whether the place holds it in every direction.
"""
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
from client_walk import hold

ROOT = Path(__file__).resolve().parents[1]

# The strafe keys and the way back.
KEYS = [('A left', 0x41), ('D right', 0x44), ('A left', 0x41),
        ('D right', 0x44), ('A left', 0x41), ('D right', 0x44)]
SECONDS = 3.0


def reader():
    return decode(assert_real_frame(grab_desktop()))


def main():
    run = 'client_strafe_out_' + str(time.time_ns())
    result = stamp(dict(run=run, status='FAILED', steps=[]), sys.argv)
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
        state = reader()
        corpse = (state['corpse_x'], state['corpse_y'])
        result['corpse'] = list(corpse)
        result['start'] = {'position': [state['pos_x'], state['pos_y']],
                           'facing': state['facing'],
                           'distance': round(math.hypot(
                               corpse[0] - state['pos_x'],
                               corpse[1] - state['pos_y']), 5)}
        evidence.capture('01-start', state)
        best = None
        for index, (name, key) in enumerate(KEYS):
            before = reader()
            hold(key, SECONDS, hwnd)
            time.sleep(0.4)
            after = reader()
            distance = math.hypot(corpse[0] - after['pos_x'],
                                  corpse[1] - after['pos_y'])
            entry = {'key': name, 'seconds': SECONDS,
                     'moved': round(math.hypot(after['pos_x'] - before['pos_x'],
                                               after['pos_y'] - before['pos_y']), 6),
                     'distance': round(distance, 5),
                     'position': [after['pos_x'], after['pos_y']]}
            result['steps'].append(entry)
            evidence.capture('02-%d' % index)
            if best is None or distance < best:
                best = distance
        result['best_distance'] = round(best, 5)
        result['status'] = 'MEASURED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('strafe out', str(path), result['status'])
    return 0 if result['status'] == 'MEASURED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
