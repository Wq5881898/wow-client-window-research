"""Measure how far the character can walk in every direction.

The character stood still in a corner of the map, and it was not clear
whether the input reaches the client at all or whether the ground is in
the way. The probe turns the character to eight directions, walks a short
way in each of them and writes down how far it came.

The result tells the two cases apart: no direction moves the character at
all means that the input does not reach the client, while one direction
that moves means that the ground is in the way and the way out is a
question of direction.
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
from client_walk import hold, VK_FORWARD

ROOT = Path(__file__).resolve().parents[1]

# The eight directions of the compass. The movement at the heading h moves
# the position by (-sin h, -cos h), so a heading of zero is to the north.
DIRECTIONS = [('north', 0.0), ('north east', math.pi / 4),
              ('east', math.pi / 2), ('south east', 3 * math.pi / 4),
              ('south', math.pi), ('south west', 5 * math.pi / 4),
              ('west', 3 * math.pi / 2), ('north west', 7 * math.pi / 4)]

# How long the character walks in one direction.
STEP_SECONDS = 1.2
# A movement below this does not count.
MOVED = 0.0004


def reader():
    return decode(assert_real_frame(grab_desktop()))


def turn_to(hwnd, reader, heading):
    """Turn the character to the heading, and report the error that is left."""
    for _ in range(8):
        state = reader()
        error = (heading - state['facing'] + math.pi) % (2 * math.pi) - math.pi
        if abs(error) <= 0.12:
            return 0.0
        d.post_key(hwnd, 0x25 if error > 0 else 0x27)
        time.sleep(min(0.8, max(0.08, abs(error) / math.pi)))
    return error


def main():
    run = 'client_move_probe_' + str(time.time_ns())
    result = stamp(dict(run=run, status='FAILED', directions=[]), sys.argv)
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
        state = reader()
        result['start'] = {'position': [state['pos_x'], state['pos_y']],
                           'facing': state['facing'],
                           'dead': state['dead'],
                           'health': state['health'],
                           'zone': state.get('zone_hash'),
                           'subzone': state.get('subzone_hash')}
        evidence.capture('01-start', state)
        for name, heading in DIRECTIONS:
            error = turn_to(hwnd, reader, heading)
            before = reader()
            hold(VK_FORWARD, STEP_SECONDS, hwnd)
            after = reader()
            moved = math.hypot(after['pos_x'] - before['pos_x'],
                               after['pos_y'] - before['pos_y'])
            entry = {'direction': name, 'heading': round(heading, 3),
                     'turn_error': round(error, 3),
                     'moved': round(moved, 5),
                     'from': [before['pos_x'], before['pos_y']],
                     'to': [after['pos_x'], after['pos_y']]}
            result['directions'].append(entry)
            evidence.capture('02-%s' % name.replace(' ', '-'), after)
        state = reader()
        result['end'] = {'position': [state['pos_x'], state['pos_y']],
                         'dead': state['dead'], 'health': state['health']}
        best = max(result['directions'], key=lambda item: item['moved'])
        result['best_direction'] = best['direction']
        result['best_moved'] = best['moved']
        result['status'] = 'MEASURED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('move probe', str(path), result['status'])
    return 0 if result['status'] == 'MEASURED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
