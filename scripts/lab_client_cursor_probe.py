"""Read the name of the unit under the cursor at given points.

The script moves the cursor to every point of the list, reads the hash of
the name that the probe reports and writes a picture of the screen for every
point, so the name that the hash belongs to can be read by a human.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'


def main():
    points = []
    for argument in sys.argv[1:]:
        x, y = argument.split(',')
        points.append((int(x), int(y)))
    result = {'points': []}
    hwnd = d.game_window()
    d.ensure_foreground(hwnd)
    for index, (x, y) in enumerate(points):
        d.u.SetCursorPos(int(x), int(y))
        time.sleep(0.4)
        try:
            state = decode(assert_real_frame(grab_desktop()))
        except Exception as exc:
            result['points'].append({'x': x, 'y': y, 'error': repr(exc)})
            continue
        shot = OUT / ('cursor-%02d.png' % index)
        grab_desktop().save(shot)
        result['points'].append({'x': x, 'y': y,
                                 'hash': state.get('cursor_name_hash'),
                                 'picture': str(shot)})
    (OUT / 'cursor-probe.json').write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
