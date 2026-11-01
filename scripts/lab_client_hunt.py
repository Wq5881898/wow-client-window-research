"""Walk out of the safe zone until an attackable creature shows up.

The test area has no hostile creatures inside the village, and a target with
more than one health point is needed to observe a failed cast that is
caused by the facing and not by the target dying.
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
from lab_client_minimap_hunt import (grey_blue_pixels, cluster, on_minimap)

ROOT = Path(__file__).resolve().parents[1]
VK_FORWARD = 0x57
VK_TURN_LEFT = 0x25
NAMES = ['Wolf', 'Defias Bandit', 'Kobold Laborer', 'Cougar',
         'Deer', 'Koboid Vermin']
# A creature that leaves combat regenerates quickly in this client version,
# and an elite creature resists the spells of a low character, so the driver
# looks for an ordinary creature that a few casts can finish.
MAX_TARGET_HEALTH = 130
MAX_TARGET_CLASS = 1


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


def send(hwnd, text, settle=1.2, reader=None):
    """Type a slash command, after the chat input was closed."""
    if reader is not None:
        ensure_chat_closed(hwnd, reader)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.4)
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.03)
    time.sleep(0.2)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(settle)


def main():
    run = 'client_hunt_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', scans=[])
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

        for round_index in range(10):
            # The chat input steals the key presses, so it is closed before
            # the character is moved.
            ensure_chat_closed(hwnd, reader)
            found = None
            # The minimap shows the portrait of every hostile creature in the
            # area. Clicking one turns the camera onto it, which is a far
            # better search than walking blind.
            image = grab_desktop()
            groups = [group for group in cluster(grey_blue_pixels(image))
                       if len(group) > 40]
            for marker in groups:
                point = (sum(p[0] for p in marker) // len(marker),
                         sum(p[1] for p in marker) // len(marker))
                if not on_minimap(point):
                    continue
                # A click that misses the round map opens the world map,
                # which hides the screen from the probe.
                close_world_map(hwnd)
                d.click_si(*point)
                time.sleep(1.0)
                for _ in range(6):
                    hold(VK_FORWARD, 1.2, hwnd)
                    d.post_key(hwnd, win32con.VK_TAB)
                    time.sleep(0.6)
                    state = reader()
                    if (state['target_exists'] and state['target_attackable']
                            and state.get('target_class', 1) <= MAX_TARGET_CLASS):
                        found = {'name': 'minimap', 'health': state['target_health'],
                                 'guid': state['target_guid'],
                                 'class': state.get('target_class_name'),
                                 'range': state['spell_range']}
                        break
                if found:
                    break
            if not found:
                # Walk in a straight line with a small turn between the legs,
                # so the path leaves the village instead of circling.
                hold(VK_FORWARD, 8.0, hwnd)
                time.sleep(0.3)
                hold(VK_TURN_LEFT, 0.3, hwnd)
                hold(VK_FORWARD, 6.0, hwnd)
                time.sleep(0.3)
                state = reader()
                # The tab key selects the nearest hostile unit in view.
                for _ in range(4):
                    d.post_key(hwnd, win32con.VK_TAB)
                    time.sleep(0.6)
                    state = reader()
                    if (state['target_exists'] and state['target_attackable']
                            and state['target_health'] <= MAX_TARGET_HEALTH
                            and state.get('target_class', 1) <= MAX_TARGET_CLASS):
                        found = {'name': 'tab', 'health': state['target_health'],
                                 'guid': state['target_guid'],
                                 'class': state.get('target_class_name'),
                                 'range': state['spell_range']}
                        break
            if not found:
                for name in NAMES:
                    send(hwnd, '/target ' + name, settle=0.7, reader=reader)
                    state = reader()
                    if (state['target_exists'] and state['target_attackable']
                            and state['target_health'] <= MAX_TARGET_HEALTH
                            and state.get('target_class', 1) <= MAX_TARGET_CLASS):
                        found = {'name': name, 'health': state['target_health'],
                                 'guid': state['target_guid'],
                                 'class': state.get('target_class_name'),
                                 'range': state['spell_range']}
                        break
            result['scans'].append({'round': round_index,
                                    'position': [state['pos_x'], state['pos_y']],
                                    'found': found})
            if found:
                result['target'] = found
                evidence.capture('01-found', state)
                result['status'] = 'TARGET_FOUND'
                break
        if result['status'] != 'TARGET_FOUND':
            raise ValueError('no hostile creature was found')
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('02-end')
        path = evidence.write(result)
        d.log('hunt run', path, result['status'])
    return 0 if result['status'] == 'TARGET_FOUND' else 1


if __name__ == '__main__':
    raise SystemExit(main())
