"""Acquire a hostile target and bind it, without casting anything."""
import json
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
from client_combat_controller import CombatController
from client_evidence import Evidence

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ['Diseased Young Wolf', 'Young Wolf', 'Wolf', 'Diseased Wolf',
              'Rabid Diseased Wolf', 'Kobold Vermin']


def main():
    run = 'client_targeting_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', tried=[])
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        state = reader()
        evidence.capture('01-start', state)
        result['health'] = state['health']
        result['position'] = [state['pos_x'], state['pos_y']]

        for name in CANDIDATES:
            before = reader()
            d.post_key(hwnd, win32con.VK_RETURN)
            time.sleep(0.5)
            for character in '/target ' + name:
                win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
                time.sleep(0.04)
            time.sleep(0.2)
            d.post_key(hwnd, win32con.VK_RETURN)
            time.sleep(1.2)
            state = reader()
            entry = {'name': name, 'target_exists': state['target_exists'],
                     'attackable': state['target_attackable'],
                     'guid': state['target_guid'], 'health': state['target_health'],
                     'max_health': state['target_max_health'],
                     'distance': state['target_distance'],
                     'range': state['spell_range']}
            result['tried'].append(entry)
            if state['target_exists'] and state['target_attackable']:
                controller = CombatController(state['target_guid'], 133)
                binding = controller.bind_target(state)
                entry['binding'] = binding
                result['target_guid'] = state['target_guid']
                result['target_name'] = name
                evidence.capture('02-target-bound', state)
                if binding['decision'] != 'BOUND':
                    raise ValueError('binding refused: ' + str(binding))
                result['status'] = 'TARGET_BOUND'
                break
        else:
            raise ValueError('no hostile target could be acquired')
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('targeting run', path, result['status'])
    return 0 if result['status'] == 'TARGET_BOUND' else 1


if __name__ == '__main__':
    raise SystemExit(main())
