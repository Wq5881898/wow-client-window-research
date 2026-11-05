"""Look for a merchant in the neighbourhood.

A merchant is a creature with a name that ends in a trade, and the client
shows the name of the creature under the cursor. The script moves the cursor
over the screen in a grid, reads the name that the probe reports and writes
every name it saw, so the merchants of the zone can be found without
knowing where they stand.

The money and the number of items in the bags are reported as well: a trade
with a merchant has to change the money, and the bags are what is to be
sold.
"""
import ctypes
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame, name_hash
from client_evidence import Evidence

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'

# The points of the grid the cursor is put on. The world is drawn in the
# middle of the screen, so the grid stays inside it.
GRID_X = range(120, 1800, 110)
GRID_Y = range(150, 950, 100)

# How often the character is turned between the scans.
TURNS = 3

# The character is turned between the scans, because a creature that is
# beside the character is not in the picture when the camera looks away.
TURN_KEY = 0x27   # the right arrow turns the character
TURN_SECONDS = 0.6


def reader():
    return decode(assert_real_frame(grab_desktop()))


def main():
    run = 'client_vendor_scan_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', names=[], points=0)
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
        state = reader()
        result['start'] = {'level': state.get('level'),
                           'money': state.get('money'),
                           'bag_items': state.get('bag_items'),
                           'position': [state['pos_x'], state['pos_y']]}
        evidence.capture('01-start', state)
        seen = {}
        for turn in range(TURNS):
            for y in GRID_Y:
                for x in GRID_X:
                    d.u.SetCursorPos(int(x), int(y))
                    time.sleep(0.3)
                    try:
                        reading = reader()
                    except Exception:
                        continue
                    result['points'] += 1
                    digest = reading.get('cursor_name_hash')
                    if not digest or digest == name_hash(''):
                        continue
                    if digest in seen:
                        continue
                    seen[digest] = True
                    # The name of the creature is written in the text of the
                    # panel, so a picture of the screen shows which name the
                    # hash belongs to.
                    picture = grab_desktop()
                    shot = OUT / ('vendor-%s.png' % digest)
                    picture.save(shot)
                    result['names'].append({'hash': digest, 'x': x, 'y': y,
                                            'turn': turn,
                                            'picture': str(shot),
                                            'money': reading.get('money'),
                                            'bag_items': reading.get('bag_items')})
            # The camera looks somewhere else now.
            key = d.INPUT()
            key.type = 1
            key.union.ki = d.KEYBDINPUT(TURN_KEY, 0, 0, 0, None)
            d.SendInput(1, ctypes.byref(key), ctypes.sizeof(d.INPUT))
            time.sleep(TURN_SECONDS)
            key.union.ki.dwFlags = 2
            d.SendInput(1, ctypes.byref(key), ctypes.sizeof(d.INPUT))
            time.sleep(0.6)
        evidence.capture('02-scan', None)
        result['status'] = 'SCANNED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('09-end')
        path = evidence.write(result)
        d.log('vendor scan', str(path), result['status'])
    return 0 if result['status'] == 'SCANNED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
