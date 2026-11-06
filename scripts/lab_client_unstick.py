"""Try the ways out of a place where the character does not move.

The ghost of the character stands where the ground blocks it: every
direction changes the position by a few hundredths of a thousandth, and
the distance to the corpse does not shrink. The walking primitive slides
along the obstacle and steps backwards, and that was not enough.

This script tries the other ways out and measures each of them: walking
backwards, jumping, walking away from the target to leave the pocket, and
the combination of jumping and walking backwards. Every attempt is
measured, so the report shows which one moved the character and which one
did not.
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
from client_walk import hold, VK_FORWARD, VK_BACKWARD, VK_LEFT, VK_RIGHT
from client_motion import TURN_RATE

ROOT = Path(__file__).resolve().parents[1]

VK_SPACE = 0x20


def reader():
    return decode(assert_real_frame(grab_desktop()))


def turn_to(hwnd, reader, heading):
    """Turn to the heading, and report the error that is left."""
    error = 0.0
    for _ in range(10):
        state = reader()
        error = (heading - state['facing'] + math.pi) % (2 * math.pi) - math.pi
        if abs(error) <= 0.12:
            return 0.0
        d.post_key(hwnd, VK_LEFT if error > 0 else VK_RIGHT)
        time.sleep(min(0.9, max(0.08, abs(error) / TURN_RATE)))
    return error


def jump(hwnd):
    d.post_key(hwnd, VK_SPACE)
    time.sleep(0.4)


def measure(reader, corpse):
    state = reader()
    return (state['pos_x'], state['pos_y'],
            math.hypot(corpse[0] - state['pos_x'],
                       corpse[1] - state['pos_y']))


def main():
    run = 'client_unstick_' + str(time.time_ns())
    result = stamp(dict(run=run, status='FAILED', attempts=[]), sys.argv)
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
        state = reader()
        corpse = (state['corpse_x'], state['corpse_y'])
        result['corpse'] = list(corpse)
        x, y, distance = measure(reader, corpse)
        result['start'] = {'position': [x, y], 'distance': round(distance, 5)}
        evidence.capture('01-start', state)

        # The heading of the corpse and the heading away from it.
        to_corpse = math.atan2(-(corpse[0] - x), -(corpse[1] - y))
        away = to_corpse + math.pi
        moves = [
            ('backwards', lambda: hold(VK_BACKWARD, 2.0, hwnd)),
            ('jump', lambda: jump(hwnd)),
            ('jump and backwards',
             lambda: (jump(hwnd), hold(VK_BACKWARD, 2.0, hwnd))),
            ('away from the corpse',
             lambda: (turn_to(hwnd, reader, away),
                      hold(VK_FORWARD, 3.0, hwnd))),
            ('away and jump',
             lambda: (turn_to(hwnd, reader, away), jump(hwnd),
                      hold(VK_FORWARD, 3.0, hwnd))),
            ('towards the corpse',
             lambda: (turn_to(hwnd, reader, to_corpse),
                      hold(VK_FORWARD, 3.0, hwnd))),
        ]
        for name, move in moves:
            before = measure(reader, corpse)
            move()
            time.sleep(0.8)
            after = measure(reader, corpse)
            entry = {'move': name,
                     'position_before': [before[0], before[1]],
                     'position_after': [after[0], after[1]],
                     'distance_before': round(before[2], 5),
                     'distance_after': round(after[2], 5),
                     'moved': round(math.hypot(after[0] - before[0],
                                               after[1] - before[1]), 5)}
            result['attempts'].append(entry)
            evidence.capture('02-%s' % name.replace(' ', '-'))
        x, y, distance = measure(reader, corpse)
        result['end'] = {'position': [x, y], 'distance': round(distance, 5)}
        best = min(result['attempts'], key=lambda item: item['distance_after'])
        result['best_move'] = best['move']
        result['best_distance'] = best['distance_after']
        result['status'] = 'MEASURED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('unstick', str(path), result['status'])
    return 0 if result['status'] == 'MEASURED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
