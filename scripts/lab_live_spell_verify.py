"""Non-combat Frost Armor request with observed event and aura confirmation."""
import json
import time
from pathlib import Path
from PIL import ImageGrab
import lab_driver5 as d
from lab_distance_scenarios import command
from client_control_guard import ControlGuard
from client_window_state import window_observable
from client_live_state import decode, assert_real_frame


def main():
    run = 'client_live_spell_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', samples=[])
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)

        def capture(seconds):
            guard = ControlGuard()
            end = time.monotonic() + seconds
            state = None
            while time.monotonic() < end:
                image = assert_real_frame(ImageGrab.grab())
                state = decode(image)
                decision = guard.observe(state, time.monotonic(), window_observable(hwnd))
                if decision['decision'] == 'RECOVERY_REQUIRED':
                    raise ValueError(decision['reason'])
                if state['protocol'] != 2 or state['target_exists']:
                    raise ValueError('protocol 2 and no target required')
                result['samples'].append(dict(host_monotonic=time.monotonic(), **state))
                time.sleep(.05)
            image.save(d.OUT / (run + '_' + str(len(result['samples'])) + '.png'))
            return state

        before = capture(2)
        result['before'] = before
        result['request'] = '/cast Frost Armor'
        command(hwnd, '/cast Frost Armor')
        after = capture(4)
        result['after'] = after
        if (after['cast_succeeded'] - before['cast_succeeded']) % 65536 != 1:
            raise ValueError('expected exactly one success event')
        if after['cast_failed'] != before['cast_failed'] or after['ui_errors'] != before['ui_errors']:
            raise ValueError('cast failure or UI error observed')
        if after['event_kind'] != 2 or after['event_spell'] != 168 or not after['frost_armor']:
            raise ValueError('Frost Armor event/aura not confirmed')
        result['status'] = 'NONCOMBAT_SPELL_FEEDBACK_VERIFIED'
    except Exception as exc:
        result['error'] = repr(exc)
        if hwnd:
            d.screenshot(run + '_failure.png')
    finally:
        path = Path(__file__).resolve().parents[1] / 'results' / (run + '.json')
        with path.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)
    return 0 if result['status'] == 'NONCOMBAT_SPELL_FEEDBACK_VERIFIED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
