"""Check whether a click on the client changes the picture.

A click on the zoom button of the minimap makes the minimap bigger, so the
picture of the screen tells whether the click arrived. The test is needed
because the clicks on the buttons of the world did nothing, while a click
on the list of the characters worked in an earlier run of the client.

The script clicks the button, takes the picture before and after and writes
down how much of the picture changed.
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

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'

# The button that opens the list of the add-ons, and the area it changes.
ZOOM = (120, 1018)
MINIMAP = (0, 850, 640, 1080)


def difference(first, second, box):
    """The share of the pixels that changed in the area."""
    a = first.crop(box).convert('RGB').tobytes()
    b = second.crop(box).convert('RGB').tobytes()
    changed = sum(1 for x, y in zip(a, b) if x != y)
    return round(changed / float(len(a)), 4)


def main():
    run = 'client_click_reach_' + str(time.time_ns())
    result = stamp(dict(run=run, status='FAILED'), sys.argv)
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.5)
        before = grab_desktop()
        before.save(str(OUT / (run + '_before.png')))
        d.u.SetCursorPos(*ZOOM)
        time.sleep(0.8)
        d.click_client(hwnd, *ZOOM)
        time.sleep(2.0)
        after = grab_desktop()
        after.save(str(OUT / (run + '_after.png')))
        result['minimap_change'] = difference(before, after, MINIMAP)
        result['picture_change'] = difference(before, after,
                                             (0, 0, 1920, 1080))
        result['status'] = 'MEASURED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('click reach', str(path), result['status'])
    return 0 if result['status'] == 'MEASURED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
