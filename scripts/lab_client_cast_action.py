"""Driver-side spell action wired to the combat controller, without combat.

The character targets itself so no creature is involved: the point is to
prove that a controller decision turns into an actual cast request whose
result is read back from the telemetry.
"""
import json
import time
from pathlib import Path
from PIL import ImageGrab
import win32gui
import win32con
import lab_driver5 as d
from client_live_state import decode, assert_real_frame
from client_window_state import window_observable
from client_chat_sequence import ChatSequence
from client_combat_controller import CombatController

ROOT = Path(__file__).resolve().parents[1]
SELF_NAME = 'Probehuman'
FROST_ARMOR = 168


def main():
    run = 'client_cast_action_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', samples=[], inputs=[])
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        frames = []

        def sample():
            image = assert_real_frame(ImageGrab.grab())
            state = decode(image)
            frames.append(state)
            return state

        from lab_distance_scenarios import command
        command(hwnd, '/targetexact ' + SELF_NAME)
        time.sleep(1.0)
        state = sample()
        if not state['target_exists']:
            raise ValueError('self target not acquired')

        # The controller refuses an unattackable target, so a spell action is
        # driven directly here; the controller decides what the *request* means.
        controller = CombatController(state['target_guid'], FROST_ARMOR)
        binding = controller.bind_target(state)
        result['binding'] = binding
        if binding['decision'] != 'RECOVER' or binding['reason'] != 'target_not_attackable':
            raise ValueError('self target should not be attackable: ' + str(binding))

        before = state
        sequence = ChatSequence('/cast Frost Armor', time.monotonic())
        submitted = None
        start = time.monotonic()
        while time.monotonic() - start < 15:
            now = time.monotonic()
            state = sample()
            action = sequence.step(now, True)
            if action:
                kind, value = action
                if not window_observable(hwnd):
                    raise ValueError('client window not observable before input')
                if kind == 'char':
                    win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(value), 0)
                else:
                    d.post_key(hwnd, value)
                result['inputs'].append(dict(host_monotonic=now, kind=kind, value=value))
            if sequence.submitted:
                if submitted is None:
                    submitted = now
                elif now - submitted >= 3:
                    after = state
                    result['before'] = before
                    result['after'] = after
                    if (after['cast_succeeded'] - before['cast_succeeded']) % 65536 != 1:
                        raise ValueError('expected exactly one success event')
                    if after['cast_failed'] != before['cast_failed']:
                        raise ValueError('cast failure observed')
                    if not after['frost_armor']:
                        raise ValueError('Frost Armor aura not confirmed')
                    queued = [event for event in after['events'] if event['serial']]
                    if not queued or queued[-1]['spell'] != FROST_ARMOR:
                        raise ValueError('event queue head mismatch')
                    result['queued'] = queued
                    result['status'] = 'CAST_ACTION_VERIFIED'
                    break
            time.sleep(.03)
        else:
            raise ValueError('overall timeout')
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        path = ROOT / 'results' / (run + '.json')
        with path.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)
    return 0 if result['status'] == 'CAST_ACTION_VERIFIED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
