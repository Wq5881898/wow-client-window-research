"""Find a merchant and name the people around.

The minimap shows the people around as dots, and it is centred on the
character, so the driver can walk to a dot. The name of the creature under
the cursor is reported by the probe, so the people at the place can be
named one by one after the character has arrived.

The script walks to the nearest mark of the minimap and then reads the
names of the units around the character, with a picture of the screen for
every name it found.
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
from client_minimap import find_markers, heading, CENTRE
from client_walk import walk_heading

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'

# A marker with fewer pixels is noise of the map.
MIN_PIXELS = 5
# How close the mark has to come to the middle of the map.
ARRIVED = 12.0
# How long the walk may take.
WALK_BUDGET = 420.0
# The grid the cursor is put on to name the people around.
PROBE_X = range(500, 1450, 40)
PROBE_Y = range(200, 750, 40)
# How many directions are looked at.
TURNS = 5


def turn_character(hwnd, seconds):
    """Turn the character so that the camera looks in another direction."""
    key = d.INPUT()
    key.type = 1
    key.union.ki = d.KEYBDINPUT(0x27, 0, 0, 0, None)
    d.SendInput(1, ctypes.byref(key), ctypes.sizeof(d.INPUT))
    time.sleep(seconds)
    key.union.ki.dwFlags = 2
    d.SendInput(1, ctypes.byref(key), ctypes.sizeof(d.INPUT))
    time.sleep(0.4)


def main():
    run = 'client_find_merchant_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', walk=[], names=[])
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)

        deadline = time.monotonic() + WALK_BUDGET
        last_position = None
        detour = 0.0
        while time.monotonic() < deadline:
            picture = grab_desktop()
            markers = [marker for marker in find_markers(picture)
                       if marker['pixels'] >= MIN_PIXELS]
            state = decode(assert_real_frame(picture))
            position = (state['pos_x'], state['pos_y'])
            stuck = False
            if last_position is not None:
                moved = math.hypot(position[0] - last_position[0],
                                   position[1] - last_position[1])
                stuck = moved < 0.001
            if stuck:
                # The way is blocked, most likely by the wall of the
                # graveyard. The character turns away from the mark and
                # walks around the obstacle.
                detour = math.pi / 2 if detour == 0.0 else -detour
                result['walk'].append({'action': 'stuck', 'detour': detour})
            last_position = position
            if not markers:
                result['walk'].append({'action': 'no_marker'})
                time.sleep(2.0)
                continue
            marker = min(markers,
                         key=lambda item: math.hypot(item['x'] - CENTRE[0],
                                                     item['y'] - CENTRE[1]))
            east = marker['x'] - CENTRE[0]
            south = marker['y'] - CENTRE[1]
            distance = math.hypot(east, south)
            result['walk'].append({'action': 'marker', 'marker': marker,
                                   'distance': round(distance, 1)})
            if distance <= ARRIVED:
                result['walk'].append({'action': 'arrived'})
                break
            wanted = heading(CENTRE, marker) + detour
            walk_heading(hwnd,
                         lambda: decode(assert_real_frame(grab_desktop())),
                         wanted, seconds=6.0)

        # Name the people around the character. The camera can be inside a
        # rock, so the character is turned and every direction is looked at.
        seen = {}
        for turn in range(TURNS):
            for y in PROBE_Y:
                for x in PROBE_X:
                    d.u.SetCursorPos(int(x), int(y))
                    time.sleep(0.12)
                    try:
                        reading = decode(assert_real_frame(grab_desktop()))
                    except Exception:
                        continue
                    digest = reading.get('cursor_name_hash')
                    if not digest or digest in seen:
                        continue
                    seen[digest] = True
                    shot = OUT / ('merchant-%s.png' % digest)
                    grab_desktop().save(shot)
                    result['names'].append({'hash': digest, 'x': x, 'y': y,
                                            'turn': turn,
                                            'picture': str(shot)})
            turn_character(hwnd, 1.1)
        evidence.capture('01-end', None)
        result['status'] = 'SCANNED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('09-end')
        path = evidence.write(result)
        d.log('find merchant', str(path), result['status'])
    return 0 if result['status'] == 'SCANNED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
