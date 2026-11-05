"""Walk the character back to the place where it was born.

The character went out of the valley on a walk to the east, and the standard
creature of the experiments is not there. The birth place is documented:
Elwynn Forest / Northshire Valley, near Deputy Willem outside the Northshire
Abbey, at the normalised position (0.48055, 0.43652).

The way back crosses a border and the coordinates jump. The walk therefore
goes by compass point until the area changes, and only then the position of
the birth can be addressed.

The character can be stuck against a rock or a wall, in which case walking
towards the mark does not move it at all. The walk then turns away and tries
the next direction, the same way the search for a merchant does.
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
from client_minimap import find_markers, heading, CENTRE
from client_walk import walk_heading, walk_to

ROOT = Path(__file__).resolve().parents[1]

# The place of the birth of the character (docs/20).
SPAWN = (0.4805501997, 0.4365223348)
# A jump of the coordinates means that another map area began.
AREA_JUMP = 0.05
# The walk towards the mark is given this long before it counts as blocked.
STEP_LIMIT = 0.001


def main():
    run = 'client_return_spawn_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', steps=[])
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
        state = decode(assert_real_frame(grab_desktop()))
        result['start'] = {'position': [state['pos_x'], state['pos_y']]}
        evidence.capture('01-start', state)

        deadline = time.monotonic() + 300.0
        crossed = False
        detour = 0.0
        last = (state['pos_x'], state['pos_y'])
        while time.monotonic() < deadline:
            picture = grab_desktop()
            state = decode(assert_real_frame(picture))
            markers = [marker for marker in find_markers(picture)
                       if marker['pixels'] >= 5]
            if not markers:
                result['steps'].append({'action': 'no_marker'})
                time.sleep(2.0)
                continue
            blue = [marker for marker in markers if marker['kind'] == 'blue']
            pool = blue if blue else markers
            marker = min(pool,
                         key=lambda item: math.hypot(item['x'] - CENTRE[0],
                                                     item['y'] - CENTRE[1]))
            before = (state['pos_x'], state['pos_y'])
            wanted = heading(CENTRE, marker) + detour
            walk_heading(hwnd,
                         lambda: decode(assert_real_frame(grab_desktop())),
                         wanted, seconds=6.0)
            after = decode(assert_real_frame(grab_desktop()))
            step = math.hypot(after['pos_x'] - before[0],
                              after['pos_y'] - before[1])
            entry = {'action': 'walked', 'step': round(step, 5),
                     'position': [after['pos_x'], after['pos_y']]}
            if step < STEP_LIMIT:
                # The way is blocked, so the character turns away from the
                # mark and tries the next direction.
                detour = math.pi / 2 if detour == 0.0 else -detour
                entry['detour'] = detour
            result['steps'].append(entry)
            if step >= AREA_JUMP:
                crossed = True
                result['steps'].append({'action': 'area_changed',
                                        'position': [after['pos_x'],
                                                     after['pos_y']]})
                break
            last = (after['pos_x'], after['pos_y'])
        if not crossed:
            result['reason'] = 'the border of the area was not reached'
        else:
            # Now the coordinates belong to the area of the birth.
            distance = walk_to(hwnd, reader, SPAWN, timeout=180.0)
            state = decode(assert_real_frame(grab_desktop()))
            result['at_spawn'] = {'position': [state['pos_x'], state['pos_y']],
                                  'distance': distance}
            evidence.capture('02-spawn', state)
            result['status'] = 'AT_SPAWN'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('09-end')
        path = evidence.write(result)
        d.log('return to spawn', str(path), result['status'])
    return 0 if result['status'] == 'AT_SPAWN' else 1


def reader():
    return decode(assert_real_frame(grab_desktop()))


if __name__ == '__main__':
    raise SystemExit(main())
