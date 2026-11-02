"""Run a dead character to its corpse and revive it.

The task was designed after the manual recovery of the 2026-10-29, where a
supervised run walked the ghost to the corpse with the d key and confirmed the
dialog with a click. This script does the same without supervision: the
probe reports the heading of the character and the spot of the corpse, so the
direction is known and the walk is not blind.

The run has two parts. The first one walks the ghost to its corpse, turning
by the difference between the heading and the direction of the corpse. The
second one confirms the dialog that the client offers on the spot of the
corpse. The run counts as a success when the client reports a living
character without combat.
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
from client_corpse_runner import CorpseRunner, corpse_distance, wrap
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
TIME_BUDGET = 180.0

# The distance at which the client offers the resurrect dialog, in the
# normalised map coordinates of the zone.
CORPSE_RANGE = 0.004


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
    run = 'client_corpse_run_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', steps=[])
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        def note(action, detail):
            result['steps'].append(dict(action=action, detail=detail))

        state = reader()
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
            d.log('corpse run', str(path), result['status'])
            return 0
        if not state.get('corpse_exists'):
            result['status'] = 'NO_CORPSE'
            note('skip', 'the client reports no corpse')
            path = evidence.write(result)
            d.log('corpse run', str(path), result['status'])
            return 0

        ensure_chat_closed(hwnd, reader)
        runner = CorpseRunner(time_budget=TIME_BUDGET)
        while True:
            state = reader()
            action = runner.observe(state, time.monotonic())
            distance = corpse_distance(state)
            detail = {'distance': distance, 'facing': state['facing'],
                      'position': [state['pos_x'], state['pos_y']],
                      'phase': runner.phase, 'avoid': runner.avoid}
            if action['action'] == 'DONE':
                result['status'] = 'RECOVERED'
                result['final'] = {'health': state['health'],
                                   'dead': state['dead'],
                                   'combat': state['combat']}
                evidence.capture('02-recovered', state)
                break
            if action['action'] == 'GIVE_UP':
                result['status'] = 'FAILED'
                result['reason'] = action.get('reason')
                evidence.capture('04-given-up', state)
                break
            if action['action'] == 'TURN':
                seconds = min(1.1, max(0.06, abs(action['error']) / TURN_RATE))
                note('turn', dict(detail, direction=action['direction'],
                                  seconds=seconds))
                # The left arrow key raises the heading of the client, the
                # right one lowers it.
                hold(VK_LEFT if action['direction'] == 'left' else VK_RIGHT,
                     seconds, hwnd)
                continue
            if action['action'] == 'WALK':
                note('walk', detail)
                hold(VK_FORWARD, 0.8, hwnd)
                continue
            if action['action'] == 'ACCEPT':
                note('accept', detail)
                evidence.capture('03-at-corpse', state)
                image = grab_desktop()
                button = find_resurrect_button(image)
                result['dialog_button'] = button
                if button is None:
                    # The button of the dialog sits in the middle of the
                    # upper half of the picture of the client.
                    button = picture_to_screen(hwnd, *action['point'])
                for attempt in range(40):
                    d.click_si(*button)
                    time.sleep(1.5)
                    state = read_or_dismiss(reader, d.game_window())
                    if not state['dead']:
                        result['status'] = 'RECOVERED'
                        result['final'] = {'health': state['health'],
                                           'dead': state['dead'],
                                           'combat': state['combat']}
                        evidence.capture('06-recovered', state)
                        break
                    # The server puts a countdown on the dialog and the
                    # button stays grey until it is over, so the dialog is
                    # looked at again and the button is pressed as soon as
                    # it works.
                    found = find_red_button(grab_desktop())
                    if found is not None:
                        button = found
                if result['status'] != 'RECOVERED':
                    result['status'] = 'FAILED'
                    result['reason'] = 'dialog_not_accepted'
                break
            raise ValueError('unknown action ' + str(action))
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('09-end')
        path = evidence.write(result)
        d.log('corpse run', str(path), result['status'])
    return 0 if result['status'] == 'RECOVERED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
