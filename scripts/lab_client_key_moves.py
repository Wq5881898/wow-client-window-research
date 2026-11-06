"""Try every key of the movement and report which one moves the character.

The bindings of this machine are not the usual ones: the A key was seen to
strafing instead of going left. The character did not move at all, so
every key of the keyboard is tried and the distance is measured after
each of them.

The result says whether the key of the movement is bound at all, or
whether the character is held in place by the world.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
from client_evidence import Evidence
from client_parent_run import stamp
from client_walk import hold

ROOT = Path(__file__).resolve().parents[1]

# The keys that move a character: W A S D and the arrow keys.
KEYS = [('W', 0x57), ('A', 0x41), ('S', 0x53), ('D', 0x44),
        ('up', 0x26), ('down', 0x28), ('left', 0x25), ('right', 0x27),
        ('W again', 0x57), ('S again', 0x53)]
SECONDS = 1.5


def reader():
    return decode(assert_real_frame(grab_desktop()))


def main():
    run = 'client_key_moves_' + str(time.time_ns())
    result = stamp(dict(run=run, status='FAILED', keys=[]), sys.argv)
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
        state = reader()
        result['start'] = {'position': [state['pos_x'], state['pos_y']],
                           'facing': state['facing'],
                           'dead': state['dead']}
        evidence.capture('01-start', state)
        for name, key in KEYS:
            before = reader()
            hold(key, SECONDS, hwnd)
            time.sleep(0.4)
            after = reader()
            moved = ((after['pos_x'] - before['pos_x']) ** 2
                     + (after['pos_y'] - before['pos_y']) ** 2) ** 0.5
            result['keys'].append({
                'key': name,
                'moved': round(moved, 6),
                'facing_before': round(before['facing'], 3),
                'facing_after': round(after['facing'], 3),
                'position': [after['pos_x'], after['pos_y']]})
            evidence.capture('02-key-%s' % name.replace(' ', '-'))
        best = max(result['keys'], key=lambda item: item['moved'])
        result['best_key'] = best['key']
        result['best_moved'] = best['moved']
        result['status'] = 'MEASURED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('key moves', str(path), result['status'])
    return 0 if result['status'] == 'MEASURED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
