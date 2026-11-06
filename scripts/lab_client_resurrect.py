"""Resurrect the character at its corpse.

The ghost of the character stands on its corpse and the client asks
whether it wants to come back. The question is a red button in the upper
half of the screen, and the driver has to press it.

The script reports what the client answered: the character is alive, or it
is still a ghost, or the dialog was never there.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
from client_evidence import Evidence
from client_parent_run import stamp
from client_read_fresh import find_red_button

ROOT = Path(__file__).resolve().parents[1]


def reader():
    return decode(assert_real_frame(grab_desktop()))


def main():
    run = 'client_resurrect_' + str(time.time_ns())
    result = stamp(dict(run=run, status='FAILED'), sys.argv)
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
        state = reader()
        result['before'] = {'dead': state['dead'], 'health': state['health'],
                            'position': [state['pos_x'], state['pos_y']],
                            'corpse_exists': state.get('corpse_exists'),
                            'corpse': [state.get('corpse_x'),
                                       state.get('corpse_y')]}
        if not state['dead']:
            result['status'] = 'ALREADY_ALIVE'
            result['after'] = result['before']
            evidence.capture('01-already-alive', state)
        else:
            button = find_red_button(grab_desktop())
            result['button'] = button
            if button is None:
                raise ValueError('the dialog of the resurrection was not found')
            evidence.capture('01-dialog')
            # The client puts a countdown on the dialog, and the button is
            # grey until it is over. The button is pressed again and again,
            # and the state is read after every try, so a dialog that waits
            # is not taken for a refusal.
            for attempt in range(10):
                d.u.SetCursorPos(*button)
                time.sleep(0.5)
                try:
                    d.click_client(hwnd, *button)
                except Exception as exc:
                    result.setdefault('click_errors', []).append(repr(exc))
                time.sleep(1.5)
                state = reader()
                result['after'] = {'dead': state['dead'],
                                   'health': state['health'],
                                   'position': [state['pos_x'],
                                                state['pos_y']],
                                   'corpse_exists': state.get('corpse_exists')}
                if not state['dead']:
                    break
                # Enter is deliberately not used: in the game it can open
                # chat rather than activate this dialog.
            evidence.capture('02-after', state)
            if state['dead']:
                result['reason'] = 'the character stayed a ghost'
            else:
                result['status'] = 'RESURRECTED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('resurrect', str(path), result['status'])
    return 0 if result['status'] in ('RESURRECTED', 'ALREADY_ALIVE') else 1


if __name__ == '__main__':
    raise SystemExit(main())
