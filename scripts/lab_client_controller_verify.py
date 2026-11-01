"""Non-combat check of the combat-period state machine.

Targets the character itself so no creature is involved, then confirms the
controller reacts to the real telemetry stream.
"""
import json
import time
from pathlib import Path
from PIL import ImageGrab
import lab_driver5 as d
from client_live_state import decode, assert_real_frame
from client_window_state import window_observable
from client_combat_controller import CombatController

ROOT = Path(__file__).resolve().parents[1]
SELF_NAME = 'Probehuman'


def main():
    run = 'client_controller_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', samples=[], decisions=[])
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        controller = CombatController('0x0', 133)
        frames = []

        def sample():
            image = assert_real_frame(ImageGrab.grab())
            state = decode(image)
            if not window_observable(hwnd):
                raise ValueError('client window not observable')
            frames.append(state)
            return state

        # Discover the character's own GUID so the binding check is real.
        state = sample()
        self_guid = '0x0'

        from lab_distance_scenarios import command
        command(hwnd, '/targetexact ' + SELF_NAME)
        time.sleep(1.0)
        state = sample()
        if not state['target_exists']:
            raise ValueError('self target not acquired')
        self_guid = state['target_guid']
        result['self_guid'] = self_guid

        controller = CombatController(self_guid, 133)
        binding = controller.bind_target(state)
        result['binding'] = binding
        # The character cannot attack itself, so the binding must be refused.
        if binding['decision'] != 'RECOVER' or binding['reason'] != 'target_not_attackable':
            raise ValueError('self binding should be refused: ' + str(binding))

        for _ in range(6):
            state = sample()
            decision = controller.observe(state, time.monotonic())
            result['decisions'].append(decision)
            time.sleep(.05)

        # A valid hostile target must be accepted, so build the same state with
        # the attackable flag set and confirm the controller binds it.
        valid = dict(state)
        valid['target_attackable'] = True
        valid['target_dead'] = False
        valid['target_health'] = 30
        valid['spell_range'] = 1
        accept = CombatController(self_guid, 133)
        accept.bind_target(valid)
        accept.observe(valid, time.monotonic())
        accepted = accept.observe(dict(valid, sequence=state['sequence'] + 1,
                                       game_ms=state['game_ms'] + 100),
                                  time.monotonic() + 0.2)
        result['valid_target_decision'] = accepted
        if accepted['decision'] != 'CAST_ALLOWED':
            raise ValueError('valid target was not accepted: ' + str(accepted))

        result['status'] = 'CONTROLLER_SELF_BINDING_VERIFIED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        path = ROOT / 'results' / (run + '.json')
        with path.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)
    return 0 if result['status'] == 'CONTROLLER_SELF_BINDING_VERIFIED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
