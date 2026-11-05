"""Walk to a marker of the minimap.

The minimap is centred on the character and has north at the top, so the
position of a marker on it gives the direction to that marker. The script
walks in that direction until the marker is close to the middle of the map,
which means that the character stands at the place of the marker.

The quest marker is used by default; the dots of the creatures are the
fallback.
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
from client_minimap import find_markers, heading, nearest, CENTRE
from client_walk import walk_heading

ROOT = Path(__file__).resolve().parents[1]

# How close the marker has to come to the middle of the map.
ARRIVED = 14.0

# How long the walk may take.
BUDGET = 180.0


def main():
    run = 'client_minimap_walk_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', steps=[])
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
        deadline = time.monotonic() + BUDGET
        last_heading = None
        while time.monotonic() < deadline:
            picture = grab_desktop()
            markers = find_markers(picture)
            marker = nearest(markers)
            if marker is None:
                result['steps'].append({'action': 'no_marker'})
                time.sleep(2.0)
                continue
            east = marker['x'] - CENTRE[0]
            south = marker['y'] - CENTRE[1]
            distance = math.hypot(east, south)
            result['steps'].append({'action': 'marker', 'marker': marker,
                                    'distance': round(distance, 1),
                                    'heading': round(heading(CENTRE, marker), 3)})
            if distance <= ARRIVED:
                result['status'] = 'ARRIVED'
                break
            wanted = heading(CENTRE, marker)
            if last_heading is not None:
                # The marker moves with the character, so a change of the
                # direction means that the way is not free.
                turn = abs((wanted - last_heading + math.pi) % (2 * math.pi)
                           - math.pi)
                if turn > 1.2:
                    result['steps'].append({'action': 'turned',
                                            'turn': round(turn, 3)})
            last_heading = wanted
            walk_heading(hwnd, lambda: decode(assert_real_frame(grab_desktop())),
                         wanted, seconds=6.0)
        evidence.capture('01-end')
        if result['status'] != 'ARRIVED':
            result['status'] = 'NOT_REACHED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('09-end')
        path = evidence.write(result)
        d.log('minimap walk', str(path), result['status'])
    return 0 if result['status'] == 'ARRIVED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
