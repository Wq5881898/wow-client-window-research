"""Walk out of the map area until the coordinates jump.

The coordinates of the probe are the ones of the current map area, and the
areas are not comparable with each other. When the character crosses the
border of the area, the numbers jump, and the jump is the proof that the
area changed. The direction is given as a compass point, because a place in
another area cannot be used as the target of the walk.

The conventions of the heading were measured on the client: the map x grows
to the east, the map y to the south, the heading grows counter clockwise
from the north, and walking at the heading h moves the position by
(-sin h, -cos h). So the heading for east is -pi/2.
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
from client_walk import walk_heading, walk_to

ROOT = Path(__file__).resolve().parents[1]

# The heading of every compass point, in the convention of the client.
DIRECTIONS = {
    'north': 0.0,
    'north-east': -math.pi / 4,
    'east': -math.pi / 2,
    'south-east': -3 * math.pi / 4,
    'south': math.pi,
    'south-west': 3 * math.pi / 4,
    'west': math.pi / 2,
    'north-west': math.pi / 4,
}

# A jump of the coordinates that large means that another map area started.
AREA_JUMP = 0.05

# The character has to move this much, otherwise the way is blocked.
MIN_PROGRESS = 0.0008


def main():
    run = 'client_walk_out_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', trace=[])
    evidence = Evidence(run)
    try:
        direction = 'east'
        if '--direction' in sys.argv:
            direction = sys.argv[sys.argv.index('--direction') + 1]
        seconds = 120.0
        if '--seconds' in sys.argv:
            seconds = float(sys.argv[sys.argv.index('--seconds') + 1])
        wanted = [word.strip() for word in direction.split(',') if word.strip()]
        for word in wanted:
            if word not in DIRECTIONS:
                raise ValueError('unknown direction ' + word)
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        start = reader()
        result['start'] = {'position': [start['pos_x'], start['pos_y']],
                           'facing': start['facing'],
                           'health': start['health']}
        evidence.capture('01-start', start)
        if start['dead']:
            raise ValueError('the character is dead')

        # The walk starts at a known place, so the distance from the
        # graveyard is the same in every run.
        if '--from' in sys.argv:
            index = sys.argv.index('--from')
            home = (float(sys.argv[index + 1]), float(sys.argv[index + 2]))
            result['home'] = list(home)
            walk_to(hwnd, reader, home, timeout=120.0)
            start = reader()
            result['at_home'] = {'position': [start['pos_x'], start['pos_y']],
                                 'distance': math.hypot(
                                     start['pos_x'] - home[0],
                                     start['pos_y'] - home[1])}

        reached = False
        blocked_ok = '--stop-when-blocked' in sys.argv
        state = start
        for word in wanted:
            last = (state['pos_x'], state['pos_y'])
            stuck = 0
            trace = []
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                done, state = walk_heading(hwnd, reader, DIRECTIONS[word],
                                           seconds=12.0, trace=trace)
                step = math.hypot(state['pos_x'] - last[0],
                                  state['pos_y'] - last[1])
                result['trace'].append({'direction': word,
                                        'position': [state['pos_x'],
                                                     state['pos_y']],
                                        'step': step})
                if step >= AREA_JUMP:
                    reached = True
                    result['area_changed'] = True
                    result['direction_used'] = word
                    break
                if step < MIN_PROGRESS:
                    stuck += 1
                    if stuck >= 2:
                        result['blocked'] = word
                        break
                else:
                    stuck = 0
                last = (state['pos_x'], state['pos_y'])
            if reached:
                break
        result['end'] = {'position': [state['pos_x'], state['pos_y']],
                         'health': state['health']}
        result['distance'] = math.hypot(state['pos_x'] - start['pos_x'],
                                        state['pos_y'] - start['pos_y'])
        evidence.capture('02-end', state)
        if not reached:
            if not blocked_ok:
                raise ValueError('the character did not reach another map area')
            result['status'] = 'WALKED'
        else:
            result['status'] = 'OUT'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('09-end')
        path = evidence.write(result)
        d.log('walk out', str(path), result['status'])
    return 0 if result['status'] in ('OUT', 'WALKED') else 1


if __name__ == '__main__':
    raise SystemExit(main())
