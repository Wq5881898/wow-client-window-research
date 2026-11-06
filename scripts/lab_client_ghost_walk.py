"""Bring the ghost of the character to its corpse.

The character is a ghost and it stands in a place where the ground blocks
it: every direction of the walk changes the position by a few hundredths
of a thousandth. The corpse is a known distance away, and the ghost has to
stand on it to be revived.

The script walks towards the corpse with the walking primitive that slides
along an obstacle and steps backwards when nothing moves. Every attempt is
measured, so the report shows whether the distance shrinks or the place
is simply too narrow for the ghost.
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
from client_walk import walk_to

ROOT = Path(__file__).resolve().parents[1]

# The ghost has to stand this close to the corpse for the dialog.
CORPSE_RANGE = 0.004
# How long one attempt to come closer may take.
ATTEMPT_SECONDS = 45.0
# How many attempts there are at most.
ATTEMPTS = 6


def reader():
    return decode(assert_real_frame(grab_desktop()))


def main():
    run = 'client_ghost_walk_' + str(time.time_ns())
    result = stamp(dict(run=run, status='FAILED', attempts=[]), sys.argv)
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
        state = reader()
        if not state.get('corpse_exists'):
            raise ValueError('the client does not know a corpse')
        corpse = (state['corpse_x'], state['corpse_y'])
        result['corpse'] = list(corpse)
        result['start'] = {'position': [state['pos_x'], state['pos_y']],
                           'dead': state['dead'],
                           'distance': round(math.hypot(
                               corpse[0] - state['pos_x'],
                               corpse[1] - state['pos_y']), 5)}
        evidence.capture('01-start', state)

        for attempt in range(ATTEMPTS):
            state = reader()
            distance = math.hypot(corpse[0] - state['pos_x'],
                                  corpse[1] - state['pos_y'])
            if distance <= CORPSE_RANGE:
                result['status'] = 'AT_THE_CORPSE'
                break
            before = (state['pos_x'], state['pos_y'])
            walk = walk_to(hwnd, reader, corpse, tolerance=CORPSE_RANGE,
                           timeout=ATTEMPT_SECONDS)
            state = reader()
            after = (state['pos_x'], state['pos_y'])
            distance = math.hypot(corpse[0] - after[0], corpse[1] - after[1])
            entry = {'attempt': attempt,
                     'distance_before': round(math.hypot(
                         corpse[0] - before[0], corpse[1] - before[1]), 5),
                     'distance_after': round(distance, 5),
                     'arrived': walk.arrived,
                     'blocked': walk.blocked,
                     'steps': walk.steps,
                     'reason': walk.reason,
                     'position': [after[0], after[1]]}
            result['attempts'].append(entry)
            evidence.capture('02-attempt-%d' % attempt, state)
            if distance <= CORPSE_RANGE:
                result['status'] = 'AT_THE_CORPSE'
                break
        state = reader()
        result['end'] = {'position': [state['pos_x'], state['pos_y']],
                         'dead': state['dead'], 'health': state['health'],
                         'distance': round(math.hypot(
                             corpse[0] - state['pos_x'],
                             corpse[1] - state['pos_y']), 5)}
        if result['status'] != 'AT_THE_CORPSE':
            result['status'] = 'FAILED'
            result['reason'] = 'the corpse was not reached'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('ghost walk', str(path), result['status'])
    return 0 if result['status'] == 'AT_THE_CORPSE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
