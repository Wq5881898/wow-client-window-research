"""Walk to a hostile marker on the minimap and select it.

The minimap shows the portrait of every hostile creature in the area.
Clicking the portrait turns the camera onto it, and the tab key then selects
the creature that is in front of the character. The script reports the
classification of the creature it found, so an elite one can be skipped.
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
from client_chat_guard import ensure_chat_closed, ensure_focus, close_world_map
from lab_client_minimap_hunt import (grey_blue_pixels, cluster, on_minimap,
                                     MINIMAP_CENTER, MINIMAP_RADIUS)

ROOT = Path(__file__).resolve().parents[1]
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


def hold(vk, seconds, hwnd=None):
    import ctypes
    if hwnd is not None:
        ensure_focus(hwnd)
    key = d.INPUT()
    key.type = 1
    key.union.ki = d.KEYBDINPUT(vk, 0, 0, 0, None)
    try:
        if d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key)) != 1:
            raise RuntimeError('key down failed')
        time.sleep(seconds)
    finally:
        key.union.ki.dwFlags = 2
        if d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key)) != 1:
            raise RuntimeError('key up failed')


def main():
    run = 'client_marker_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', attempts=[])
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        close_world_map(hwnd, reader)
        for attempt in range(8):
            ensure_chat_closed(hwnd, reader)
            image = grab_desktop()
            groups = [group for group in cluster(grey_blue_pixels(image))
                      if len(group) > 40]
            usable = []
            for group in groups:
                point = (sum(p[0] for p in group) // len(group),
                         sum(p[1] for p in group) // len(group))
                if on_minimap(point):
                    usable.append((point, len(group)))
            result['attempts'].append({'attempt': attempt,
                                       'markers': len(usable)})
            if not usable:
                hold(TURN, 0.5, hwnd)
                hold(WALK, 3.0, hwnd)
                continue
            # The marker closest to the player arrow is the easiest to reach.
            point, size = min(usable,
                               key=lambda item: abs(item[0][0] - MINIMAP_CENTER[0])
                               + abs(item[0][1] - MINIMAP_CENTER[1]))
            close_world_map(hwnd, reader)
            d.click_si(*point)
            time.sleep(1.2)
            selected = None
            for _ in range(12):
                # The camera points at the creature now, so it is in the
                # middle of the screen. Clicking it selects it.
                d.click_si(960, 430)
                time.sleep(0.4)
                state = reader()
                if state['target_exists'] and state['target_attackable']:
                    selected = {'guid': state['target_guid'],
                                'health': state['target_health'],
                                'class': state.get('target_class_name'),
                                'class_id': state.get('target_class'),
                                'range': state['spell_range']}
                    break
                # Otherwise walk towards the point the camera shows.
                d.click_si(960, 760)
                hold(WALK, 0.8, hwnd)
                d.post_key(hwnd, win32con.VK_TAB)
                time.sleep(0.4)
                state = reader()
                if state['target_exists'] and state['target_attackable']:
                    selected = {'guid': state['target_guid'],
                                'health': state['target_health'],
                                'class': state.get('target_class_name'),
                                'class_id': state.get('target_class'),
                                'range': state['spell_range']}
                    break
            if selected:
                result['target'] = selected
                evidence.capture('01-target', reader())
                result['status'] = 'TARGET_FOUND'
                break
        if result['status'] != 'TARGET_FOUND':
            raise ValueError('no hostile was reached through the minimap')
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('02-end')
        path = evidence.write(result)
        d.log('marker hunt run', path, result['status'])
    return 0 if result['status'] == 'TARGET_FOUND' else 1


if __name__ == '__main__':
    raise SystemExit(main())
