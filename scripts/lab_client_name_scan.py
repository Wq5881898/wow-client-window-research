"""Name the people around the character.

The name of a person is written above the model in the picture, so the
places where a name can be are found first and only there the cursor is
put. The scan is therefore short and it finds the small models that a grid
over the whole screen misses.

Every name that is found is reported with the hash of the name, so the
driver can look for a creature by name.
"""
import ctypes
import ctypes
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
from client_names import name_candidates, model_point, spread

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'

# How many places are looked at.
LIMIT = 24
# The pause between two probes.
PAUSE = 0.15


def reader():
    return decode(assert_real_frame(grab_desktop()))


def main():
    run = 'client_name_scan_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', names=[])
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
        seen = {}
        for turn in range(4):
            picture = grab_desktop()
            candidates = spread(name_candidates(picture), LIMIT)
            result['turns'] = result.get('turns', 0) + 1
            for candidate in candidates:
                point = model_point(candidate)
                d.u.SetCursorPos(int(point[0]), int(point[1]))
                time.sleep(PAUSE)
                try:
                    reading = reader()
                except Exception:
                    continue
                digest = reading.get('cursor_name_hash')
                if not digest or digest == name_hash(''):
                    continue
                if digest in seen:
                    continue
                seen[digest] = True
                shot = OUT / ('name-%s.png' % digest)
                grab_desktop().save(shot)
                result['names'].append({'hash': digest,
                                        'at': [point[0], point[1]],
                                        'text_width': candidate['right']
                                        - candidate['left'],
                                        'picture': str(shot)})
            evidence.capture('02-turn-%d' % turn, None)
            # The character looks into another direction, so the names of the
            # other side are found as well.
            key = d.INPUT()
            key.type = 1
            key.union.ki = d.KEYBDINPUT(0x27, 0, 0, 0, None)
            d.SendInput(1, ctypes.byref(key), ctypes.sizeof(d.INPUT))
            time.sleep(1.1)
            key.union.ki.dwFlags = 2
            d.SendInput(1, ctypes.byref(key), ctypes.sizeof(d.INPUT))
            time.sleep(0.5)
        result['status'] = 'SCANNED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('09-end')
        path = evidence.write(result)
        d.log('name scan', str(path), result['status'])
    return 0 if result['status'] == 'SCANNED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
