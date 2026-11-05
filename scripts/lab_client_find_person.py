"""Find a creature by the hash of its name.

The probe reports the name of the creature under the cursor as a hash, and
the same hash is computed in Python for every name that is wanted. The scan
only puts the cursor on the places where a name can be, so it is quick
enough to look around the character several times.

The script does not claim that it found a merchant: it reports the names it
read with the place where they were found, and the caller decides which of
them is the one that was asked for.
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
from client_names import name_candidates, model_point, spread

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'

# How many places are looked at at most.
LIMIT = 40
# How many directions are looked at.
TURNS = 4


def reader():
    return decode(assert_real_frame(grab_desktop()))


def wanted_hashes(names):
    """The hashes of the names that are looked for."""
    return dict((name_hash(name), name) for name in names)


def main():
    run = 'client_find_person_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', names=[])
    evidence = Evidence(run)
    try:
        wanted = []
        for argument in sys.argv[1:]:
            if argument.startswith('--name='):
                wanted.append(argument.split('=', 1)[1])
        hashes = wanted_hashes(wanted)
        result['wanted'] = [{'name': name, 'hash': digest}
                            for digest, name in hashes.items()]
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
        seen = {}
        for turn in range(TURNS):
            picture = grab_desktop()
            candidates = spread(name_candidates(picture), LIMIT)
            for candidate in candidates:
                point = model_point(candidate)
                d.u.SetCursorPos(int(point[0]), int(point[1]))
                time.sleep(0.2)
                try:
                    state = reader()
                except Exception:
                    continue
                digest = state.get('cursor_name_hash')
                if not digest or digest in seen:
                    continue
                seen[digest] = True
                shot = OUT / ('person-%s.png' % digest)
                grab_desktop().save(shot)
                entry = {'hash': digest, 'point': list(point),
                         'picture': str(shot)}
                if digest in hashes:
                    entry['name'] = hashes[digest]
                    entry['wanted'] = True
                result['names'].append(entry)
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
        found = [entry for entry in result['names'] if entry.get('wanted')]
        result['found'] = found
        result['status'] = 'SCANNED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('09-end')
        path = evidence.write(result)
        d.log('find person', str(path), result['status'])
    return 0 if result['status'] == 'SCANNED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
