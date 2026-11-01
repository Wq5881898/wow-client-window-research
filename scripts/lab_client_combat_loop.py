"""Full combat loop: acquire a target, fight it, retreat when needed, verify survival.

The loop is bounded in every direction: target must be a specific hostile,
casts are budgeted, health has a floor, and the run ends with a survival check
rather than a cast count.
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
from client_combat_controller import CombatController, LOW_HEALTH_RATIO
from client_evidence import Evidence
from client_retreat import break_engagement
from client_facing import turn_step

ROOT = Path(__file__).resolve().parents[1]
FIREBALL = 133
VK_FORWARD = 0x57
VK_BACK = 0x53
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


def send_command(hwnd, text, reader, settle=1.2):
    """Type a chat command and return the state after it had time to act."""
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.5)
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.04)
    time.sleep(0.2)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(settle)
    return reader()


def cast(hwnd, text, reader, timeout=6.0, on_tick=None):
    """Type a cast command and return the telemetry after the client acted.

    The command is typed by a worker thread so the caller can keep sampling
    while the cast is in flight; a long cast must not look like a dead link.
    """
    before = reader()

    def worker():
        d.post_key(hwnd, win32con.VK_RETURN)
        time.sleep(0.5)
        for character in text:
            win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
            time.sleep(0.05)
        time.sleep(0.3)
        d.post_key(hwnd, win32con.VK_RETURN)

    thread = threading.Thread(target=worker)
    thread.start()
    deadline = time.monotonic() + timeout
    state = before
    while time.monotonic() < deadline:
        state = reader()
        if on_tick is not None:
            on_tick(state)
        if (state['cast_succeeded'] != before['cast_succeeded']
                or state['cast_failed'] != before['cast_failed']
                or state['ui_errors'] != before['ui_errors']):
            break
        time.sleep(0.06)
    thread.join()
    return state


def move_while_watching(hwnd, vk, seconds, reader, deadline_check=None):
    """Hold a movement key while sampling, so the heartbeat never sees a gap."""
    worker = threading.Thread(target=hold, args=(vk, seconds))
    worker.start()
    states = []
    while worker.is_alive():
        states.append(reader())
        if deadline_check is not None:
            deadline_check(states[-1])
        time.sleep(0.05)
    worker.join()
    return states


def main():
    run = 'client_combat_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', timeline=[], errors=[])
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
        if start['protocol'] != 4:
            raise ValueError('protocol 4 required, got ' + str(start['protocol']))
        if start['dead'] or start['combat']:
            raise ValueError('must start alive and out of combat')
        evidence.capture('01-start', start)
        note('baseline', {'health': start['health'], 'position': [start['pos_x'], start['pos_y']]})

        # Acquire a hostile target and bind its identity.
        target_name = result.get('target', 'Diseased Young Wolf')
        state = send_command(hwnd, '/target ' + target_name, reader)
        if not state['target_exists'] or not state['target_attackable']:
            raise ValueError('could not acquire a hostile target')
        target_guid = state['target_guid']
        result['target_guid'] = target_guid
        result['target_name'] = target_name
        result['target_health_at_start'] = state['target_health']
        evidence.capture('02-target-acquired', state)
        note('target_acquired', {'guid': target_guid, 'health': state['target_health'],
                                 'distance': state['target_distance']})

        controller = CombatController(target_guid, FIREBALL, max_attempts=4, timeout=2.5)
        binding = controller.bind_target(state)
        if binding['decision'] != 'BOUND':
            raise ValueError('target binding failed: ' + str(binding))

        deadline = time.monotonic() + 90
        last_evidence = time.monotonic()
        final = None
        while time.monotonic() < deadline:
            state = reader()
            if not window_observable(hwnd):
                raise ValueError('client window not observable')
            decision = controller.observe(state, time.monotonic())
            note('observe', decision)

            if decision['decision'] == 'CAST_ALLOWED':
                controller.record_attempt()
                result['casts'] = result.get('casts', 0) + 1
                # The cast runs in a worker thread; keep reading telemetry so
                # the heartbeat stays alive while the spell is in flight.
                after = cast(hwnd, '/cast Fireball', reader,
                             on_tick=lambda s: controller.heartbeat(
                                 s, time.monotonic()))
                note('cast_result', {
                    'succeeded': after['cast_succeeded'],
                    'failed': after['cast_failed'],
                    'ui_errors': after['ui_errors'],
                    'target_health': after['target_health'],
                    'player_health': after['health'],
                })
                state = after
                if time.monotonic() - last_evidence > 12:
                    evidence.capture('03-mid-fight', state)
                    last_evidence = time.monotonic()
                if after['health'] < after['max_health'] * LOW_HEALTH_RATIO:
                    # Aborting the run here would leave the character in
                    # combat. Low health is a recovery trigger, not an exit.
                    note('health_floor', {'health': after['health'],
                                          'ratio': round(after['health'] / after['max_health'], 3)})
                    decision = {'decision': 'RECOVER', 'reason': 'low_health'}
                else:
                    continue

            if decision['decision'] == 'CLOSE_DISTANCE':
                # The target is out of range. Fireball reaches 30 yards, so
                # walk forward until the range check flips to in-range.
                before_distance = state.get('target_distance', 0)
                moved = move_while_watching(hwnd, VK_FORWARD, 0.6, reader)
                after_state = moved[-1] if moved else reader()
                note('close_distance', {
                    'distance_before': before_distance,
                    'distance_after': after_state.get('target_distance', 0),
                    'range_after': after_state['spell_range'],
                    'position': [after_state['pos_x'], after_state['pos_y']],
                })
                continue

            if decision['decision'] == 'TURN':
                # The client says the target is not in front. There is no
                # facing readout, so the turn is blind and the error code
                # decides when the target came into view.
                turn_step('left')
                note('turn', decision)
                continue

            if decision['decision'] == 'WAIT':
                time.sleep(0.2)
                continue

            if decision['decision'] == 'VERIFY_SURVIVAL':
                final = 'target_defeated'
                break

            # RECOVER: retreat and confirm the character survives.
            # Backing straight up fails against a pursuer: it runs along the
            # pursuit line and never opens a gap. Turn away and run instead.
            evidence.capture('04-recover-trigger', state)
            note('recover', decision)
            try:
                steps = break_engagement(hwnd, reader, steps=8,
                                         hold_seconds=MAX_HOLD)
            except ValueError as exc:
                note('retreat_failed', {'error': str(exc)})
                raise ValueError('retreat did not clear combat; recovery unproven')
            for step in steps:
                note('retreat_step', step)
            state = reader()
            note('recover_result', {'health': state['health'],
                                    'combat': state['combat'],
                                    'dead': state['dead']})
            final = 'recovered'
            break

        if final is None:
            raise ValueError('combat loop ended without a verdict')

        # Survival check: alive, out of combat and still for a sustained period.
        quiet = 0
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            state = reader()
            if state['dead']:
                raise ValueError('player died during the run')
            if state['combat']:
                quiet = 0
            else:
                quiet += 1
                if quiet >= 6:
                    break
            time.sleep(0.4)
        if state['combat']:
            raise ValueError('still in combat at the end of the run')
        evidence.capture('05-end', state)
        result['final'] = state
        result['status'] = 'COMBAT_LOOP_COMPLETED'
        result['outcome'] = final
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('06-final')
        path = evidence.write(result)
        d.log('combat run', path, result['status'])
    return 0 if result['status'] == 'COMBAT_LOOP_COMPLETED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
