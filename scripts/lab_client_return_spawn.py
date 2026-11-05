"""Walk the character back to the place where it was born, around obstacles.

The character went out of the valley on a walk to the east, and the standard
creature of the experiments is not there. The birth place is documented:
Elwynn Forest / Northshire Valley, near Deputy Willem outside the Northshire
Abbey, at the normalised position (0.48055, 0.43652).

The way back crosses a border and the coordinates jump, so the walk goes by
compass point until the area changes and only then the position of the
birth can be addressed. The walk uses the obstacle aware walk, so a rock in
the way no longer eats the whole budget.
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
from client_walk import walk_to, walk_heading

ROOT = Path(__file__).resolve().parents[1]

# The place of the birth of the character (docs/20).
SPAWN = (0.4805501997, 0.4365223348)
# A jump of the coordinates means that another map area began.
AREA_JUMP = 0.05
# The compass points that lead out of the area, tried one after the other.
# The tunnel back into the valley was crossed to the north east, so that
# direction is tried first.
DIRECTIONS = [math.pi / 4, 0.0, -math.pi / 2, -3 * math.pi / 4, math.pi / 2,
              math.pi, 3 * math.pi / 4]


def reader():
    return decode(assert_real_frame(grab_desktop()))


def main():
    run = 'client_return_spawn_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', steps=[])
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
        state = reader()
        result['start'] = {'position': [state['pos_x'], state['pos_y']]}
        evidence.capture('01-start', state)

        # Walk to the border of the area by a compass point, until the
        # coordinates jump. Every direction is tried, so that a corner does
        # not stop the walk.
        deadline = time.monotonic() + 420.0
        crossed = False
        index = 0
        while time.monotonic() < deadline and index < len(DIRECTIONS):
            wanted = DIRECTIONS[index]
            before = (state['pos_x'], state['pos_y'])
            walk_heading(hwnd, reader, wanted, seconds=60.0)
            state = reader()
            step = math.hypot(state['pos_x'] - before[0],
                              state['pos_y'] - before[1])
            result['steps'].append({'direction': round(wanted, 3),
                                    'step': round(step, 5),
                                    'position': [state['pos_x'],
                                                 state['pos_y']]})
            if step >= AREA_JUMP:
                crossed = True
                result['steps'].append({'action': 'area_changed',
                                        'position': [state['pos_x'],
                                                     state['pos_y']]})
                break
            index += 1
        if not crossed:
            result['reason'] = 'the border of the area was not reached'
        else:
            # Now the coordinates belong to the area of the birth.
            distance = walk_to(hwnd, reader, SPAWN, timeout=240.0)
            state = reader()
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


if __name__ == '__main__':
    raise SystemExit(main())
