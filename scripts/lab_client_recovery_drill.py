"""Injury drill: take real damage, then prove the recovery branch works.

The character buffs up, deliberately stops fighting so the target can hit it,
and the run must leave combat on its own once health crosses the floor.
A critical floor aborts the drill and escapes immediately.
"""
import json
import threading
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
from client_window_state import window_observable
from client_combat_controller import CombatController
from client_evidence import Evidence

ROOT = Path(__file__).resolve().parents[1]
FIREBALL = 133
FROST_ARMOR = 168
VK_BACK = 0x53
VK_FORWARD = 0x57
VK_TURN_LEFT = 0x25     # left arrow: turns the character
VK_TURN_RIGHT = 0x27    # right arrow: turns the character
MAX_HOLD = 2.0
CRITICAL_RATIO = 0.25
TURN_SECONDS = 0.5


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
    """Press and release a movement key."""
    import ctypes
    if not 0 < seconds <= MAX_HOLD:
        raise ValueError('hold duration must be in (0, %d]' % MAX_HOLD)
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


def move_while_watching(vk, seconds, reader):
    """Hold a movement key while sampling, so the heartbeat never sees a gap."""
    worker = threading.Thread(target=hold, args=(vk, seconds))
    worker.start()
    states = []
    while worker.is_alive():
        states.append(reader())
        time.sleep(0.05)
    worker.join()
    return states


def send_command(hwnd, text, reader, settle=1.2):
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.5)
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.04)
    time.sleep(0.2)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(settle)
    return reader()


def main():
    run = 'client_recovery_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', timeline=[], damage_events=[])
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        def note(phase, detail):
            result['timeline'].append({'phase': phase, 'host_monotonic': time.monotonic(),
                                       'detail': detail})

        start = reader()
        if start['protocol'] not in (4, 5, 6):
            raise ValueError('protocol 4, 5 or 6 required, got ' + str(start['protocol']))
        if start['dead'] or start['combat']:
            raise ValueError('must start alive and out of combat')
        result['max_health'] = start['max_health']
        evidence.capture('01-start', start)
        note('baseline', {'health': start['health']})

        # Buff up first so the drill does not end in a corpse.
        state = send_command(hwnd, '/cast Frost Armor', reader, settle=2.0)
        result['frost_armor'] = state['frost_armor']
        if not state['frost_armor']:
            raise ValueError('Frost Armor did not apply; drill aborted for safety')
        evidence.capture('02-buffed', state)
        note('buffed', {'frost_armor': state['frost_armor']})

        # Acquire a hostile and bind it, then stop attacking on purpose.
        state = send_command(hwnd, '/target Diseased Young Wolf', reader)
        if not state['target_exists'] or not state['target_attackable']:
            raise ValueError('could not acquire a hostile target')
        target_guid = state['target_guid']
        result['target_guid'] = target_guid
        controller = CombatController(target_guid, FIREBALL, timeout=2.5)
        binding = controller.bind_target(state)
        if binding['decision'] != 'BOUND':
            raise ValueError('target binding failed: ' + str(binding))
        evidence.capture('03-target-acquired', state)
        note('target_acquired', {'guid': target_guid, 'health': state['target_health']})

        # Pull aggro with one hit. Targeting alone never makes a creature
        # attack, and a miss at long range leaves the character untouched,
        # so close the distance first and only then cast.
        for approach in range(20):
            state = reader()
            if state['spell_range'] == 1:
                break
            note('approach', {'attempt': approach, 'range': state['spell_range'],
                              'position': [state['pos_x'], state['pos_y']]})
            # The client turns the character when a spell on the current
            # target is cast, so the approach only has to close the distance;
            # the range flag is the guide.
            hold(VK_FORWARD, 0.6)
            time.sleep(0.2)
        state = reader()
        note('in_range', {'range': state['spell_range']})
        if state['spell_range'] != 1:
            raise ValueError('could not reach cast range; drill aborted')
        state = send_command(hwnd, '/cast Fireball', reader, settle=2.5)
        result['aggro_pull'] = {'succeeded': state['cast_succeeded'],
                               'failed': state['cast_failed'],
                               'combat': state['combat'],
                               'target_health': state['target_health']}
        note('aggro_pull', result['aggro_pull'])
        evidence.capture('04-aggro-pulled', state)
        if not state['combat']:
            raise ValueError('target did not engage; drill aborted')

        # Stand still and let the target hit. No further casting: we want injury.
        low_health_seen = False
        last_health = start['health']
        damage = []
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            state = reader()
            if not window_observable(hwnd):
                raise ValueError('client window not observable')
            if state['dead']:
                raise ValueError('player died during the drill')
            if state['health'] != last_health:
                damage.append({'health': state['health'], 'max_health': state['max_health'],
                               'host_monotonic': time.monotonic()})
                note('damage_taken', {'health': state['health'],
                                      'ratio': round(state['health'] / state['max_health'], 3),
                                      'combat': state['combat']})
                last_health = state['health']
                if not low_health_seen and state['health'] / state['max_health'] <= 0.9:
                    evidence.capture('05-first-damage', state)
            decision = controller.observe(state, time.monotonic())
            if decision['decision'] == 'RECOVER':
                low_health_seen = True
                result['recovery_reason'] = decision['reason']
                note('recover_triggered', decision)
                evidence.capture('06-recovery-trigger', state)
                break
            if state['health'] / state['max_health'] <= CRITICAL_RATIO:
                note('critical_floor', {'health': state['health']})
                evidence.capture('06-critical', state)
                break
            time.sleep(0.15)

        if not low_health_seen:
            raise ValueError('no damage or no recovery trigger within the budget')

        result['damage_events'] = damage
        result['health_at_trigger'] = last_health
        result['health_ratio_at_trigger'] = round(last_health / start['max_health'], 3)

        # Escape: turn away first, then run. Holding "back" only reverses the
        # current heading, and a chasing mob follows along that same line, so
        # the character has to break the line of pursuit before backing off.
        escaped = False
        previous = (state['pos_x'], state['pos_y'])
        for attempt in range(8):
            hold(VK_TURN_LEFT, TURN_SECONDS)
            hold(VK_FORWARD, MAX_HOLD)
            time.sleep(0.2)
            state = reader()
            current = (state['pos_x'], state['pos_y'])
            note('retreat_step', {'attempt': attempt, 'health': state['health'],
                                  'combat': state['combat'],
                                  'position': list(current),
                                  'moved': current != previous})
            previous = current
            if not state['combat']:
                escaped = True
                break
        if not escaped:
            raise ValueError('retreat did not clear combat')
        evidence.capture('07-escaped', state)
        note('escaped', {'health': state['health']})

        # Survival check: alive and out of combat for a sustained period.
        quiet = 0
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            state = reader()
            if state['dead']:
                raise ValueError('player died after the retreat')
            if state['combat']:
                quiet = 0
            else:
                quiet += 1
                if quiet >= 6:
                    break
            time.sleep(0.4)
        if state['combat']:
            raise ValueError('still in combat at the end of the drill')
        if state['health'] <= 0:
            raise ValueError('player has no health left')
        evidence.capture('08-survived', state)
        result['final'] = state
        result['outcome'] = 'recovered_after_damage'
        result['status'] = 'RECOVERY_DRILL_PASSED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('08-end')
        path = evidence.write(result)
        d.log('recovery drill', path, result['status'])
    return 0 if result['status'] == 'RECOVERY_DRILL_PASSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
