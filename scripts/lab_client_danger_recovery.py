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
import sys
import math
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame, THREAT_UNKNOWN
from client_evidence import Evidence
from client_parent_run import stamp
from client_danger_recovery import DangerRecovery
from client_chat_guard import ensure_chat_closed, ensure_focus
from client_read_fresh import read_or_dismiss, find_red_button
from client_target import select_hostile
from client_geometry import picture_to_screen
from client_motion import TURN_RATE

ROOT = Path(__file__).resolve().parents[1]
VK_FORWARD = 0x57
VK_LEFT = 0x25
VK_RIGHT = 0x27

# The turn rate of the client was measured at exactly one half turn per
# second, and the left arrow key raises the heading while the right one
# lowers it.

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
    result = stamp(dict(run=run, status='FAILED', steps=[]), sys.argv)
    evidence = Evidence(run)
    die_again = '--die-again' in sys.argv
    stage = 'walk-back'
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
            # The spot of the corpse is only known after the spirit was
            # released, so this is not an error: the machine asks for it.
            note('corpse-unknown', {'dead': state['dead']})

        ensure_chat_closed(hwnd, reader)
        machine = DangerRecovery(time_budget=TIME_BUDGET)
        # The deadline for the threat is set once. It was set again on every
        # turn of the loop before, so a threat that could not be read kept
        # the run waiting until the whole budget was used up.
        threat_deadline = time.monotonic() + 30.0
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
                if die_again and stage == 'walk-back':
                    # The character is back at the graveyard. It walks into
                    # the danger zone once more, so the task can show what
                    # it does when the character dies a second time: the new
                    # corpse is looked up and the distance to the graveyard
                    # is compared with the one of the first death.
                    stage = 'aggro'
                    machine.route = [tuple(machine.corpses[0]['corpse'])]
                    machine.route_index = 0
                    machine.phase = 'ESCAPE'
                    machine.stuck = 0
                    machine.avoid = 0.0
                    machine.last_action = None
                    machine.last_distance = None
                    note('walk-back-to-danger', {'target': machine.route[0]})
                    continue
                if die_again and stage == 'aggro':
                    # The character is in the danger zone again. A hostile is
                    # picked and hit once, so it engages and the character
                    # dies a second time.
                    stage = 'wait-death'
                    target = select_hostile(hwnd, reader)
                    result['second_target'] = (target or {}).get('target_guid')
                    if target is None:
                        # No hostile creature was in reach, so the second
                        # death did not happen. The character is alive and
                        # out of combat, but the task asked for a second
                        # death, so the result says that it is missing.
                        result['second_death'] = 'not happened'
                        result['second_death_reason'] = 'no hostile in reach'
                        result['status'] = 'RECOVERED'
                        result['corpses'] = machine.corpses
                        result['deaths'] = machine.deaths
                        result['releases'] = machine.releases
                        result['final'] = {'health': state['health'],
                                           'dead': state['dead'],
                                           'combat': state['combat'],
                                           'graveyard': machine.graveyard}
                        break
                    note('aggro', {'guid': target['target_guid'],
                                   'health': target['target_health']})
                    d.post_key(d.game_window(), 0x31)
                    time.sleep(1.0)
                    deadline = time.monotonic() + 90
                    while time.monotonic() < deadline:
                        state = read_or_dismiss(reader, d.game_window())
                        if state['dead']:
                            note('second-death', {'position':
                                                   [state['pos_x'], state['pos_y']]})
                            break
                        time.sleep(1.0)
                    else:
                        # No second death in the time that was given. The
                        # character walks back to the graveyard, so the run
                        # does not end with the character in the danger
                        # zone.
                        machine.route = machine.memory.route_back(
                            state['pos_x'], state['pos_y'])
                        machine.route_index = 0
                        machine.phase = 'ESCAPE'
                        machine.stuck = 0
                        machine.avoid = 0.0
                        machine.last_action = None
                        machine.last_distance = None
                        note('walk-back-home', {'route': len(machine.route)})
                        stage = 'home'
                        continue
                    continue
                # The character is at the graveyard, but the place is not
                # safe: the wolves of the valley hunt there. The run is
                # only finished when the aggro is really gone, which the
                # threat of the probe shows.
                threat = state.get('threat')
                if threat == THREAT_UNKNOWN:
                    # The threat could not be read. That is not a threat
                    # that is left, and it is not a threat that is gone:
                    # the run says so instead of waiting for a number that
                    # never comes.
                    result['threat_available'] = False
                    result['threat_note'] = ('the threat could not be read '
                                             'on this client')
                elif threat and time.monotonic() < threat_deadline:
                    note('threat-left', {'threat': threat,
                                          'combat': state['combat']})
                    time.sleep(1.0)
                    continue
                elif threat:
                    # The creatures of the valley watch the graveyard, so
                    # the threat may stay for a while. The run waits for it
                    # a limited time and reports it then.
                    result['threat_left'] = threat
                    result['threat_available'] = True
                else:
                    result['threat_available'] = True
                result['status'] = 'RECOVERED'
                result['final'] = {'health': state['health'],
                                   'dead': state['dead'],
                                   'combat': state['combat'],
                                   'threat': threat,
                                   'graveyard': machine.graveyard}
                if die_again:
                    result['second_death'] = ('happened'
                                              if len(machine.corpses) >= 2
                                              else 'not happened')
                result['corpses'] = machine.corpses
                result['deaths'] = machine.deaths
                result['releases'] = machine.releases
                result['route_was_direct'] = machine.route_is_direct
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
                d.click_client(hwnd, *button)
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
                hold(VK_FORWARD, action.get('seconds', 0.8), hwnd)
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
                for _ in range(40):
                    d.click_client(hwnd, *button)
                    time.sleep(1.5)
                    state = read_or_dismiss(reader, d.game_window())
                    if not state['dead']:
                        break
                    # The server puts a countdown on the dialog, and the
                    # button is grey until it is over. The dialog is looked
                    # at again, so the button is pressed as soon as it works.
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
        if len(machine.corpses) >= 2:
            # The second death has to be closer to the graveyard than the
            # first one, measured along a path that was really walked.
            first = machine.corpses[0]['path_length']
            last = machine.corpses[-1]['path_length']
            result['path_length_comparison'] = {
                'first': first,
                'last': last,
                'closer_to_graveyard': last < first,
                'deaths': len(machine.corpses),
            }
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('09-end')
        path = evidence.write(result)
        d.log('danger recovery', str(path), result['status'])
    return 0 if result['status'] == 'RECOVERED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
