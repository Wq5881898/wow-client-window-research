"""Look at the picture while the character walks.

The position of the probe did not change while the character was told to
walk. The picture tells more than the number: the camera follows the
character, and the minimap shows where the character is. If the picture
changes while the key is held, the character moves and the position of
the probe is the thing that does not follow.

The script writes the difference of the picture and of the minimap before
and after the walk.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_driver5 as d
from client_capture import grab_desktop
from client_evidence import Evidence
from client_parent_run import stamp
from client_walk import hold, VK_FORWARD

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'

# The area of the minimap in the picture of the client.
MINIMAP = (1680, 20, 1900, 210)


def difference(first, second, box=None):
    """The share of the pixels that changed."""
    if box:
        first = first.crop(box)
        second = second.crop(box)
    a = first.convert('RGB').tobytes()
    b = second.convert('RGB').tobytes()
    changed = sum(1 for x, y in zip(a, b) if x != y)
    return round(changed / float(len(a)), 4)


def main():
    run = 'client_walk_picture_' + str(time.time_ns())
    result = stamp(dict(run=run, status='FAILED'), sys.argv)
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
        before = grab_desktop()
        before.save(str(OUT / (run + '_before.png')))
        hold(VK_FORWARD, 3.0, hwnd)
        time.sleep(0.5)
        after = grab_desktop()
        after.save(str(OUT / (run + '_after.png')))
        result['picture'] = difference(before, after)
        result['minimap'] = difference(before, after, MINIMAP)
        result['status'] = 'MEASURED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('walk picture', str(path), result['status'])
    return 0 if result['status'] == 'MEASURED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
