"""Full combat loop: acquire a target, fight it, retreat when needed, verify survival.

The loop is bounded in every direction: target must be a specific hostile,
casts are budgeted, health has a floor, and the run ends with a survival check
rather than a cast count.
"""
import json
import math
import sys
import threading
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import (decode, assert_real_frame, name_hash,
                                THREAT_UNKNOWN)
from client_window_state import window_observable
from client_combat_controller import (CombatController, LOW_HEALTH_RATIO,
                                     KILL_REASONS)
from client_evidence import Evidence
from client_retreat import break_engagement
from client_facing import CastProbe, sweep_toward
from client_chat_guard import ensure_chat_closed
from client_walk import walk_to

ROOT = Path(__file__).resolve().parents[1]
FIREBALL = 133
# A creature that leaves combat regenerates quickly in this client version,
# so the target has to be weak enough to kill before it recovers. An ordinary
# creature of level six has about a hundred and twenty health, and the
# character deals about twenty one points per cast.
MAX_TARGET_HEALTH = 130
# How long the character has to be watched after the fight before the run
# may call it a success.
SURVIVAL_OBSERVATION = 30.0
# The places where the creatures of the valley were seen before. They roam,
# so the driver walks over them until it finds one. The offsets are relative
# to the character: the coordinates of the probe belong to the map area the
# character is in, and every area has its own basis.
SWEEP_OFFSETS = [(0.0, 0.0), (0.006, 0.006), (-0.006, -0.006),
                  (0.006, -0.006), (-0.006, 0.006), (0.012, 0.0),
                  (0.0, 0.012)]
VK_FORWARD = 0x57
VK_LEFT = 0x25
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
    """Type a chat command and return the state after it had time to act.

    The chat input of the client steals every key press while it is open,
    so it is closed before the command is typed.
    """
    ensure_chat_closed(hwnd, reader)
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


def action_check(controller, state, now):
    """Watch the character while a spell is in flight.

    The heartbeat alone only keeps the freshness alive. The checks that can
    stop the fight have to run at every sample: a character that is dying,
    that is below the floor of the health, or that is fighting another
    creature than the one that was bound.
    """
    if not controller.heartbeat(state, now):
        return False
    if state.get('dead'):
        return False
    maximum = state.get('max_health') or 0
    if maximum and state.get('health', 0) / maximum <= controller.low_health:
        return False
    if state.get('target_exists') and state.get('target_guid') != controller.target_guid:
        return False
    return True


def tab_target(hwnd, reader, steps=8, prefer_hash=None):
    """Select a hostile creature with the tab key.

    When a name hash is given, the creature with that name is preferred; the
    probe reports the name of the target as a hash, so the driver can lock
    a creature without reading any text.
    """
    named = []
    found = []
    for _ in range(steps):
        d.post_key(hwnd, win32con.VK_TAB)
        time.sleep(0.5)
        candidate = reader()
        if not (candidate['target_exists']
                and candidate['target_attackable']
                and candidate['target_health'] > 1):
            continue
        if prefer_hash is not None:
            # The creature was asked for by name, so only that one counts.
            if candidate.get('target_name_hash') == prefer_hash:
                # The scan stops here: every further key press would only
                # take time and select another creature.
                return candidate
            continue
        found.append(candidate)
    if prefer_hash is not None:
        return None
    if found:
        return found[0]
    return None


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
        if start['protocol'] not in (4, 5, 6, 7, 8, 9, 10, 11, 12, 13):
            raise ValueError('protocol 4 to 12 required, got ' + str(start['protocol']))
        if start['dead'] or start['combat']:
            raise ValueError('must start alive and out of combat')
        evidence.capture('01-start', start)
        note('baseline', {'health': start['health'], 'position': [start['pos_x'], start['pos_y']]})

        # Acquire a hostile target and bind its identity. The tab key selects
        # the nearest hostile unit in view, which works even when the name of
        # the creature is not known to the caller.
        target_name = result.get('target')
        prefer_hash = None
        if '--target-name' in sys.argv:
            index = sys.argv.index('--target-name')
            target_name = sys.argv[index + 1]
            prefer_hash = name_hash(target_name)
            result['target_name_hash'] = prefer_hash
        state = None
        if target_name and prefer_hash is None:
            state = send_command(hwnd, '/target ' + target_name, reader)
        else:
            state = tab_target(hwnd, reader, prefer_hash=prefer_hash)
            if state is None:
                # The creatures roam, so the character walks over the places
                # where they were seen before and looks again. The places
                # are relative to the character: the coordinates of the
                # probe belong to the map area the character is in, and the
                # areas have their own basis.
                here = (reader()['pos_x'], reader()['pos_y'])
                spots = [(here[0] + offset[0], here[1] + offset[1])
                         for offset in SWEEP_OFFSETS]
                if '--walk-to' in sys.argv:
                    index = sys.argv.index('--walk-to')
                    spot = (float(sys.argv[index + 1]),
                            float(sys.argv[index + 2]))
                    spots = [spot] + spots
                note('sweep', [list(spot) for spot in spots])
                for spot in spots:
                    walk_to(d.game_window(), reader, spot, timeout=45.0)
                    evidence.capture('01b-walked', None)
                    state = tab_target(hwnd, reader, prefer_hash=prefer_hash)
                    if state is not None:
                        break
        if not state or not state['target_exists'] or not state['target_attackable']:
            raise ValueError('could not acquire a hostile target')
        if state.get('target_class', 1) > 1:
            raise ValueError('the target is an elite creature: '
                             + str(state.get('target_class_name')))
        if state['target_health'] > MAX_TARGET_HEALTH:
            raise ValueError('the target has too much health: '
                             + str(state['target_health']))
        target_guid = state['target_guid']
        result['target_guid'] = target_guid
        result['target_name_hash_seen'] = state.get('target_name_hash')
        if prefer_hash is not None and result['target_name_hash_seen'] != prefer_hash:
            # The driver was asked for a creature by name, so a run against
            # another one would not be what was asked for.
            raise ValueError('the creature %s was not in reach (the hash of '
                             'the selected one is %s)'
                             % (target_name, result['target_name_hash_seen']))
        result['target_name'] = target_name or 'tab-selected'
        result['target_health_at_start'] = state['target_health']
        evidence.capture('02-target-acquired', state)
        note('target_acquired', {'guid': target_guid, 'health': state['target_health'],
                                 'distance': state['target_distance'],
                                 'range': state['spell_range']})

        controller = CombatController(target_guid, FIREBALL, max_attempts=4, timeout=2.5)
        binding = controller.bind_target(state)
        if binding['decision'] != 'BOUND':
            raise ValueError('target binding failed: ' + str(binding))

        # Close the distance before the first cast. The tab key must not be
        # pressed here: it selects the next hostile creature and would
        # break the identity of the bound target. When the walk does not
        # bring the target into range, the controller takes over: it walks
        # closer and turns towards the creature when the client says that
        # the target is not in front.
        for approach in range(6):
            if state['spell_range'] == 1:
                break
            ensure_chat_closed(hwnd, reader)
            moved = move_while_watching(hwnd, VK_FORWARD, 0.7, reader)
            state = moved[-1] if moved else reader()
            note('approach', {'attempt': approach, 'range': state['spell_range'],
                              'position': [state['pos_x'], state['pos_y']]})
        evidence.capture('03-in-range', state)

        deadline = time.monotonic() + 90
        last_evidence = time.monotonic()
        final = None
        while time.monotonic() < deadline:
            decision = None
            try:
                state = reader()
            except Exception as exc:
                # The panel cannot be read any more. The fight is over and
                # the character has to get out; whether that worked is
                # checked afterwards, and an unreadable panel is never
                # reported as a success.
                note('reading_failed', {'error': repr(exc)})
                result['reading_failed'] = repr(exc)
                decision = {'decision': 'RECOVER', 'reason': 'reading_failed'}
                state = {'dead': False, 'health': 0, 'max_health': 1,
                         'combat': True, 'target_exists': False,
                         'target_guid': '', 'target_health': 0,
                         'target_dead': False, 'speed': 0.0,
                         'pos_x': 0.0, 'pos_y': 0.0, 'facing': 0.0}
            if decision is None and not window_observable(hwnd):
                # The client is not in front any more. The observation is
                # lost, so the run goes into the recovery branch: the
                # character turns away and runs. Waiting for the picture to
                # come back would leave it in the fight.
                note('lost_observation', {'observable': False,
                                          'health': state['health'],
                                          'combat': state['combat']})
                decision = {'decision': 'RECOVER', 'reason': 'lost_observation'}
            elif decision is None:
                if (prefer_hash is not None and state['target_exists']
                        and state.get('target_name_hash') != prefer_hash):
                    # The client selected another creature, most likely the
                    # one that attacked the character. The named creature is
                    # picked again, so the fight stays about the one that
                    # was asked for.
                    again = tab_target(hwnd, reader, prefer_hash=prefer_hash)
                    if again is not None:
                        state = again
                        controller.rebind(state)
                        note('rebound', {'guid': state['target_guid'],
                                         'health': state['target_health']})
                decision = controller.observe(state, time.monotonic())
            note('observe', decision)

            if decision['decision'] == 'CAST_ALLOWED':
                controller.record_attempt(state['target_health'])
                result['casts'] = result.get('casts', 0) + 1
                # A command only reaches the client when the chat input is
                # closed, and an open chat input would swallow the key
                # presses of the next movement.
                ensure_chat_closed(hwnd, reader)
                # The cast runs in a worker thread; keep reading telemetry so
                # the heartbeat stays alive while the spell is in flight.
                after = cast(hwnd, '/cast Fireball', reader,
                             on_tick=lambda s: action_check(controller, s,
                                                          time.monotonic()))
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
                walked = math.hypot(after_state['pos_x'] - state['pos_x'],
                                     after_state['pos_y'] - state['pos_y'])
                note('close_distance', {
                    'distance_before': before_distance,
                    'distance_after': after_state.get('target_distance', 0),
                    'range_after': after_state['spell_range'],
                    'walked': walked,
                    'position': [after_state['pos_x'], after_state['pos_y']],
                })
                if walked < 0.0005:
                    # The character does not move: a wall or a rock is in the
                    # way. Walking into it again would only use up the time
                    # of the fight, so the character turns and tries the
                    # next direction.
                    hold(VK_LEFT, 0.8)
                    note('detour', {'position': [after_state['pos_x'],
                                                 after_state['pos_y']]})
                continue

            if decision['decision'] == 'TURN':
                # The client says the target is not in front. There is no
                # facing readout, so the turn is blind and the error code
                # decides when the target came into view. The sweep turns a
                # small step and casts again until the cast succeeds.
                # The cast of the sweep needs the heartbeat as well: the
                # sweep turns and casts for a while, and without the
                # heartbeat the freshness of the telemetry would look stale
                # and the run would go into the recovery.
                probe = CastProbe(
                    lambda: cast(hwnd, '/cast Fireball', reader,
                                 on_tick=lambda s: controller.heartbeat(
                                     s, time.monotonic())),
                    reader, settle=0)
                steps, after_state = sweep_toward(probe, max_steps=18,
                                                  hwnd=hwnd)
                note('turn', {'reason': decision['reason'], 'steps': steps,
                              'cast_failed': after_state['cast_failed'],
                              'cast_succeeded': after_state['cast_succeeded'],
                              'target_health': after_state['target_health'],
                              'error_reason': after_state['last_error_reason']})
                state = after_state
                controller.record_attempt()
                continue

            if decision['decision'] == 'WAIT':
                time.sleep(0.2)
                continue

            if decision['decision'] == 'VERIFY_SURVIVAL':
                # A kill has to be proved: the death of the bound creature
                # has to have been seen. A creature that vanished without
                # that proof leaves the outcome of the fight unknown, and
                # that must not be reported as a kill.
                reason = decision.get('reason')
                final = ('target_defeated'
                         if reason in KILL_REASONS else 'target_gone_unconfirmed')
                result['kill_evidence'] = reason
                result['kill_confirmed'] = decision.get('kill_confirmed', False)
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

        # Survival check: the character has to be alive, out of combat and
        # still for a sustained period. The observation after the fight is
        # at least SURVIVAL_OBSERVATION seconds long, because a character
        # that is still in combat a moment after the run looks safe.
        quiet = 0
        observed = 0.0
        threats = []
        deadline = time.monotonic() + SURVIVAL_OBSERVATION + 60
        last = time.monotonic()
        while observed < SURVIVAL_OBSERVATION and time.monotonic() < deadline:
            state = reader()
            now = time.monotonic()
            observed += now - last
            last = now
            if state['dead']:
                raise ValueError('player died during the run')
            if state['combat']:
                quiet = 0
            else:
                quiet += 1
            threats.append(state.get('threat'))
            time.sleep(0.4)
        result['survival_observation'] = round(observed, 1)
        # The combat flag alone does not tell whether the aggro is gone: a
        # creature that still has the character on its list keeps a threat
        # even when the fight was stopped. The threat situation is watched
        # over the whole observation.
        result['threat_max'] = max([value for value in threats
                                    if value is not None] or [0])
        result['threat_last'] = threats[-1] if threats else None
        if state['combat']:
            raise ValueError('still in combat at the end of the run')
        if state['dead']:
            raise ValueError('the character is dead at the end of the run')
        if result['threat_max'] == THREAT_UNKNOWN:
            # The threat could not be read. That is not a cleared threat.
            raise ValueError('the threat of the player could not be read; '
                             'the end of the fight cannot be confirmed')
        if result['threat_max'] == THREAT_UNKNOWN:
            # The threat could not be read. That is not a cleared threat.
            raise ValueError('the threat of the player could not be read; '
                             'the end of the fight cannot be confirmed')
        if result['threat_max'] > 0:
            raise ValueError('the threat did not clear during the '
                             'observation: %s' % result['threat_max'])
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
