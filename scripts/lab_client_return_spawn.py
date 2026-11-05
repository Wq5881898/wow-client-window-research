"""Walk the character back to the place of the birth.

The character went out of the valley on a walk to the east, and the standard
creature of the experiments is not there. The birth place is documented:
Elwynn Forest / Northshire Valley, near Deputy Willem outside the Northshire
Abbey, at the normalised position (0.48055, 0.43652).

The zone and the subzone of the character are reported by the probe as
hashes, so the crossing of the border is recognised by the name of the area
and not by a jump of the coordinates, which depend on the area.

The coordinates of the place of the birth belong to the valley. They may
therefore only be used while the character is in the valley: in another
area the same numbers point at another place. Outside the valley the walk
follows the mark of the quest on the minimap, which is a direction of the
world and stays valid across the border.
"""
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame, name_hash
from client_evidence import Evidence
from client_minimap_mark import quest_marker, heading_to, distance_to
from client_walk import walk_to
from client_parent_run import stamp

ROOT = Path(__file__).resolve().parents[1]

# The place of the birth of the character (docs/20).
SPAWN = (0.4805501997, 0.4365223348)
# The areas of this client. Northshire Valley is the subzone of the valley
# and Elwynn Forest is the zone around it, so both names are checked.
NORTHSHIRE = name_hash('Northshire Valley')
ELWYNN = name_hash('Elwynn Forest')
# The budget of the whole walk.
BUDGET = 420.0


def reader():
    return decode(assert_real_frame(grab_desktop()))


def in_valley(state):
    """True when the character is in the valley of the birth.

    The probe reports the zone and the subzone of the character. In this
    client the valley is the subzone and the forest around it is the zone,
    so both names are checked.
    """
    return (state.get('zone_hash') == NORTHSHIRE
            or state.get('subzone_hash') == NORTHSHIRE
            or state.get('zone_hash') == ELWYNN
            or state.get('subzone_hash') == ELWYNN)


def main():
    run = 'client_return_spawn_' + str(time.time_ns())
    result = stamp(dict(run=run, status='FAILED', steps=[]), sys.argv)
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
        state = reader()
        result['start'] = {'position': [state['pos_x'], state['pos_y']],
                           'zone': state.get('zone_hash'),
                           'subzone': state.get('subzone_hash')}
        evidence.capture('01-start', state)

        deadline = time.monotonic() + BUDGET
        reached = False
        while time.monotonic() < deadline:
            picture = grab_desktop()
            state = reader()
            zone = state.get('zone_hash')
            subzone = state.get('subzone_hash')
            entry = {'position': [state['pos_x'], state['pos_y']],
                     'zone': zone, 'subzone': subzone}
            if in_valley(state):
                entry['action'] = 'in_the_valley'
                result['steps'].append(entry)
                reached = True
                break
            mark = quest_marker(picture)
            if mark is not None:
                entry['marker'] = mark
                entry['heading'] = round(heading_to(mark), 3)
                entry['distance'] = round(distance_to(mark), 1)
            result['steps'].append(entry)
            # The character walks towards the mark of the quest, which is a
            # direction of the world. The coordinates of the place of the
            # birth belong to the valley and may only be used inside it.
            if mark is not None:
                target = aim(state, heading_to(mark))
            else:
                entry['reason'] = 'the mark of the quest is not to be seen'
                target = None
            if target is not None:
                walk = walk_to(hwnd, reader, target, timeout=20.0)
                entry['blocked'] = walk.blocked
                entry['walk_reason'] = walk.reason
        if not reached:
            result['reason'] = 'the valley was not reached'
        else:
            walk = walk_to(hwnd, reader, SPAWN, timeout=240.0)
            state = reader()
            result['at_spawn'] = {'position': [state['pos_x'], state['pos_y']],
                                  'distance': walk.distance,
                                  'arrived': walk.arrived,
                                  'blocked': walk.blocked,
                                  'reason': walk.reason,
                                  'zone': state.get('zone_hash'),
                                  'subzone': state.get('subzone_hash')}
            evidence.capture('02-spawn', state)
            result['status'] = 'AT_SPAWN'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('09-end')
        path = evidence.write(result)
        d.log('return to spawn', str(path), result['status'])
    return 0 if result['status'] == 'AT_SPAWN' else 1


def aim(state, heading):
    """The point the character walks to, in the direction of the mark."""
    # The movement at the heading h is (-sin h, -cos h).
    return (state['pos_x'] - math.sin(heading) * 0.05,
            state['pos_y'] - math.cos(heading) * 0.05)


if __name__ == '__main__':
    raise SystemExit(main())
