"""Drive the combat loop straight into its recovery branch.

The character enters combat first, so the loop starts with a live fight and
must leave it through the low-health recovery path.
"""
import json
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
from client_window_state import window_observable
from client_combat_controller import CombatController, LOW_HEALTH_RATIO
from client_evidence import Evidence
from client_retreat import break_engagement

ROOT = Path(__file__).resolve().parents[1]
FIREBALL = 133
VK_FORWARD = 0x57
VK_TURN_LEFT = 0x25
MAX_HOLD = 2.0


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


def send_command(hwnd, text, reader, settle=1.2):
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.4)
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.03)
    time.sleep(0.2)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(settle)
    return reader()


def main():
    run = 'client_loop_recover_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', timeline=[])
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
        if start['dead'] or start['combat']:
            raise ValueError('must start alive and out of combat')
        evidence.capture('01-start', start)

        # Pull two creatures into the fight so the player takes real damage.
        state = send_command(hwnd, '/target Diseased Young Wolf', reader)
        target_guid = state['target_guid']
        result['target_guid'] = target_guid
        # Target by name, then walk forward. The client turns the character
        # when a spell on the current target is cast, so the approach only has
        # to close the distance; the range flag is the guide.
        for approach in range(20):
            state = reader()
            if state['spell_range'] == 1:
                break
            note('approach', {'attempt': approach, 'range': state['spell_range'],
                              'position': [state['pos_x'], state['pos_y']]})
            hold(VK_FORWARD, 0.6)
            time.sleep(0.2)
        state = reader()
        result['range_before_cast'] = state['spell_range']
        if state['spell_range'] != 1:
            raise ValueError('could not reach cast range; range=' + str(state['spell_range']))
        # Targeting does not turn the character, and the client has no facing
        # readout, so a cast can miss by aiming at empty ground. The client
        # turns the character when it faces the target explicitly.
        state = send_command(hwnd, '/face', reader, settle=1.0)
        result['after_face'] = {'range': state['spell_range']}
        state = send_command(hwnd, '/cast Fireball', reader, settle=3.0)
        result['after_cast'] = {'combat': state['combat'],
                                'succeeded': state['cast_succeeded'],
                                'failed': state['cast_failed'],
                                'ui_errors': state['ui_errors'],
                                'target_health': state['target_health'],
                                'range': state['spell_range']}
        note('aggro_pull', result['after_cast'])
        if not state['combat']:
            raise ValueError('could not pull the first target: ' + str(result['after_cast']))
        if not state['combat']:
            raise ValueError('could not pull the first target')
        evidence.capture('02-in-combat', state)
        note('aggro_pull', {'combat': state['combat'],
                            'target_health': state['target_health']})

        # Ignore the fight and let the damage land: the loop below must be the
        # one that notices the low-health floor and runs the recovery branch.
        controller = CombatController(target_guid, FIREBALL, max_attempts=4, timeout=2.5)
        controller.bind_target(state)
        low_health_seen = False
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            state = reader()
            if not window_observable(hwnd):
                raise ValueError('client window not observable')
            if state['dead']:
                raise ValueError('player died before the recovery branch ran')
            decision = controller.observe(state, time.monotonic())
            note('observe', {'decision': decision['decision'], 'reason': decision['reason'],
                             'health': state['health'], 'combat': state['combat']})
            if decision['decision'] == 'RECOVER':
                low_health_seen = True
                result['recovery_reason'] = decision['reason']
                evidence.capture('03-recovery-trigger', state)
                note('recover_triggered', decision)
                break
            time.sleep(0.15)

        if not low_health_seen:
            raise ValueError('the low-health branch never triggered')

        # This is the combat loop's own recovery path.
        try:
            steps = break_engagement(hwnd, reader, steps=8, hold_seconds=MAX_HOLD)
        except ValueError as exc:
            note('retreat_failed', {'error': str(exc)})
            raise ValueError('retreat did not clear combat; recovery unproven')
        for step in steps:
            note('retreat_step', step)
        state = reader()
        evidence.capture('04-escaped', state)
        note('recover_result', {'health': state['health'], 'combat': state['combat'],
                                'dead': state['dead']})

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
            raise ValueError('still in combat at the end of the run')
        evidence.capture('05-survived', state)
        result['final'] = state
        result['outcome'] = 'recovered_after_damage'
        result['status'] = 'LOOP_RECOVERY_PASSED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('06-end')
        path = evidence.write(result)
        d.log('loop recovery run', path, result['status'])
    return 0 if result['status'] == 'LOOP_RECOVERY_PASSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
