"""Walk the character back to the valley with the quest marker as the guide.

The character went out of the valley on a walk to the east, and the standard
creature of the experiments is not there. The birth place is documented:
Elwynn Forest / Northshire Valley, near Deputy Willem outside the Northshire
Abbey, at the normalised position (0.48055, 0.43652).

Two things tell the driver the way back:

* the minimap shows the mark of the quest of the valley, and the mark is
  drawn in the north, so the direction to it is the direction to the abbey;
* the probe reports the zone of the character as a hash, so the crossing of
  the border is recognised by the name of the area and not by a jump of the
  coordinates, which depend on the area.

The walk towards the mark uses the walk that slides along an obstacle, so a
rock between the character and the mark does not stop the run.
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

ROOT = Path(__file__).resolve().parents[1]

# The place of the birth of the character (docs/20).
SPAWN = (0.4805501997, 0.4365223348)
# The areas of this client.
NORTHSHIRE = name_hash('Northshire Valley')
# How close the mark has to come to the middle of the minimap.
ARRIVED = 14.0
# The budget of the whole walk.
BUDGET = 420.0
# How far the aim of the walk reaches in the map coordinates.
REACH = 0.05


def reader():
    return decode(assert_real_frame(grab_desktop()))


def aim(state, heading):
    """The point the character walks to, in the direction of the mark."""
    # The movement at the heading h is (-sin h, -cos h).
    return (state['pos_x'] - math.sin(heading) * REACH,
            state['pos_y'] - math.cos(heading) * REACH)


def main():
    run = 'client_return_spawn_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', steps=[])
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
        state = reader()
        result['start'] = {'position': [state['pos_x'], state['pos_y']],
                           'zone': state.get('zone_hash')}
        evidence.capture('01-start', state)

        deadline = time.monotonic() + BUDGET
        arrived = False
        while time.monotonic() < deadline:
            picture = grab_desktop()
            state = reader()
            mark = quest_marker(picture)
            entry = {'position': [state['pos_x'], state['pos_y']],
                     'zone': state.get('zone_hash')}
            if mark is None:
                entry['marker'] = None
                result['steps'].append(entry)
                # Without the mark the direction is unknown, so the character
                # walks on and the mark is looked for again.
                walk_to(hwnd, reader, aim(state, math.pi / 4), timeout=20.0)
                continue
            heading = heading_to(mark)
            distance = distance_to(mark)
            entry.update({'marker': mark, 'heading': round(heading, 3),
                          'distance': round(distance, 1)})
            result['steps'].append(entry)
            if distance <= ARRIVED:
                entry['action'] = 'at_the_mark'
                arrived = True
                break
            walk_to(hwnd, reader, aim(state, heading), timeout=25.0)
        if not arrived:
            result['reason'] = 'the mark of the quest was not reached'
        else:
            distance = walk_to(hwnd, reader, SPAWN, timeout=240.0)
            state = reader()
            result['at_spawn'] = {'position': [state['pos_x'], state['pos_y']],
                                  'distance': distance,
                                  'zone': state.get('zone_hash')}
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
