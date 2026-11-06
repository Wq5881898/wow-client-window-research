"""Walk the character to the mark of the quest on the minimap.

The place of the birth of the character lies in the valley of Northshire,
and the character is somewhere else in the forest of Elwynn. The
coordinates of the probe belong to the area the character is in, so they
may not be used to walk there. The mark of the quest on the minimap is a
direction of the world, and it stays right across the border.

The script walks towards the mark until it is close or the budget is
spent, and writes down how the distance to the mark changes.
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
from client_minimap_mark import quest_marker, heading_to, distance_to
from client_walk import walk_to

ROOT = Path(__file__).resolve().parents[1]

# The budget of the whole walk.
BUDGET = 300.0
# How far the aim of the walk reaches in the map coordinates.
REACH = 0.05
# The mark is close enough at this distance in the picture.
CLOSE = 18.0


def reader():
    return decode(assert_real_frame(grab_desktop()))


def aim(state, heading):
    """The point the character walks to, in the direction of the mark."""
    # The movement at the heading h moves the position by (-sin h, -cos h).
    return (state['pos_x'] - math.sin(heading) * REACH,
            state['pos_y'] - math.cos(heading) * REACH)


def main():
    run = 'client_walk_to_marker_' + str(time.time_ns())
    result = stamp(dict(run=run, status='FAILED', steps=[]), sys.argv)
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
        state = reader()
        result['start'] = {'position': [state['pos_x'], state['pos_y']],
                           'zone': state.get('zone_hash'),
                           'subzone': state.get('subzone_hash'),
                           'dead': state['dead'],
                           'health': state['health']}
        evidence.capture('01-start', state)
        # The point the character walks to. By default it is the direction
        # of the mark; a point may be given instead, so that a known place
        # can be tried and the distance to the mark tells whether it was
        # the right one.
        target = None
        for argument in sys.argv[1:]:
            if argument.startswith('--target='):
                x, y = argument.split('=', 1)[1].split(',')
                target = (float(x), float(y))
        result['walk_target'] = list(target) if target else None
        deadline = time.monotonic() + BUDGET
        arrived = False
        best = None
        while time.monotonic() < deadline:
            picture = grab_desktop()
            state = reader()
            mark = quest_marker(picture)
            entry = {'position': [state['pos_x'], state['pos_y']],
                     'zone': state.get('zone_hash'),
                     'subzone': state.get('subzone_hash')}
            if mark is None:
                entry['marker'] = None
                entry['note'] = 'the mark is not to be seen'
                result['steps'].append(entry)
                break
            entry['marker_distance'] = round(distance_to(mark), 1)
            entry['marker_heading'] = round(heading_to(mark), 3)
            result['steps'].append(entry)
            if best is None or entry['marker_distance'] < best:
                best = entry['marker_distance']
            if entry['marker_distance'] <= CLOSE:
                arrived = True
                result['status'] = 'AT_THE_MARK'
                break
            goal = target if target is not None else aim(state, heading_to(mark))
            walk = walk_to(hwnd, reader, goal, timeout=25.0)
            entry['blocked'] = walk.blocked
            entry['walk_reason'] = walk.reason
        result['best_marker_distance'] = best
        state = reader()
        result['end'] = {'position': [state['pos_x'], state['pos_y']],
                         'zone': state.get('zone_hash'),
                         'subzone': state.get('subzone_hash'),
                         'dead': state['dead'],
                         'health': state['health']}
        evidence.capture('02-end', state)
        if not arrived and result['status'] != 'AT_THE_MARK':
            result['status'] = 'FAILED'
            result['reason'] = 'the mark was not reached'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('walk to marker', str(path), result['status'])
    return 0 if result['status'] == 'AT_THE_MARK' else 1


if __name__ == '__main__':
    raise SystemExit(main())
