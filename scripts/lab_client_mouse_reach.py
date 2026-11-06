"""Check whether the mouse reaches the client while it is in the world.

The clicks on the buttons of the client do nothing in the world, while a
click on the list of the characters works. The probe reports the name of
the unit under the cursor as a hash, so the mouse can be checked without
reading any text: the name of the character itself is known.

The script moves the mouse over several places of the picture and writes
down the name under the cursor after every move.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame, name_hash
from client_evidence import Evidence
from client_parent_run import stamp

ROOT = Path(__file__).resolve().parents[1]

# The places of the picture that are tried.
PLACES = [('the character', 960, 620), ('the minimap', 1780, 115),
          ('the empty ground', 300, 400), ('the chat frame', 300, 940),
          ('the action bar', 960, 1040), ('the panel', 300, 700)]


def reader():
    return decode(assert_real_frame(grab_desktop()))


def main():
    run = 'client_mouse_reach_' + str(time.time_ns())
    result = stamp(dict(run=run, status='FAILED', places=[]), sys.argv)
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
        result['probehuman_hash'] = name_hash('Probehuman')
        for name, x, y in PLACES:
            d.u.SetCursorPos(x, y)
            time.sleep(1.2)
            state = reader()
            cursor = state.get('cursor_name_hash')
            entry = {'place': name, 'at': [x, y],
                     'cursor_name_hash': cursor,
                     'cursor_is_probehuman': cursor == name_hash('Probehuman')}
            result['places'].append(entry)
            evidence.capture('02-%s' % name.replace(' ', '-'))
        result['status'] = 'MEASURED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('mouse reach', str(path), result['status'])
    return 0 if result['status'] == 'MEASURED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
