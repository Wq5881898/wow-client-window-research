"""Measure how fast the client turns, and how fast the character walks.

The rate of the turn decides how long a key has to be held to reach a
heading. It was assumed to be a half turn per second; the assumption is
measured here, because a wrong rate makes every turn overshoot and every
walk leaves the target.

The walk is measured as well: the character has to cover a known distance
in a known time, so that the size of the steps can be judged.
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
from client_walk import hold, VK_FORWARD, VK_LEFT, VK_RIGHT

ROOT = Path(__file__).resolve().parents[1]
HOLD = 0.6


def reader():
    return decode(assert_real_frame(grab_desktop()))


def turn_rate(hwnd, reader, key):
    """How many radians the heading changes in a second."""
    before = reader()['facing']
    hold(key, HOLD, hwnd)
    after = reader()['facing']
    change = (after - before + math.pi) % (2 * math.pi) - math.pi
    return change / HOLD


def main():
    run = 'client_turn_rate_' + str(time.time_ns())
    result = stamp(dict(run=run, status='FAILED', turns=[]), sys.argv)
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
        for name, key in (('left', VK_LEFT), ('right', VK_RIGHT),
                          ('left', VK_LEFT), ('right', VK_RIGHT)):
            rate = turn_rate(hwnd, reader, key)
            result['turns'].append({'key': name, 'rate': round(rate, 3),
                                    'hold': HOLD})
            evidence.capture('01-turn-%s-%d' % (name, len(result['turns'])))
        left = [item['rate'] for item in result['turns']
                if item['key'] == 'left']
        right = [item['rate'] for item in result['turns']
                 if item['key'] == 'right']
        result['rate_left'] = round(sum(left) / len(left), 3) if left else None
        result['rate_right'] = round(sum(right) / len(right), 3) if right else None
        result['rate_pi'] = round(math.pi, 3)

        # The walk: how far does the character come in a second?
        before = reader()
        hold(VK_FORWARD, 2.0, hwnd)
        after = reader()
        result['walk'] = {
            'seconds': 2.0,
            'distance': round(math.hypot(after['pos_x'] - before['pos_x'],
                                         after['pos_y'] - before['pos_y']), 5),
            'from': [before['pos_x'], before['pos_y']],
            'to': [after['pos_x'], after['pos_y']]}
        evidence.capture('02-walk', after)
        result['status'] = 'MEASURED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('turn rate', str(path), result['status'])
    return 0 if result['status'] == 'MEASURED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
