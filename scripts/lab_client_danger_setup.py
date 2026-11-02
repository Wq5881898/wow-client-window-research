"""Make the character die in the danger zone.

The target is acquired the same way the recovery drill does it, but the run
does not stop at low health: it keeps standing in the reach of the hostile
until the character is dead. The place of the death and the place of the
corpse are recorded, so the recovery can be planned from real data.
"""
import json
import time
from pathlib import Path
import win32con
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
from client_evidence import Evidence
from client_chat_guard import ensure_chat_closed, ensure_no_modal
from client_read_fresh import read_fresh

ROOT = Path(__file__).resolve().parents[1]
FIREBALL = 133
VK_FORWARD = 0x57
TARGET_NAME = 'Diseased Young Wolf'
DEADLINE = 240.0


def hide_consoles():
    import win32gui
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


def send_command(hwnd, text, reader, settle=1.2):
    ensure_chat_closed(hwnd, reader)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.5)
    import win32gui
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.04)
    time.sleep(0.2)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(settle)
    return reader()


def hold(vk, seconds):
    import ctypes
    key = d.INPUT()
    key.type = 1
    key.union.ki = d.KEYBDINPUT(vk, 0, 0, 0, None)
    d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key))
    time.sleep(seconds)
    key.union.ki.dwFlags = 2
    d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key))


def cast_fireball(hwnd, reader, attempts=4):
    """Cast fireball with the key of the action bar.

    The chat is not used: the chat input takes the focus away from the
    game and the panel of the probe stops being updated while it is open.
    Fireball sits in the first slot of the action bar.
    """
    for _ in range(attempts):
        d.post_key(hwnd, 0x31)
        time.sleep(0.8)
        state = reader()
        if state['cast_started'] or state['cast_succeeded']:
            time.sleep(1.2)
            return reader()
    return reader()


def select_hostile(hwnd, reader):
    """Select the hostile creature that is closest.

    The tab key selects the next hostile in sight, so it is pressed until
    a hostile that is not the wolf of the standard area shows up, or until
    the cycle has come back to the first one. A command in the chat is not
    used: the chat input takes the focus away and the panel of the probe
    stops being updated while it is open.
    """
    seen = []
    found = []
    for step in range(12):
        ensure_chat_closed(hwnd, reader)
        d.post_key(hwnd, win32con.VK_TAB)
        time.sleep(0.7)
        state = read_fresh(reader, hwnd)
        if not state['target_exists']:
            continue
        guid = state['target_guid']
        if guid in seen:
            continue
        seen.append(guid)
        if state['target_attackable'] and state['target_class'] == 1:
            found.append(state)
    if not found:
        return None
    # The weakest ordinary creature in reach is used, so the run is short.
    return min(found, key=lambda s: s['target_health'])


def main():
    run = 'client_danger_setup_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', timeline=[])
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        def fresh():
            return read_fresh(reader, hwnd)

        ensure_no_modal(hwnd, reader)
        start = reader()
        result['start'] = {'health': start['health'], 'dead': start['dead'],
                           'position': [start['pos_x'], start['pos_y']]}
        evidence.capture('01-start', start)
        if start['dead']:
            raise ValueError('the character is already dead')

        state = select_hostile(hwnd, reader)
        if state is None:
            raise ValueError('could not acquire a hostile target')
        result['target_guid'] = state['target_guid']
        result['target_health'] = state['target_health']
        result['target_class'] = state.get('target_class_name')
        evidence.capture('02-targeted', state)

        # Close the distance first: a miss at long range leaves the
        # character untouched, so the hostile would never engage.
        for attempt in range(30):
            state = fresh()
            if state['spell_range'] == 1:
                break
            hold(VK_FORWARD, 0.6)
            time.sleep(0.2)
        state = fresh()
        result['range'] = state['spell_range']
        if state['spell_range'] != 1:
            raise ValueError('could not reach cast range')
        evidence.capture('03-in-range', state)

        # One hit pulls the aggro. The character then stops attacking.
        state = cast_fireball(hwnd, reader)
        result['aggro_pull'] = {'succeeded': state['cast_succeeded'],
                                'combat': state['combat'],
                                'target_health': state['target_health']}
        evidence.capture('04-aggro-pulled', state)
        if not state['combat']:
            raise ValueError('the hostile did not engage')

        # Stand in the reach of the hostile until the character is dead.
        deadline = time.monotonic() + DEADLINE
        last_health = start['health']
        while time.monotonic() < deadline:
            state = fresh()
            if state['health'] != last_health:
                last_health = state['health']
                result['timeline'].append({'health': state['health'],
                                           'host_monotonic': time.monotonic()})
            if state['dead']:
                break
            time.sleep(0.6)
        state = fresh()
        result['dead'] = state['dead']
        result['death_position'] = [state['pos_x'], state['pos_y']]
        result['corpse'] = [state.get('corpse_x'), state.get('corpse_y')]
        result['corpse_exists'] = state.get('corpse_exists')
        evidence.capture('05-dead', state)
        if not state['dead']:
            raise ValueError('the character did not die in time')
        result['status'] = 'DEAD'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('09-end')
        path = evidence.write(result)
        d.log('danger setup', str(path), result['status'])
    return 0 if result['status'] == 'DEAD' else 1


if __name__ == '__main__':
    raise SystemExit(main())
