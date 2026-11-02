"""Recover a character that died in a danger zone and walk it to safety.

The run has three parts. The ghost walks to its corpse and confirms the
dialog that revives the character. The character then follows the path it
walked as a ghost back to the graveyard, so the way back is one the server
accepts and not a straight line through the fence. If the character dies
again, the new corpse is picked up and the run starts over.

The decision is made by :mod:`client_danger_recovery`, this script only
carries it out.
"""
import ctypes
import json
import math
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
from client_evidence import Evidence
from client_danger_recovery import DangerRecovery
from client_chat_guard import ensure_chat_closed, ensure_focus
from client_read_fresh import read_or_dismiss, find_red_button
from client_geometry import picture_to_screen

ROOT = Path(__file__).resolve().parents[1]
VK_FORWARD = 0x57
VK_LEFT = 0x25
VK_RIGHT = 0x27

# The turn rate of the client was measured at exactly one half turn per
# second, and the left arrow key raises the heading while the right one
# lowers it.
TURN_RATE = math.pi

# The longest time the whole task may take.
TIME_BUDGET = 240.0


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


def hold(vk, seconds, hwnd):
    """Hold a key down for a while with the client in the foreground."""
    ensure_focus(hwnd)
    key = d.INPUT()
    key.type = 1
    key.union.ki = d.KEYBDINPUT(vk, 0, 0, 0, None)
    if d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key)) != 1:
        raise RuntimeError('key down failed')
    try:
        time.sleep(seconds)
    finally:
        key.union.ki.dwFlags = 2
        if d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key)) != 1:
            raise RuntimeError('key up failed')


def find_resurrect_button(image):
    """The centre of the red button that revives the character.

    The client shows a dialog with the question "Resurrect now?" in the
    upper middle of the screen once the ghost stands on its corpse. The
    button of that dialog is drawn in a strong red, which nothing else in
    that part of the screen is.
    """
    width, height = image.size
    pixels = image.convert('RGB').load()
    rows = {}
    for y in range(int(height * 0.12), int(height * 0.32)):
        found = [x for x in range(int(width * 0.35), int(width * 0.65))
                 if pixels[x, y][0] > 90
                 and pixels[x, y][0] > pixels[x, y][1] * 2.2
                 and pixels[x, y][0] > pixels[x, y][2] * 2.2]
        if len(found) > 30:
            rows[y] = (min(found), max(found))
    if not rows:
        return None
    ys = sorted(rows)
    left = min(rows[y][0] for y in ys)
    right = max(rows[y][1] for y in ys)
    return ((left + right) // 2, (ys[0] + ys[-1]) // 2)


def main():
    run = 'client_danger_recovery_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', steps=[])
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        def note(action, detail):
            result['steps'].append(dict(action=action, detail=detail))

        state = read_or_dismiss(reader, hwnd)
        result['start'] = {
            'health': state['health'], 'dead': state['dead'],
            'position': [state['pos_x'], state['pos_y']],
            'facing': state['facing'],
            'corpse_exists': state.get('corpse_exists'),
            'corpse': [state.get('corpse_x'), state.get('corpse_y')],
        }
        evidence.capture('01-start', state)
        if not state['dead']:
            result['status'] = 'NOT_DEAD'
            note('skip', 'the character is alive')
            path = evidence.write(result)
            d.log('danger recovery', str(path), result['status'])
            return 0
        if not state.get('corpse_exists'):
            result['status'] = 'NO_CORPSE'
            note('skip', 'the client reports no corpse')
            path = evidence.write(result)
            d.log('danger recovery', str(path), result['status'])
            return 0

        ensure_chat_closed(hwnd, reader)
        machine = DangerRecovery(time_budget=TIME_BUDGET)
        while True:
            hwnd = d.game_window()
            state = read_or_dismiss(reader, hwnd)
            action = machine.observe(state, time.monotonic())
            distance = action.get('distance')
            detail = {'distance': distance, 'facing': state['facing'],
                      'position': [state['pos_x'], state['pos_y']],
                      'phase': machine.phase, 'dead': state['dead'],
                      'health': state['health']}
            if action['action'] == 'DONE':
                result['status'] = 'RECOVERED'
                result['final'] = {'health': state['health'],
                                   'dead': state['dead'],
                                   'combat': state['combat'],
                                   'graveyard': machine.graveyard}
                result['corpses'] = machine.corpses
                evidence.capture('02-safe', state)
                break
            if action['action'] == 'GIVE_UP':
                result['status'] = 'FAILED'
                result['reason'] = action.get('reason')
                result['corpses'] = machine.corpses
                evidence.capture('03-given-up', state)
                break
            if action['action'] == 'RELEASE':
                # The window of the death has to be closed before the
                # character becomes a ghost. Its button is the only red
                # button in the upper half of the screen.
                note('release', detail)
                image = grab_desktop()
                button = find_red_button(image)
                result['release_button'] = button
                if button is None:
                    raise ValueError('the death window of the client was not found')
                d.click_si(*button)
                time.sleep(2.0)
                continue
            if action['action'] == 'TURN':
                seconds = min(1.1, max(0.06, abs(action['error']) / TURN_RATE))
                note('turn', dict(detail, direction=action['direction'],
                                  seconds=seconds))
                hold(VK_LEFT if action['direction'] == 'left' else VK_RIGHT,
                     seconds, hwnd)
                continue
            if action['action'] == 'WALK':
                note('walk', detail)
                hold(VK_FORWARD, 0.8, hwnd)
                continue
            if action['action'] == 'ACCEPT':
                note('accept', detail)
                evidence.capture('04-at-corpse', state)
                image = grab_desktop()
                button = find_red_button(image)
                result['dialog_button'] = button
                if button is None:
                    # The button of the dialog sits in the middle of the
                    # upper half of the picture of the client.
                    button = picture_to_screen(hwnd, *action['point'])
                for _ in range(6):
                    d.click_si(*button)
                    time.sleep(1.2)
                    state = reader()
                    if not state['dead']:
                        break
                    found = find_red_button(grab_desktop())
                    if found is not None:
                        button = found
                if state['dead']:
                    result['status'] = 'FAILED'
                    result['reason'] = 'dialog_not_accepted'
                    result['corpses'] = machine.corpses
                    evidence.capture('05-given-up', state)
                    break
                continue
            raise ValueError('unknown action ' + str(action))
        result['corpses'] = machine.corpses
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('09-end')
        path = evidence.write(result)
        d.log('danger recovery', str(path), result['status'])
    return 0 if result['status'] == 'RECOVERED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
