"""Use the world map to travel to a named place.

Clicking a location on the world map makes the client walk there, which
does not need any knowledge about the direction the character faces.
"""
import json
import sys
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
from client_evidence import Evidence
from client_chat_guard import ensure_focus, close_world_map

ROOT = Path(__file__).resolve().parents[1]
# The world map fills the screen when it is open. The zone list of the top
# left corner opens the zone map, where the places are named.
MAP_CLOSE = (1857, 45)
ZONE_LIST = (196, 58)
# Places on the world map of Elwynn Forest, in screen pixels.
# Places on the world map of Elwynn Forest, in screen pixels of the
# 1920 wide desktop. The map was measured on a 1200 wide copy, so the
# positions are scaled by one and a half.
PLACES = {
    'Goldshire': (792, 704),
    'NorthshireValley': (947, 477),
    'NorthshireWest': (885, 544),
    'NorthshireSouth': (947, 504),
    'NorthshireFarms': (976, 512),
    'CrystalLake': (960, 380),
}


def hide_consoles():
    def cb(hwnd, _):
        try:
            cls = win32gui.GetClassName(hwnd)
            title = win32gui.GetWindowText(hwnd)
        except Exception:
            return True
        if cls == 'ConsoleWindowClass' or 'python.exe' in title.lower():
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            except Exception:
                pass
        return True
    win32gui.EnumWindows(cb, None)


def main():
    run = 'client_travel_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', steps=[])
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    destination = 'Goldshire'
    if '--place' in sys.argv:
        destination = sys.argv[sys.argv.index('--place') + 1]
    result['place'] = destination
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        close_world_map(hwnd, reader)
        before = reader()
        result['start'] = {'health': before['health'],
                           'position': [before['pos_x'], before['pos_y']]}
        evidence.capture('01-start', before)

        # Open the world map with the m key.
        ensure_focus(hwnd)
        d.post_key(hwnd, 0x4D)
        time.sleep(1.5)
        evidence.capture('02-map')
        image = grab_desktop()
        image.resize((1200, 675)).save('.cache/desktop-check/travel-map.png')

        # The world map of the zone shows the named places. Clicking one
        # makes the client walk there, which does not need any knowledge
        # about the direction the character faces.
        d.click_si(*PLACES[destination])
        time.sleep(1.5)
        # The map has to be closed, it hides the telemetry of the probe.
        close_world_map(hwnd, reader)
        evidence.capture('04-travel-ordered')
        result['status'] = 'TRAVEL_ORDERED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('05-end')
        path = evidence.write(result)
        d.log('travel run', path, result['status'])
    return 0 if result['status'] == 'TRAVEL_ORDERED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
