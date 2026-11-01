"""Find a hostile creature through the markers on the minimap.

The minimap shows the portrait of every hostile creature in the area. The
markers are grey blue shields, which are easy to tell apart from the white
arrow of the player and from the coloured dots of other players. Clicking a
marker turns the camera towards that creature, so the driver can walk there
and select it with the tab key.
"""
import json
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
from client_evidence import Evidence
from client_chat_guard import close_world_map

ROOT = Path(__file__).resolve().parents[1]
MINIMAP = (1690, 30, 1905, 235)
# The round map in the corner. A click outside of it opens the world map,
# which covers the screen and hides the telemetry of the probe.
MINIMAP_CENTER = (1800, 145)
MINIMAP_RADIUS = 82
WALK = 0x57
TURN = 0x25


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


def hold(vk, seconds):
    import ctypes
    key = d.INPUT()
    key.type = 1
    key.union.ki = d.KEYBDINPUT(vk, 0, 0, 0, None)
    try:
        d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key))
        time.sleep(seconds)
    finally:
        key.union.ki.dwFlags = 2
        d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key))


def grey_blue_pixels(image):
    """Return the pixels that look like a hostile marker on the minimap."""
    left, top, right, bottom = MINIMAP
    region = image.crop((left, top, right, bottom)).convert('RGB')
    found = []
    for y in range(region.height):
        for x in range(region.width):
            r, g, b = region.getpixel((x, y))
            # The hostile portrait is a desaturated blue grey.
            if 90 < r < 160 and 100 < g < 165 and 110 < b < 175 \
                    and b > r and abs(int(r) - int(g)) < 25:
                found.append((left + x, top + y))
    return found


def cluster(points, radius=14):
    """Group the marker pixels into single markers."""
    groups = []
    for point in points:
        for group in groups:
            if any(abs(point[0] - member[0]) <= radius
                   and abs(point[1] - member[1]) <= radius
                   for member in group):
                group.append(point)
                break
        else:
            groups.append([point])
    return groups


def on_minimap(point):
    """True when the point lies inside the round map of the corner."""
    dx = point[0] - MINIMAP_CENTER[0]
    dy = point[1] - MINIMAP_CENTER[1]
    return dx * dx + dy * dy <= MINIMAP_RADIUS * MINIMAP_RADIUS


def main():
    run = 'client_minimap_hunt_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', markers=[])
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        # A stray click can leave the world map open, and it hides the
        # telemetry of the probe.
        close_world_map(hwnd, reader)

        for attempt in range(12):
            image = grab_desktop()
            points = grey_blue_pixels(image)
            groups = [group for group in cluster(points) if len(group) > 40]
            result['markers'] = [{'x': sum(p[0] for p in group) // len(group),
                                  'y': sum(p[1] for p in group) // len(group),
                                  'size': len(group)} for group in groups]
            evidence.capture('01-minimap')
            if not groups:
                hold(TURN, 0.4)
                hold(WALK, 2.0)
                continue
            # The marker closest to the player arrow is the easiest to reach.
            marker = min(groups,
                         key=lambda group: min(abs(p[0] - 1800) + abs(p[1] - 110)
                                               for p in group))
            point = (sum(p[0] for p in marker) // len(marker),
                     sum(p[1] for p in marker) // len(marker))
            if not on_minimap(point):
                continue
            # A click that misses the round map opens the world map, which
            # hides the screen from the probe.
            close_world_map(hwnd)
            d.click_si(*point)
            time.sleep(1.2)
            # Walk towards the turned camera.
            for _ in range(8):
                d.post_key(hwnd, win32con.VK_TAB)
                time.sleep(0.5)
                state = reader()
                if state['target_exists'] and state['target_attackable']:
                    result['target'] = {'guid': state['target_guid'],
                                        'health': state['target_health'],
                                        'range': state['spell_range']}
                    evidence.capture('02-target', state)
                    result['status'] = 'TARGET_FOUND'
                    break
                hold(WALK, 0.8)
            if result['status'] == 'TARGET_FOUND':
                break
        if result['status'] != 'TARGET_FOUND':
            raise ValueError('no hostile was reached through the minimap')
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('minimap hunt run', path, result['status'])
    return 0 if result['status'] == 'TARGET_FOUND' else 1


if __name__ == '__main__':
    raise SystemExit(main())
